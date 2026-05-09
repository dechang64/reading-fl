"""
EWA-Fed Experiment Framework
=============================
Unified framework for running EWA conformity monitoring experiments
across 4 tasks: Medical NLP, Financial NLP, Medical CV, Industrial CV.

Each experiment:
1. Defines client profiles (expert minority + majority)
2. Simulates FL rounds with Non-IID data
3. Runs EWA vs FedAvg comparison
4. Outputs metrics for paper tables

Usage:
    python -m experiments.run_all
    python -m experiments.run_all --task medical_cv
    python -m experiments.run_all --output results/
"""
from __future__ import annotations

import sys
import os
import json
import time
import argparse
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from twc_core.ewa.primitives import PrimitiveBatch, PrimitiveCodec, PrimitiveType
from twc_core.ewa.aggregator import (
    EntropyWeightedAggregator, AggregationStrategy, AggregationResult,
)
from twc_core.ewa.conformity import ConformityDetector
from twc_core.audit import AuditEngine


# ── Data Classes ──

@dataclass
class ClientProfile:
    """Defines a simulated FL client."""
    client_id: str
    label: str
    class_distribution: Dict[str, float]  # class -> fraction
    confidence_range: Tuple[float, float]  # (min, max)
    entropy_range: Tuple[float, float] = (0.0, 5.0)  # derived from confidence
    n_samples_per_round: int = 20

    def __post_init__(self):
        # Derive entropy range from confidence range
        # confidence ≈ exp(-entropy) → entropy ≈ -ln(confidence)
        self.entropy_range = (
            round(-np.log(max(self.confidence_range[1], 0.01)), 4),
            round(-np.log(max(self.confidence_range[0], 0.01)), 4),
        )


@dataclass
class ExperimentConfig:
    """Configuration for one experiment."""
    task_name: str
    modality: str  # "nlp" or "cv"
    domain: str  # "medical", "financial", "industrial"
    num_rounds: int = 10
    classes: List[str] = field(default_factory=list)
    clients: List[ClientProfile] = field(default_factory=list)
    expert_client_id: str = "expert"
    expert_specialty: str = ""  # the class the expert specializes in
    seed: int = 42


@dataclass
class RoundMetrics:
    """Metrics for one FL round."""
    round_id: int
    strategy: str
    total_primitives: int
    num_classes: int
    avg_entropy: float
    high_conformity_ratio: float
    minority_suppressed: int
    expert_specialty_weight: float  # expert's weight on its specialty class
    expert_specialty_conformity: float  # conformity score for specialty class
    expert_avg_weight: float  # expert's average weight across all classes


@dataclass
class ExperimentResult:
    """Complete experiment results."""
    task_name: str
    modality: str
    domain: str
    num_rounds: int
    num_clients: int
    expert_specialty: str
    ewa_rounds: List[Dict[str, Any]] = field(default_factory=list)
    fedavg_rounds: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    audit_valid: bool = True
    timestamp: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


# ── Abstract Base ──

