"""
Module G: Entropy-Weighted Aggregator (v2)

Monitors FL training by analyzing visual primitives from each client.
NOT a training algorithm — a diagnostic tool.

Core idea:
    Each FL client runs local inference → encodes detections as visual primitives
    → uploads primitives (not raw images) to server.
    Server groups primitives by class → computes class prototypes →
    detects whether minority expertise is being suppressed by majority.

Conformity detection:
    - Group primitives by class (ref), not by spatial IoU
    - For each class, compare per-client statistics vs aggregated prototype
    - If expert client's high-confidence detections are underrepresented
      in the aggregated prototype → conformity alert

Privacy: operates on structured primitives only, never on raw images.

Pure NumPy. No PyTorch. Streamlit Cloud compatible.
"""
from __future__ import annotations

import numpy as np
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .primitives import (
    VisualPrimitive, PrimitiveBatch, PrimitiveType, PrimitiveCodec,
)


class AggregationStrategy(Enum):
    """How to weight primitives during aggregation."""
    ENTROPY_WEIGHTED = "entropy_weighted"   # weight = 1/H
    EQUAL_WEIGHT = "equal_weight"           # baseline: uniform weight
    CONFIDENCE_WEIGHTED = "confidence"      # weight = exp(-H)
    INVERSE_ENTROPY = "inverse_entropy"     # weight = 1/(H + epsilon)


@dataclass
class ClassPrototype:
    """Aggregated statistics for one semantic class across all clients.

    This is the core output of EWA: for each detected class (e.g., "late_stage"),
    compute the weighted statistics across all clients' primitives.
    """
    ref: str                              # class label
    num_primitives: int                   # total primitives in this class
    num_clients: int                      # how many clients contributed
    client_ids: List[str]                 # contributing client IDs
    mean_entropy: float                   # weighted mean entropy
    mean_confidence: float                # weighted mean confidence
    mean_area: float                      # weighted mean bbox area
    prevalence: float                     # fraction of all primitives in this class

    # Per-client breakdown for conformity analysis
    client_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # e.g. {"lab_a": {"count": 5, "avg_entropy": 0.1, "avg_confidence": 0.95}}

    def to_dict(self) -> dict:
        return {
            "ref": self.ref,
            "num_primitives": self.num_primitives,
            "num_clients": self.num_clients,
            "client_ids": self.client_ids,
            "mean_entropy": round(self.mean_entropy, 4),
            "mean_confidence": round(self.mean_confidence, 4),
            "mean_area": round(self.mean_area, 2),
            "prevalence": round(self.prevalence, 4),
            "client_stats": self.client_stats,
        }


@dataclass
class AggregationResult:
    """Result of one round of primitive analysis.

    Attributes:
        round_id: FL round number.
        prototypes: Class prototypes — one per detected class.
        total_input: Total primitives received.
        strategy: Aggregation strategy used.
        entropy_stats: Global entropy distribution.
        conformity_report: Per-class conformity analysis.
        client_summaries: Per-client contribution summary.
    """
    round_id: int
    prototypes: List[ClassPrototype]
    total_input: int
    strategy: str
    entropy_stats: Dict[str, float] = field(default_factory=dict)
    conformity_report: Dict[str, Any] = field(default_factory=dict)
    client_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def total_output(self) -> int:
        return len(self.prototypes)

    def to_json(self) -> str:
        return json.dumps({
            "round_id": self.round_id,
            "prototypes": [p.to_dict() for p in self.prototypes],
            "total_input": self.total_input,
            "total_output": self.total_output,
            "strategy": self.strategy,
            "entropy_stats": self.entropy_stats,
            "conformity_report": self.conformity_report,
            "client_summaries": self.client_summaries,
        }, ensure_ascii=False)


# Keep AggregatedPrimitive for backward compatibility
@dataclass
class AggregatedPrimitive:
    """Legacy: single aggregated primitive (kept for API compat)."""
    ref: str
    primitive_type: PrimitiveType
    coords: List[List[int]]
    mean_entropy: float
    weight: float
    num_contributors: int
    contributor_ids: List[str] = field(default_factory=list)
    conformity_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ref": self.ref,
            "type": self.primitive_type.value,
            "coords": self.coords,
            "mean_entropy": round(self.mean_entropy, 4),
            "weight": round(self.weight, 4),
            "contributors": self.num_contributors,
            "client_ids": self.contributor_ids,
            "conformity_score": round(self.conformity_score, 4),
        }


