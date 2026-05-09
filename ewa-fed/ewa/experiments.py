"""EWA-Fed experiment configurations and runner.

Self-contained: no twc-core dependency.
"""
from __future__ import annotations

import numpy as np
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Tuple

from ewa.primitives import PrimitiveBatch, PrimitiveCodec, PrimitiveType
from ewa.aggregator import (
    EntropyWeightedAggregator, AggregationStrategy, AggregationResult,
)
from ewa.conformity import ConformityDetector


@dataclass
class ClientProfile:
    client_id: str
    label: str
    class_distribution: Dict[str, float]
    confidence_range: Tuple[float, float]
    n_samples_per_round: int = 20


@dataclass
class ExperimentConfig:
    task_name: str
    modality: str
    domain: str
    clients: List[ClientProfile]
    expert_client_id: str
    expert_specialty_class: str
    n_rounds: int = 10
    seed: int = 42


@dataclass
class ExperimentResult:
    task_name: str
    modality: str
    domain: str
    n_rounds: int
    n_clients: int
    strategy: str
    rounds: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0


def _generate_nlp_primitives(client: ClientProfile, round_id: int, rng: np.random.RandomState) -> PrimitiveBatch:
    codec = PrimitiveCodec()
    codec.client_id = client.client_id
    points, labels, entropies = [], [], []
    for cls, frac in client.class_distribution.items():
        n = max(1, int(frac * client.n_samples_per_round))
        for _ in range(n):
            conf = rng.uniform(*client.confidence_range)
            entropy = max(0.01, -np.log(max(conf, 0.01)) + rng.normal(0, 0.05))
            points.append((0, 0))
            labels.append(cls)
            entropies.append(entropy)
    batch = codec.encode_points(points, labels, entropies=entropies, round_id=round_id)
    for p in batch.primitives:
        p.auxiliary = {"confidence": float(np.exp(-p.token_entropy)), "modality": "nlp"}
    return batch


def _generate_cv_primitives(client: ClientProfile, round_id: int, rng: np.random.RandomState) -> PrimitiveBatch:
    codec = PrimitiveCodec()
    codec.client_id = client.client_id

    class _Det:
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
        for _ in range(n):
            conf = rng.uniform(*client.confidence_range)
            x1, y1 = rng.randint(10, 200), rng.randint(10, 200)
            x2, y2 = x1 + rng.randint(50, 200), y1 + rng.randint(50, 200)
            dets.append(_Det([x1, y1, x2, y2], cls, conf))
    return codec.encode_detections(dets, round_id=round_id)


def run_experiment(config: ExperimentConfig, strategy: AggregationStrategy = AggregationStrategy.ENTROPY_WEIGHTED) -> ExperimentResult:
    rng = np.random.RandomState(config.seed)
    agg = EntropyWeightedAggregator(strategy=strategy)
    detector = ConformityDetector()
    gen = _generate_nlp_primitives if config.modality == "nlp" else _generate_cv_primitives
    t0 = time.time()
    rounds = []

    for rnd in range(1, config.n_rounds + 1):
        batches = [gen(c, rnd, rng) for c in config.clients]
        result = agg.aggregate(batches)
        detector.update(result)

        late_proto = next((p for p in result.prototypes if p.ref == config.expert_specialty_class), None)
        expert_ws = 0.0
        if late_proto and config.expert_client_id in late_proto.client_stats:
            expert_ws = late_proto.client_stats[config.expert_client_id].get("weight_share", 0.0)

        per_class = result.conformity_report.get("per_class", {})
        late_conf = per_class.get(config.expert_specialty_class, {}).get("conformity_score", 0.0)

        rounds.append({
            "round": rnd,
            "total_input": result.total_input,
            "total_output": result.total_output,
            "avg_entropy": result.entropy_stats.get("mean", 0),
            "expert_weight_share": expert_ws,
            "specialty_conformity": late_conf,
            "high_conformity_ratio": result.conformity_report.get("high_conformity_ratio", 0),
        })

    expert_ws_list = [r["expert_weight_share"] for r in rounds]
    summary = {
        "expert_specialty_weight": {
            "ewa_mean": float(np.mean(expert_ws_list)),
            "ewa_std": float(np.std(expert_ws_list)),
            "fedavg_mean": 0.0,
            "fedavg_std": 0.0,
            "improvement": 0.0,
            "improvement_pct": 0.0,
        },
        "avg_entropy": float(np.mean([r["avg_entropy"] for r in rounds])),
        "conformity_alerts": len(detector.alerts),
    }

    # Also run FedAvg baseline for comparison
    if strategy != AggregationStrategy.EQUAL_WEIGHT:
        rng2 = np.random.RandomState(config.seed)
        agg2 = EntropyWeightedAggregator(strategy=AggregationStrategy.EQUAL_WEIGHT)
        fed_ws_list = []
        for rnd in range(1, config.n_rounds + 1):
            batches = [gen(c, rnd, rng2) for c in config.clients]
            result2 = agg2.aggregate(batches)
            proto = next((p for p in result2.prototypes if p.ref == config.expert_specialty_class), None)
            if proto and config.expert_client_id in proto.client_stats:
                fed_ws_list.append(proto.client_stats[config.expert_client_id].get("weight_share", 0.0))
        if fed_ws_list:
            summary["expert_specialty_weight"]["fedavg_mean"] = float(np.mean(fed_ws_list))
            summary["expert_specialty_weight"]["fedavg_std"] = float(np.std(fed_ws_list))
            ewa_m = summary["expert_specialty_weight"]["ewa_mean"]
            fed_m = summary["expert_specialty_weight"]["fedavg_mean"]
            summary["expert_specialty_weight"]["improvement"] = round(ewa_m - fed_m, 2)
            summary["expert_specialty_weight"]["improvement_pct"] = round((ewa_m - fed_m) / max(fed_m, 0.01) * 100, 1)

    return ExperimentResult(
        task_name=config.task_name,
        modality=config.modality,
        domain=config.domain,
        n_rounds=config.n_rounds,
        n_clients=len(config.clients),
        strategy=strategy.value,
        rounds=rounds,
        summary=summary,
        duration_sec=round(time.time() - t0, 2),
    )