class ExperimentBase(ABC):
    """Base class for EWA experiments."""

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.rng = np.random.RandomState(config.seed)

    @abstractmethod
    def generate_primitives(self, client: ClientProfile, round_id: int) -> PrimitiveBatch:
        """Generate simulated primitives for one client in one round."""
        ...

    def run(self) -> ExperimentResult:
        """Run the full experiment (EWA vs FedAvg)."""
        ewa_result = self._run_strategy(AggregationStrategy.ENTROPY_WEIGHTED, "EWA")
        fedavg_result = self._run_strategy(AggregationStrategy.EQUAL_WEIGHT, "FedAvg")

        # Compute summary
        summary = self._compute_summary(ewa_result, fedavg_result)

        return ExperimentResult(
            task_name=self.config.task_name,
            modality=self.config.modality,
            domain=self.config.domain,
            num_rounds=self.config.num_rounds,
            num_clients=len(self.config.clients),
            expert_specialty=self.config.expert_specialty,
            ewa_rounds=ewa_result,
            fedavg_rounds=fedavg_result,
            summary=summary,
            timestamp=datetime.now().isoformat(),
        )

    def _run_strategy(self, strategy: AggregationStrategy, label: str) -> List[Dict]:
        """Run one strategy across all rounds."""
        agg = EntropyWeightedAggregator(strategy=strategy)
        conformity = ConformityDetector()
        audit = AuditEngine()
        rounds = []

        for rnd in range(1, self.config.num_rounds + 1):
            # Generate primitives from all clients
            batches = []
            for client in self.config.clients:
                batch = self.generate_primitives(client, rnd)
                batches.append(batch)

            # Aggregate
            result = agg.aggregate(batches)
            snapshot = conformity.update(result)

            # Extract expert metrics
            expert_ws = 0.0
            specialty_conf = 0.0
            per_class = result.conformity_report.get("per_class", {})

            for proto in result.prototypes:
                if proto.ref == self.config.expert_specialty:
                    cs = proto.client_stats.get(self.config.expert_client_id, {})
                    expert_ws = cs.get("weight_share", 0.0)
                    specialty_conf = per_class.get(self.config.expert_specialty, {}).get("conformity_score", 0.0)

            # Expert average weight across all classes
            expert_weights = []
            for proto in result.prototypes:
                cs = proto.client_stats.get(self.config.expert_client_id, {})
                expert_weights.append(cs.get("weight_share", 0.0))
            expert_avg = float(np.mean(expert_weights)) if expert_weights else 0.0

            audit.append("round_analysis", {
                "round": rnd, "strategy": label,
                "total_input": result.total_input,
                "expert_specialty_weight": expert_ws,
            })

            rounds.append({
                "round": rnd,
                "total_primitives": result.total_input,
                "num_classes": len(result.prototypes),
                "avg_entropy": round(result.entropy_stats.get("mean", 0), 4),
                "high_conformity_ratio": round(
                    result.conformity_report.get("high_conformity_ratio", 0), 4),
                "minority_suppressed": result.conformity_report.get("minority_suppressed", 0),
                "expert_specialty_weight": round(expert_ws, 2),
                "expert_specialty_conformity": round(specialty_conf, 4),
                "expert_avg_weight": round(expert_avg, 2),
            })

        return rounds

    def _compute_summary(self, ewa_rounds: List[Dict], fedavg_rounds: List[Dict]) -> Dict:
        """Compute summary statistics comparing EWA vs FedAvg."""
        ewa_spec = [r["expert_specialty_weight"] for r in ewa_rounds]
        fed_spec = [r["expert_specialty_weight"] for r in fedavg_rounds]
        ewa_avg = [r["expert_avg_weight"] for r in ewa_rounds]
        fed_avg = [r["expert_avg_weight"] for r in fedavg_rounds]
        ewa_conf = [r["high_conformity_ratio"] for r in ewa_rounds]
        fed_conf = [r["high_conformity_ratio"] for r in fedavg_rounds]

        return {
            "expert_specialty_weight": {
                "ewa_mean": round(float(np.mean(ewa_spec)), 2),
                "fedavg_mean": round(float(np.mean(fed_spec)), 2),
                "ewa_std": round(float(np.std(ewa_spec)), 2),
                "fedavg_std": round(float(np.std(fed_spec)), 2),
                "improvement": round(float(np.mean(ewa_spec)) - float(np.mean(fed_spec)), 2),
                "improvement_pct": round(
                    (float(np.mean(ewa_spec)) - float(np.mean(fed_spec)))
                    / max(float(np.mean(fed_spec)), 0.01) * 100, 1
                ),
            },
            "expert_avg_weight": {
                "ewa_mean": round(float(np.mean(ewa_avg)), 2),
                "fedavg_mean": round(float(np.mean(fed_avg)), 2),
            },
            "conformity": {
                "ewa_mean": round(float(np.mean(ewa_conf)), 4),
                "fedavg_mean": round(float(np.mean(fed_conf)), 4),
            },
            "entropy": {
                "ewa_mean": round(float(np.mean([r["avg_entropy"] for r in ewa_rounds])), 4),
                "fedavg_mean": round(float(np.mean([r["avg_entropy"] for r in fedavg_rounds])), 4),
            },
        }


# ── NLP Experiment ──

class NLPExperiment(ExperimentBase):
    """NLP experiment: token entropy from text generation."""

    def generate_primitives(self, client: ClientProfile, round_id: int) -> PrimitiveBatch:
        codec = PrimitiveCodec()
        codec.client_id = client.client_id

        points = []
        labels = []
        entropies = []

        for cls, frac in client.class_distribution.items():
            n = max(1, int(frac * client.n_samples_per_round))
            for _ in range(n):
                conf = self.rng.uniform(*client.confidence_range)
                entropy = -np.log(max(conf, 0.01))
                entropy += self.rng.normal(0, 0.05)
                entropy = max(0.01, entropy)
                points.append((0, 0))  # dummy coords for NLP
                labels.append(cls)
                entropies.append(entropy)

        batch = codec.encode_points(points, labels, entropies=entropies, round_id=round_id)
        # Tag NLP modality
        for p in batch.primitives:
            conf = float(np.exp(-p.token_entropy))
            p.auxiliary = {"confidence": conf, "modality": "nlp"}
        return batch


