"""
EWA-Fed Experiment: Organoid FL — Conformity Monitoring
=========================================================
Correct FL scenario: each lab has its own private Non-IID dataset.
EWA monitors whether minority expertise is suppressed.

Scenario:
  - 5 labs, each with private organoid images
  - Lab A (expert minority): specializes in late_stage, high confidence
  - Lab B-E (majority): mostly healthy, lower confidence
  - Standard FedAvg for model training (not shown here)
  - EWA analyzes uploaded primitives to detect conformity

What EWA measures:
  - Per-class prototype: aggregated statistics across all clients
  - Per-client contribution: how much each client contributes to each class
  - Conformity score: is expert's late_stage knowledge preserved?

Expected result:
  - FedAvg weighting: majority (healthy-heavy) dominates, late_stage
    prototype shifts toward majority's uncertain detections
  - EWA weighting: expert's high-confidence late_stage gets higher weight,
    prototype stays closer to expert's characterization
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from twc_core.ewa.primitives import PrimitiveBatch, PrimitiveCodec
from twc_core.ewa.aggregator import EntropyWeightedAggregator, AggregationStrategy
from twc_core.ewa.conformity import ConformityDetector
from twc_core.audit import AuditEngine

np.random.seed(42)

# ── Configuration ──
NUM_ROUNDS = 10
CLASSES = ["healthy", "early_stage", "late_stage"]

# Each lab has its own data distribution (Non-IID)
LABS = {
    "expert": {
        "name": "Expert Lab (minority)",
        # Expert specializes in late_stage, high confidence
        "class_dist": [0.25, 0.30, 0.45],  # healthy, early, late
        "confidence_range": (0.88, 0.98),
        "num_images": 20,
    },
    "factory_b": {
        "name": "Factory B (majority)",
        "class_dist": [0.70, 0.20, 0.10],
        "confidence_range": (0.55, 0.75),
        "num_images": 50,
    },
    "factory_c": {
        "name": "Factory C (majority)",
        "class_dist": [0.65, 0.25, 0.10],
        "confidence_range": (0.50, 0.72),
        "num_images": 45,
    },
    "factory_d": {
        "name": "Factory D (majority)",
        "class_dist": [0.72, 0.18, 0.10],
        "confidence_range": (0.52, 0.70),
        "num_images": 55,
    },
    "factory_e": {
        "name": "Factory E (majority)",
        "class_dist": [0.68, 0.22, 0.10],
        "confidence_range": (0.58, 0.74),
        "num_images": 48,
    },
}


def simulate_lab_primitives(codec: PrimitiveCodec, lab_id: str, lab_config: dict,
                            round_id: int) -> PrimitiveBatch:
    """Simulate one lab's local inference → visual primitives.

    Each lab detects organoids in its OWN private images.
    No image sharing between labs.
    """
    rng = np.random.RandomState(hash(lab_id) % (2**31) + round_id * 1000)
    n_detections = rng.randint(15, 40)

    class _Det:
        def __init__(self, bbox, cls, conf):
            self.bbox = bbox
            self.class_name = cls
            self.confidence = conf
            self.area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            self.width = bbox[2] - bbox[0]
            self.height = bbox[3] - bbox[1]

    dets = []
    for _ in range(n_detections):
        cls = rng.choice(CLASSES, p=lab_config["class_dist"])
        conf = rng.uniform(*lab_config["confidence_range"])
        # Random bbox (each lab's own image space)
        x1, y1 = rng.randint(10, 500, 2)
        x2, y2 = x1 + rng.randint(40, 150), y1 + rng.randint(40, 150)
        dets.append(_Det([int(x1), int(y1), int(x2), int(y2)], cls, round(conf, 3)))

    codec.client_id = lab_id
    return codec.encode_detections(dets, round_id=round_id)


def run_experiment(strategy: AggregationStrategy, label: str) -> dict:
    """Run EWA monitoring for one FL training strategy."""
    codec = PrimitiveCodec()
    aggregator = EntropyWeightedAggregator(strategy=strategy)
    conformity = ConformityDetector(warning_threshold=0.5)
    audit = AuditEngine(project_name=f"ewa-monitor-{label}")

    audit.append("monitor_start", {
        "strategy": label,
        "labs": list(LABS.keys()),
        "rounds": NUM_ROUNDS,
    })

    round_results = []

    for round_id in range(1, NUM_ROUNDS + 1):
        # Each lab runs local inference on its own data
        batches = []
        for lab_id, lab_config in LABS.items():
            batch = simulate_lab_primitives(codec, lab_id, lab_config, round_id)
            batches.append(batch)

        # EWA analyzes primitives (monitoring, not training)
        result = aggregator.aggregate(batches)

        # Track conformity
        snapshot = conformity.update(result)

        # Extract per-class detail from prototypes
        class_info = {}
        for proto in result.prototypes:
            class_info[proto.ref] = {
                "num_primitives": proto.num_primitives,
                "num_contributors": proto.num_clients,
                "avg_confidence": proto.mean_confidence,
                "avg_entropy": proto.mean_entropy,
                "client_stats": proto.client_stats,
            }

        # Key metric: expert's weight on late_stage (its specialty)
        late_proto = next((p for p in result.prototypes if p.ref == "late_stage"), None)
        expert_weight = 0.0
        late_conformity = 0.0
        if late_proto and "expert" in late_proto.client_stats:
            expert_weight = late_proto.client_stats["expert"].get("weight_share", 0.0)
        # Get conformity from conformity_report
        per_class = result.conformity_report.get("per_class", {})
        late_info = per_class.get("late_stage", {})
        late_conformity = late_info.get("conformity_score", 0.0)

        audit.append("round_analysis", {
            "round": round_id,
            "total_input": result.total_input,
            "total_output": result.total_output,
            "late_stage_conformity": late_conformity,
            "expert_late_stage_weight": expert_weight,
        })

        round_results.append({
            "round": round_id,
            "total_input": result.total_input,
            "total_output": result.total_output,
            "avg_entropy": result.entropy_stats.get("mean", 0),
            "conformity_ratio": result.conformity_report.get("high_conformity_ratio", 0),
            "minority_suppressed": result.conformity_report.get("minority_suppressed", 0),
            "late_stage_conformity": late_conformity,
            "expert_late_stage_weight": expert_weight,
            "late_stage_avg_conf": late_proto.mean_confidence if late_proto else 0,
            "alerts": len(conformity.alerts),
        })

    report = conformity.get_report()
    audit.append("monitor_end", {
        "strategy": label,
        "total_alerts": len(conformity.alerts),
        "trend": report["trend"],
    })

    return {
        "strategy": label,
        "rounds": round_results,
        "conformity_report": report,
        "audit_valid": audit.verify_chain(),
        "audit_length": len(audit),
    }


# ── Run ──
print("=" * 70)
print("EWA-Fed Conformity Monitoring: Organoid FL")
print("=" * 70)
print(f"\nScenario: {len(LABS)} labs, {NUM_ROUNDS} rounds")
print(f"  Expert lab:   late_stage specialist (45% late_stage, conf 0.88-0.98)")
print(f"  Factory B-E:  mostly healthy (65-72% healthy, conf 0.50-0.75)")
print(f"  Question: Is expert's late_stage knowledge preserved in aggregation?")
print()

ewa = run_experiment(AggregationStrategy.ENTROPY_WEIGHTED, "EWA")
fed = run_experiment(AggregationStrategy.EQUAL_WEIGHT, "FedAvg")

# ── Per-round comparison ──
print(f"{'Round':>5} | {'EWA Late Conf':>13} | {'Fed Late Conf':>13} | "
      f"{'EWA Expert Wt':>13} | {'Fed Expert Wt':>13}")
print("-" * 75)
for i in range(NUM_ROUNDS):
    e = ewa["rounds"][i]
    f = fed["rounds"][i]
    print(f"{e['round']:>5} | {e['late_stage_conformity']:>13.4f} | "
          f"{f['late_stage_conformity']:>13.4f} | "
          f"{e['expert_late_stage_weight']:>13.4f} | "
          f"{f['expert_late_stage_weight']:>13.4f}")

# ── Summary ──
print(f"\n{'─'*70}")
print("FINAL RESULTS")
print(f"{'─'*70}")

ewa_late = [r["late_stage_conformity"] for r in ewa["rounds"]]
fed_late = [r["late_stage_conformity"] for r in fed["rounds"]]
ewa_exp_wt = [r["expert_late_stage_weight"] for r in ewa["rounds"]]
fed_exp_wt = [r["expert_late_stage_weight"] for r in fed["rounds"]]

print(f"\n{'Metric':<40} {'EWA':>12} {'FedAvg':>12}")
print("-" * 66)
print(f"{'Late_stage avg conformity (↓ = less suppression)':<40} "
      f"{np.mean(ewa_late):>12.4f} {np.mean(fed_late):>12.4f}")
print(f"{'Expert weight on late_stage (↑ = preserved)':<40} "
      f"{np.mean(ewa_exp_wt):>12.4f} {np.mean(fed_exp_wt):>12.4f}")
print(f"{'Total conformity alerts':<40} "
      f"{len(ewa['conformity_report']['alerts']):>12} {len(fed['conformity_report']['alerts']):>12}")
print(f"{'Audit chain valid':<40} "
      f"{'✅' if ewa['audit_valid'] else '❌':>12} "
      f"{'✅' if fed['audit_valid'] else '❌':>12}")

# Key finding
ewa_exp_avg = np.mean(ewa_exp_wt)
fed_exp_avg = np.mean(fed_exp_wt)
diff = ewa_exp_avg - fed_exp_avg

print(f"\n{'='*70}")
print("KEY FINDING:")
print(f"  Expert's weight on late_stage (its specialty):")
print(f"    EWA:    {ewa_exp_avg:.4f}")
print(f"    FedAvg: {fed_exp_avg:.4f}")
if diff > 0.01:
    print(f"  → EWA gives expert {diff:.4f} MORE weight on its specialty class")
    print(f"  → Expert's domain knowledge is better preserved under EWA")
elif diff < -0.01:
    print(f"  → FedAvg gives expert {-diff:.4f} MORE weight")
    print(f"  → (unexpected — investigate class distribution)")
else:
    print(f"  → Both strategies give similar weight to expert")
print(f"{'='*70}")

assert ewa["audit_valid"] and fed["audit_valid"]
print(f"\n✅ Both audit chains verified (tamper-evident)")
print(f"✅ Experiment complete")