class EntropyWeightedAggregator:
    """Entropy-weighted analyzer for FL visual primitives.

    Groups primitives by class, computes class prototypes,
    and detects conformity (majority suppressing minority expertise).

    Usage:
        agg = EntropyWeightedAggregator(strategy="entropy_weighted")
        result = agg.aggregate(batches)  # List[PrimitiveBatch]
        for proto in result.prototypes:
            print(f"{proto.ref}: {proto.num_clients} clients, "
                  f"conformity={proto.conformity_score:.2f}")
    """

    def __init__(
        self,
        strategy: str = "entropy_weighted",
        entropy_threshold: float = 5.0,
        min_contributors: int = 1,
    ):
        self.strategy = AggregationStrategy(strategy)
        self.entropy_threshold = entropy_threshold
        self.min_contributors = min_contributors

    # ── Weight Computation ────────────────────────────────────

    @staticmethod
    def compute_weight(entropy: float, strategy: AggregationStrategy) -> float:
        """Compute aggregation weight from entropy.

        Low entropy (high confidence) → high weight.
        High entropy (uncertain) → low weight.
        """
        eps = 1e-8
        if strategy == AggregationStrategy.ENTROPY_WEIGHTED:
            return 1.0 / (entropy + eps)
        elif strategy == AggregationStrategy.EQUAL_WEIGHT:
            return 1.0
        elif strategy == AggregationStrategy.CONFIDENCE_WEIGHTED:
            return float(np.exp(-entropy))
        elif strategy == AggregationStrategy.INVERSE_ENTROPY:
            return 1.0 / (entropy + 1.0)
        return 1.0

    # ── Grouping ──────────────────────────────────────────────

    @staticmethod
    def group_by_class(primitives: List[VisualPrimitive]) -> Dict[str, List[VisualPrimitive]]:
        """Group primitives by class label (ref).

        In FL, each client has its own private images, so spatial matching
        (IoU) is meaningless. Instead, we group by semantic class to build
        class-level prototypes across clients.
        """
        groups: Dict[str, List[VisualPrimitive]] = {}
        for p in primitives:
            groups.setdefault(p.ref, []).append(p)
        return groups

    # ── Aggregation ───────────────────────────────────────────

    def aggregate(
        self,
        batches: List[PrimitiveBatch],
    ) -> AggregationResult:
        """Analyze primitives from multiple FL clients.

        FedCtx integration: when unified-fl-backend is available, delegates
        EWA aggregation to the Rust server. Falls back to local Python when
        FedCtx is unavailable.

        Groups by class, computes weighted prototypes, detects conformity.

        Args:
            batches: List of PrimitiveBatch from different clients.

        Returns:
            AggregationResult with class prototypes and conformity analysis.
        """
        if not batches:
            return AggregationResult(
                round_id=0, prototypes=[], total_input=0,
                strategy=self.strategy.value,
            )

        # Try FedCtx EWA aggregation
        try:
            from grpc_client import get_fedctx_client
            client = get_fedctx_client()
            if client.available:
                # Submit each batch as a client update
                for i, batch in enumerate(batches):
                    flat_params = []
                    for p in batch.primitives:
                        flat_params.extend(p.values)
                    if flat_params:
                        client.fl_submit_update(
                            client_id=f"ewa_client_{i}",
                            round_num=batch.round_id,
                            parameters=flat_params,
                            num_samples=len(batch.primitives),
                            entropy=float(np.mean([p.token_entropy for p in batch.primitives])) if batch.primitives else 0.0,
                        )
                agg_resp = client.fl_aggregate(strategy="ewa")
                # If FedCtx handled it, we still need to build prototypes locally
                # (FedCtx handles parameter aggregation, prototype building is domain-specific)
        except (ImportError, Exception):
            pass  # Fall through to local aggregation

        round_id = batches[0].round_id

        # Collect all primitives, filter by entropy threshold
        all_primitives = []
        for batch in batches:
            for p in batch.primitives:
                if p.token_entropy <= self.entropy_threshold:
                    all_primitives.append(p)

        total_input = sum(len(b.primitives) for b in batches)
        filtered_out = total_input - len(all_primitives)

        # Group by class
        class_groups = self.group_by_class(all_primitives)

        # Build class prototypes
        prototypes = []
        all_entropies = []

        for class_label, primitives in class_groups.items():
            proto = self._build_prototype(class_label, primitives, len(all_primitives))
            prototypes.append(proto)
            all_entropies.extend(p.token_entropy for p in primitives)

        # Global entropy stats
        entropy_arr = np.array(all_entropies) if all_entropies else np.array([0.0])
        entropy_stats = {
            "mean": round(float(np.mean(entropy_arr)), 4),
            "std": round(float(np.std(entropy_arr)), 4),
            "min": round(float(np.min(entropy_arr)), 4),
            "max": round(float(np.max(entropy_arr)), 4),
            "median": round(float(np.median(entropy_arr)), 4),
            "filtered_out": filtered_out,
            "threshold": self.entropy_threshold,
        }

        # Conformity report
        conformity_report = self._compute_conformity(prototypes)

        # Client summaries
        client_summaries = {}
        for batch in batches:
            if batch.primitives:
                entropies = [p.token_entropy for p in batch.primitives]
                client_summaries[batch.client_id] = {
                    "num_primitives": len(batch.primitives),
                    "avg_entropy": round(float(np.mean(entropies)), 4),
                    "filtered": sum(1 for p in batch.primitives
                                   if p.token_entropy > self.entropy_threshold),
                    "bytes": batch.size_bytes(),
                }

        return AggregationResult(
            round_id=round_id,
            prototypes=prototypes,
            total_input=total_input,
            strategy=self.strategy.value,
            entropy_stats=entropy_stats,
            conformity_report=conformity_report,
            client_summaries=client_summaries,
        )

    def _build_prototype(
        self,
        class_label: str,
        primitives: List[VisualPrimitive],
        total_primitives: int,
    ) -> ClassPrototype:
        """Build a class prototype from primitives of one class.

        Computes weighted statistics and per-client breakdown.
        """
        # Compute weights
        raw_weights = np.array([
            self.compute_weight(p.token_entropy, self.strategy) for p in primitives
        ])
        weights = raw_weights / np.sum(raw_weights)  # normalize for averaging

        # Weighted mean entropy
        mean_entropy = float(np.average(
            [p.token_entropy for p in primitives], weights=weights
        ))

        # Weighted mean confidence (from auxiliary)
        confidences = []
        for p in primitives:
            if p.auxiliary and "confidence" in p.auxiliary:
                confidences.append(p.auxiliary["confidence"])
            else:
                # Infer confidence from entropy: conf ≈ exp(-entropy)
                confidences.append(float(np.exp(-p.token_entropy)))
        mean_confidence = float(np.average(confidences, weights=weights))

        # Weighted mean area
        areas = []
        for p in primitives:
            if p.coords and len(p.coords[0]) >= 4:
                x1, y1, x2, y2 = p.coords[0][:4]
                areas.append(max(0, (x2 - x1) * (y2 - y1)))
            elif p.auxiliary and "area" in p.auxiliary:
                areas.append(p.auxiliary["area"])
        mean_area = float(np.average(areas, weights=weights[:len(areas)])) if areas else 0.0

        # Per-client breakdown
        client_primitives: Dict[str, List[VisualPrimitive]] = {}
        for p in primitives:
            client_primitives.setdefault(p.source_client, []).append(p)

        # Compute total weight for this class (use raw weights for share)
        total_class_weight = float(np.sum(raw_weights))
        client_stats = {}
        for cid, cprims in client_primitives.items():
            c_confs = []
            for cp in cprims:
                if cp.auxiliary and "confidence" in cp.auxiliary:
                    c_confs.append(cp.auxiliary["confidence"])
                else:
                    c_confs.append(float(np.exp(-cp.token_entropy)))
            client_weight = sum(
                self.compute_weight(cp.token_entropy, self.strategy) for cp in cprims
            )
            client_stats[cid] = {
                "count": len(cprims),
                "avg_entropy": round(float(np.mean([cp.token_entropy for cp in cprims])), 4),
                "avg_confidence": round(float(np.mean(c_confs)), 4),
                "weight_share": round(client_weight / max(total_class_weight, 1e-8) * 100, 2),
            }

        return ClassPrototype(
            ref=class_label,
            num_primitives=len(primitives),
            num_clients=len(client_primitives),
            client_ids=list(client_primitives.keys()),
            mean_entropy=round(mean_entropy, 4),
            mean_confidence=round(mean_confidence, 4),
            mean_area=round(mean_area, 2),
            prevalence=round(len(primitives) / max(total_primitives, 1), 4),
            client_stats=client_stats,
        )

    def _compute_conformity(self, prototypes: List[ClassPrototype]) -> Dict[str, Any]:
        """Compute conformity analysis across class prototypes.

        Conformity = how much the aggregated prototype deviates from
        what minority expert clients contribute.

        For each class:
        - If a high-confidence client contributes but its weight share
          is disproportionately low → potential suppression
        - If only low-confidence clients contribute → class may be unreliable
        """
        class_reports = {}
        total_suppressed = 0

        for proto in prototypes:
            if not proto.client_stats:
                continue

            # Find the most confident client for this class
            best_client = max(
                proto.client_stats.items(),
                key=lambda x: x[1]["avg_confidence"]
            )
            best_cid, best_stats = best_client

            # Find the majority client (most primitives)
            majority_client = max(
                proto.client_stats.items(),
                key=lambda x: x[1]["count"]
            )

            # Conformity score: if best expert != majority, and expert has
            # much higher confidence but much lower count → conformity issue
            if best_cid != majority_client[0]:
                expert_conf = best_stats["avg_confidence"]
                majority_conf = majority_client[1]["avg_confidence"]
                expert_count = best_stats["count"]
                majority_count = majority_client[1]["count"]

                # Expert has higher confidence but fewer detections
                if expert_conf > majority_conf + 0.1 and expert_count < majority_count:
                    # Expert's knowledge may be drowned out
                    suppression_ratio = 1.0 - (expert_count / max(majority_count, 1))
                    class_reports[proto.ref] = {
                        "conformity_score": round(suppression_ratio, 4),
                        "expert_client": best_cid,
                        "expert_confidence": expert_conf,
                        "expert_count": expert_count,
                        "majority_client": majority_client[0],
                        "majority_confidence": majority_conf,
                        "majority_count": majority_count,
                        "status": "suppressed" if suppression_ratio > 0.5 else "partial",
                    }
                    if suppression_ratio > 0.5:
                        total_suppressed += 1
                else:
                    class_reports[proto.ref] = {
                        "conformity_score": 0.0,
                        "status": "healthy",
                    }
            else:
                class_reports[proto.ref] = {
                    "conformity_score": 0.0,
                    "status": "healthy",
                }

        # Global conformity
        all_scores = [r["conformity_score"] for r in class_reports.values()]
        avg_conformity = round(float(np.mean(all_scores)), 4) if all_scores else 0.0
        high_conformity = sum(1 for s in all_scores if s > 0.5)

        return {
            "avg_conformity": avg_conformity,
            "high_conformity_count": high_conformity,
            "high_conformity_ratio": round(
                high_conformity / max(len(class_reports), 1), 4
            ),
            "minority_suppressed": total_suppressed,
            "per_class": class_reports,
        }

    # ── Comparison: FedAvg Baseline ───────────────────────────

    def compare_with_fedavg(
        self,
        batches: List[PrimitiveBatch],
    ) -> Dict[str, Any]:
        """Compare entropy-weighted vs equal-weight analysis."""
        ew_result = self.aggregate(batches)

        fedavg_agg = EntropyWeightedAggregator(
            strategy="equal_weight",
            entropy_threshold=self.entropy_threshold,
        )
        fedavg_result = fedavg_agg.aggregate(batches)

        return {
            "entropy_weighted": {
                "num_prototypes": ew_result.total_output,
                "avg_entropy": ew_result.entropy_stats.get("mean", 0),
                "conformity_ratio": ew_result.conformity_report.get("high_conformity_ratio", 0),
                "minority_suppressed": ew_result.conformity_report.get("minority_suppressed", 0),
            },
            "fedavg_baseline": {
                "num_prototypes": fedavg_result.total_output,
                "avg_entropy": fedavg_result.entropy_stats.get("mean", 0),
                "conformity_ratio": fedavg_result.conformity_report.get("high_conformity_ratio", 0),
                "minority_suppressed": fedavg_result.conformity_report.get("minority_suppressed", 0),
            },
            "improvement": {
                "conformity_reduction": round(
                    fedavg_result.conformity_report.get("high_conformity_ratio", 0)
                    - ew_result.conformity_report.get("high_conformity_ratio", 0), 4
                ),
                "entropy_reduction": round(
                    fedavg_result.entropy_stats.get("mean", 0)
                    - ew_result.entropy_stats.get("mean", 0), 4
                ),
            },
        }