# ── CV Experiment ──

class CVExperiment(ExperimentBase):
    """CV experiment: softmax entropy from image classification/detection."""

    def generate_primitives(self, client: ClientProfile, round_id: int) -> PrimitiveBatch:
        codec = PrimitiveCodec()
        codec.client_id = client.client_id

        class _Detection:
            def __init__(self, bbox, cls, conf):
                self.bbox = bbox
                self.class_name = cls
                self.confidence = conf
                self.area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                self.width = bbox[2] - bbox[0]
                self.height = bbox[3] - bbox[1]

        dets = []
        for cls, frac in client.class_distribution.items():
            n = max(1, int(frac * client.n_samples_per_round))
            for i in range(n):
                conf = self.rng.uniform(*client.confidence_range)
                # Random bbox
                x1 = self.rng.randint(10, 200)
                y1 = self.rng.randint(10, 200)
                x2 = x1 + self.rng.randint(50, 200)
                y2 = y1 + self.rng.randint(50, 200)
                dets.append(_Detection([x1, y1, x2, y2], cls, conf))

        return codec.encode_detections(dets, round_id=round_id)


# ── Experiment Definitions ──

def medical_nlp_experiment() -> ExperimentConfig:
    """Task 1: Medical text classification (ClinicalBERT + MIMIC-III)."""
    return ExperimentConfig(
        task_name="Medical NLP (ClinicalBERT)",
        modality="nlp",
        domain="medical",
        num_rounds=10,
        classes=["normal", "mild_disease", "severe_disease", "rare_syndrome"],
        expert_client_id="expert_hospital",
        expert_specialty="rare_syndrome",
        clients=[
            ClientProfile(
                client_id="expert_hospital",
                label="🏥 Expert Hospital (Minority)",
                class_distribution={
                    "normal": 0.15, "mild_disease": 0.20,
                    "severe_disease": 0.25, "rare_syndrome": 0.40,
                },
                confidence_range=(0.85, 0.97),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="general_hospital_a",
                label="🏥 General Hospital A",
                class_distribution={
                    "normal": 0.55, "mild_disease": 0.25,
                    "severe_disease": 0.15, "rare_syndrome": 0.05,
                },
                confidence_range=(0.55, 0.78),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="general_hospital_b",
                label="🏥 General Hospital B",
                class_distribution={
                    "normal": 0.60, "mild_disease": 0.22,
                    "severe_disease": 0.13, "rare_syndrome": 0.05,
                },
                confidence_range=(0.50, 0.75),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="clinic_a",
                label="🏥 Community Clinic A",
                class_distribution={
                    "normal": 0.70, "mild_disease": 0.20,
                    "severe_disease": 0.08, "rare_syndrome": 0.02,
                },
                confidence_range=(0.45, 0.68),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="clinic_b",
                label="🏥 Community Clinic B",
                class_distribution={
                    "normal": 0.72, "mild_disease": 0.18,
                    "severe_disease": 0.07, "rare_syndrome": 0.03,
                },
                confidence_range=(0.42, 0.65),
                n_samples_per_round=25,
            ),
        ],
    )


def financial_nlp_experiment() -> ExperimentConfig:
    """Task 2: Financial sentiment analysis (FinBERT + Financial PhraseBank)."""
    return ExperimentConfig(
        task_name="Financial NLP (FinBERT)",
        modality="nlp",
        domain="financial",
        num_rounds=10,
        classes=["bullish", "neutral", "bearish", "high_risk"],
        expert_client_id="quant_fund",
        expert_specialty="high_risk",
        clients=[
            ClientProfile(
                client_id="quant_fund",
                label="📊 Quant Fund (Minority)",
                class_distribution={
                    "bullish": 0.20, "neutral": 0.15,
                    "bearish": 0.20, "high_risk": 0.45,
                },
                confidence_range=(0.82, 0.95),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="large_fund_a",
                label="🏦 Large Fund A",
                class_distribution={
                    "bullish": 0.35, "neutral": 0.40,
                    "bearish": 0.20, "high_risk": 0.05,
                },
                confidence_range=(0.55, 0.78),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="large_fund_b",
                label="🏦 Large Fund B",
                class_distribution={
                    "bullish": 0.38, "neutral": 0.38,
                    "bearish": 0.18, "high_risk": 0.06,
                },
                confidence_range=(0.52, 0.75),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="retail_fund_a",
                label="🏦 Retail Fund A",
                class_distribution={
                    "bullish": 0.40, "neutral": 0.42,
                    "bearish": 0.15, "high_risk": 0.03,
                },
                confidence_range=(0.45, 0.68),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="retail_fund_b",
                label="🏦 Retail Fund B",
                class_distribution={
                    "bullish": 0.42, "neutral": 0.40,
                    "bearish": 0.14, "high_risk": 0.04,
                },
                confidence_range=(0.43, 0.65),
                n_samples_per_round=25,
            ),
        ],
    )