# ── Experiment Configs ──

def medical_nlp() -> ExperimentConfig:
    return ExperimentConfig(
        task_name="Medical NLP (ClinicalBERT)",
        modality="nlp", domain="medical",
        clients=[
            ClientProfile("expert", "🔬 Expert Hospital", {"common_disease": 0.20, "rare_syndrome": 0.45, "medication": 0.20, "lab_result": 0.15}, (0.85, 0.98)),
            ClientProfile("hosp_a", "🏥 Hospital A", {"common_disease": 0.60, "rare_syndrome": 0.05, "medication": 0.25, "lab_result": 0.10}, (0.50, 0.75)),
            ClientProfile("hosp_b", "🏥 Hospital B", {"common_disease": 0.65, "rare_syndrome": 0.05, "medication": 0.20, "lab_result": 0.10}, (0.55, 0.70)),
            ClientProfile("clinic_c", "🏥 Clinic C", {"common_disease": 0.70, "rare_syndrome": 0.03, "medication": 0.17, "lab_result": 0.10}, (0.50, 0.68)),
            ClientProfile("clinic_d", "🏥 Clinic D", {"common_disease": 0.72, "rare_syndrome": 0.03, "medication": 0.15, "lab_result": 0.10}, (0.48, 0.65)),
        ],
        expert_client_id="expert",
        expert_specialty_class="rare_syndrome",
    )


def financial_nlp() -> ExperimentConfig:
    return ExperimentConfig(
        task_name="Financial NLP (FinBERT)",
        modality="nlp", domain="financial",
        clients=[
            ClientProfile("expert", "🏦 Expert Fund", {"bullish": 0.20, "bearish": 0.20, "neutral": 0.15, "high_risk": 0.45}, (0.82, 0.96)),
            ClientProfile("fund_a", "📊 Fund A", {"bullish": 0.35, "bearish": 0.30, "neutral": 0.25, "high_risk": 0.10}, (0.50, 0.72)),
            ClientProfile("fund_b", "📊 Fund B", {"bullish": 0.30, "bearish": 0.35, "neutral": 0.25, "high_risk": 0.10}, (0.52, 0.70)),
            ClientProfile("bank_c", "🏦 Bank C", {"bullish": 0.35, "bearish": 0.30, "neutral": 0.25, "high_risk": 0.10}, (0.48, 0.68)),
            ClientProfile("bank_d", "🏦 Bank D", {"bullish": 0.38, "bearish": 0.32, "neutral": 0.20, "high_risk": 0.10}, (0.50, 0.65)),
        ],
        expert_client_id="expert",
        expert_specialty_class="high_risk",
    )


def medical_cv() -> ExperimentConfig:
    return ExperimentConfig(
        task_name="Medical CV (Organoid, ResNet18)",
        modality="cv", domain="medical",
        clients=[
            ClientProfile("expert", "🔬 Expert Lab", {"healthy": 0.15, "early_stage": 0.20, "late_stage": 0.45, "necrotic": 0.20}, (0.85, 0.98)),
            ClientProfile("lab_a", "🏭 Lab A", {"healthy": 0.65, "early_stage": 0.20, "late_stage": 0.10, "necrotic": 0.05}, (0.50, 0.75)),
            ClientProfile("lab_b", "🏭 Lab B", {"healthy": 0.70, "early_stage": 0.15, "late_stage": 0.08, "necrotic": 0.07}, (0.55, 0.70)),
            ClientProfile("lab_c", "🏭 Lab C", {"healthy": 0.68, "early_stage": 0.17, "late_stage": 0.08, "necrotic": 0.07}, (0.50, 0.68)),
            ClientProfile("lab_d", "🏭 Lab D", {"healthy": 0.72, "early_stage": 0.13, "late_stage": 0.07, "necrotic": 0.08}, (0.48, 0.65)),
        ],
        expert_client_id="expert",
        expert_specialty_class="late_stage",
    )


def industrial_cv() -> ExperimentConfig:
    return ExperimentConfig(
        task_name="Industrial CV (PCB Defect, ResNet18)",
        modality="cv", domain="industrial",
        clients=[
            ClientProfile("expert", "🔬 Expert Inspector", {"short": 0.15, "open": 0.15, "missing": 0.20, "spurious_copper": 0.50}, (0.80, 0.95)),
            ClientProfile("line_a", "🏭 Line A", {"short": 0.30, "open": 0.30, "missing": 0.25, "spurious_copper": 0.15}, (0.50, 0.72)),
            ClientProfile("line_b", "🏭 Line B", {"short": 0.35, "open": 0.28, "missing": 0.22, "spurious_copper": 0.15}, (0.52, 0.70)),
            ClientProfile("line_c", "🏭 Line C", {"short": 0.32, "open": 0.30, "missing": 0.23, "spurious_copper": 0.15}, (0.48, 0.68)),
            ClientProfile("line_d", "🏭 Line D", {"short": 0.30, "open": 0.32, "missing": 0.23, "spurious_copper": 0.15}, (0.50, 0.65)),
        ],
        expert_client_id="expert",
        expert_specialty_class="spurious_copper",
    )


ALL_EXPERIMENTS = {
    "medical_nlp": medical_nlp,
    "financial_nlp": financial_nlp,
    "medical_cv": medical_cv,
}