def medical_cv_experiment() -> ExperimentConfig:
    """Task 3: Organoid image classification (ResNet18)."""
    return ExperimentConfig(
        task_name="Medical CV (Organoid, ResNet18)",
        modality="cv",
        domain="medical",
        num_rounds=10,
        classes=["healthy", "early_stage", "late_stage", "necrotic"],
        expert_client_id="expert_lab",
        expert_specialty="late_stage",
        clients=[
            ClientProfile(
                client_id="expert_lab",
                label="🔬 Expert Lab (Minority)",
                class_distribution={
                    "healthy": 0.15, "early_stage": 0.20,
                    "late_stage": 0.45, "necrotic": 0.20,
                },
                confidence_range=(0.85, 0.98),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="factory_a",
                label="🏭 Factory Lab A",
                class_distribution={
                    "healthy": 0.65, "early_stage": 0.20,
                    "late_stage": 0.10, "necrotic": 0.05,
                },
                confidence_range=(0.50, 0.75),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="factory_b",
                label="🏭 Factory Lab B",
                class_distribution={
                    "healthy": 0.68, "early_stage": 0.18,
                    "late_stage": 0.09, "necrotic": 0.05,
                },
                confidence_range=(0.48, 0.72),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="factory_c",
                label="🏭 Factory Lab C",
                class_distribution={
                    "healthy": 0.70, "early_stage": 0.17,
                    "late_stage": 0.08, "necrotic": 0.05,
                },
                confidence_range=(0.45, 0.70),
                n_samples_per_round=25,
            ),
            ClientProfile(
                client_id="factory_d",
                label="🏭 Factory Lab D",
                class_distribution={
                    "healthy": 0.72, "early_stage": 0.15,
                    "late_stage": 0.07, "necrotic": 0.06,
                },
                confidence_range=(0.43, 0.68),
                n_samples_per_round=25,
            ),
        ],
    )


def industrial_cv_experiment() -> ExperimentConfig:
    """Task 4: PCB defect detection (ResNet18)."""
    return ExperimentConfig(
        task_name="Industrial CV (PCB Defect, ResNet18)",
        modality="cv",
        domain="industrial",
        num_rounds=10,
        classes=["no_defect", "short_circuit", "missing_component", "spurious_copper", "pin_hole", "open_circuit"],
        expert_client_id="expert_line",
        expert_specialty="spurious_copper",
        clients=[
            ClientProfile(
                client_id="expert_line",
                label="🔧 Expert Production Line (Minority)",
                class_distribution={
                    "no_defect": 0.20, "short_circuit": 0.15,
                    "missing_component": 0.10, "spurious_copper": 0.35,
                    "pin_hole": 0.10, "open_circuit": 0.10,
                },
                confidence_range=(0.83, 0.96),
                n_samples_per_round=30,
            ),
            ClientProfile(
                client_id="line_a",
                label="🏭 Production Line A",
                class_distribution={
                    "no_defect": 0.55, "short_circuit": 0.15,
                    "missing_component": 0.12, "spurious_copper": 0.05,
                    "pin_hole": 0.08, "open_circuit": 0.05,
                },
                confidence_range=(0.52, 0.76),
                n_samples_per_round=30,
            ),
            ClientProfile(
                client_id="line_b",
                label="🏭 Production Line B",
                class_distribution={
                    "no_defect": 0.58, "short_circuit": 0.14,
                    "missing_component": 0.11, "spurious_copper": 0.04,
                    "pin_hole": 0.07, "open_circuit": 0.06,
                },
                confidence_range=(0.50, 0.74),
                n_samples_per_round=30,
            ),
            ClientProfile(
                client_id="line_c",
                label="🏭 Production Line C",
                class_distribution={
                    "no_defect": 0.60, "short_circuit": 0.13,
                    "missing_component": 0.10, "spurious_copper": 0.05,
                    "pin_hole": 0.07, "open_circuit": 0.05,
                },
                confidence_range=(0.48, 0.72),
                n_samples_per_round=30,
            ),
            ClientProfile(
                client_id="line_d",
                label="🏭 Production Line D",
                class_distribution={
                    "no_defect": 0.62, "short_circuit": 0.12,
                    "missing_component": 0.10, "spurious_copper": 0.04,
                    "pin_hole": 0.06, "open_circuit": 0.06,
                },
                confidence_range=(0.45, 0.70),
                n_samples_per_round=30,
            ),
        ],
    )


# ── Runner ──

EXPERIMENTS = {
    "medical_nlp": ("nlp", medical_nlp_experiment, NLPExperiment),
    "financial_nlp": ("nlp", financial_nlp_experiment, NLPExperiment),
    "medical_cv": ("cv", medical_cv_experiment, CVExperiment),
    "industrial_cv": ("cv", industrial_cv_experiment, CVExperiment),
}


def run_experiment(task_key: str) -> ExperimentResult:
    """Run a single experiment."""
    modality, config_fn, experiment_cls = EXPERIMENTS[task_key]
    config = config_fn()
    experiment = experiment_cls(config)
    return experiment.run()


def run_all(output_dir: Optional[str] = None, tasks: Optional[List[str]] = None):
    """Run all experiments and output results."""
    if tasks is None:
        tasks = list(EXPERIMENTS.keys())

    all_results = {}
    for task_key in tasks:
        print(f"\n{'='*70}")
        print(f"Running: {task_key}")
        print(f"{'='*70}")

        result = run_experiment(task_key)
        all_results[task_key] = result

        # Print summary
        s = result.summary["expert_specialty_weight"]
        print(f"\n  Expert's weight on '{result.expert_specialty}' (specialty):")
        print(f"    EWA:    {s['ewa_mean']:.2f}% ± {s['ewa_std']:.2f}")
        print(f"    FedAvg: {s['fedavg_mean']:.2f}% ± {s['fedavg_std']:.2f}")
        print(f"    Improvement: +{s['improvement']:.2f}% ({s['improvement_pct']:.1f}%)")

        conf = result.summary["conformity"]
        print(f"\n  Conformity (high_conformity_ratio):")
        print(f"    EWA:    {conf['ewa_mean']:.4f}")
        print(f"    FedAvg: {conf['fedavg_mean']:.4f}")

        # Save individual result
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            path = os.path.join(output_dir, f"{task_key}_result.json")
            with open(path, "w") as f:
                f.write(result.to_json())
            print(f"  Saved: {path}")

    # Print comparison table
    _print_comparison_table(all_results)

    # Save combined results
    if output_dir:
        combined = {k: json.loads(v.to_json()) for k, v in all_results.items()}
        combined_path = os.path.join(output_dir, "all_results.json")
        with open(combined_path, "w") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f"\n  Combined results: {combined_path}")

    return all_results


def _print_comparison_table(results: Dict[str, ExperimentResult]):
    """Print a comparison table for all experiments."""
    print(f"\n{'='*90}")
    print("CROSS-TASK COMPARISON TABLE")
    print(f"{'='*90}")
    print(f"{'Task':<35} {'Modality':<8} {'EWA Expert Wt':>14} {'FedAvg Expert Wt':>16} {'Improvement':>12}")
    print("-" * 90)

    for task_key, result in results.items():
        s = result.summary["expert_specialty_weight"]
        print(f"{result.task_name:<35} {result.modality:<8} "
              f"{s['ewa_mean']:>10.2f}% ±{s['ewa_std']:.1f} "
              f"{s['fedavg_mean']:>10.2f}% ±{s['fedavg_std']:.1f} "
              f"{s['improvement']:>+10.2f}%")

    print("-" * 90)

    # NLP vs CV aggregate
    nlp_improvements = []
    cv_improvements = []
    for result in results.values():
        imp = result.summary["expert_specialty_weight"]["improvement"]
        if result.modality == "nlp":
            nlp_improvements.append(imp)
        else:
            cv_improvements.append(imp)

    if nlp_improvements:
        print(f"\n  NLP avg improvement: +{np.mean(nlp_improvements):.2f}%")
    if cv_improvements:
        print(f"  CV avg improvement:  +{np.mean(cv_improvements):.2f}%")
    if nlp_improvements and cv_improvements:
        print(f"  CV > NLP: {'Yes' if np.mean(cv_improvements) > np.mean(nlp_improvements) else 'No'} "
              f"(Δ = {np.mean(cv_improvements) - np.mean(nlp_improvements):.2f}%)")

    print(f"{'='*90}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EWA-Fed Experiment Runner")
    parser.add_argument("--task", type=str, default=None,
                        choices=list(EXPERIMENTS.keys()),
                        help="Run a specific task")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for results")
    args = parser.parse_args()

    if args.task:
        run_all(output_dir=args.output, tasks=[args.task])
    else:
        run_all(output_dir=args.output)
