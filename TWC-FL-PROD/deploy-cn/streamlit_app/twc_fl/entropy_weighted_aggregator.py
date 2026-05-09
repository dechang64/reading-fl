"""
Module G: Entropy-Weighted Aggregator

Aggregates visual primitives from multiple FL clients using token entropy
as confidence weights. Replaces naive FedAvg for multimodal FL scenarios.

Core idea:
    - Low entropy (high confidence) primitives get higher weight
    - High entropy (uncertain) primitives get lower weight
    - This naturally suppresses conformity: majority clients with uncertain
      outputs cannot drown out minority clients with confident, correct outputs

Privacy guarantee: aggregation operates on structured primitives only,
never on raw images or raw model parameters.

Pure NumPy implementation. No PyTorch dependency. Streamlit Cloud compatible.
"""
from __future__ import annotations

import numpy as np
import json
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .primitive_codec import (
    VisualPrimitive, PrimitiveBatch, PrimitiveType, PrimitiveCodec,
)


class AggregationStrategy(Enum):
    """How to weight primitives during aggregation."""
    ENTROPY_WEIGHTED = "entropy_weighted"   # Default: weight = 1/H
    EQUAL_WEIGHT = "equal_weight"           # Baseline: uniform weight
    CONFIDENCE_WEIGHTED = "confidence"      # weight = exp(-H)
    INVERSE_ENTROPY = "inverse_entropy"     # weight = 1/(H + epsilon)


@dataclass
class AggregatedPrimitive:
    """Result of aggregating multiple primitives for the same semantic concept.

    Attributes:
        ref: Aggregated semantic label (majority vote).
        primitive_type: BOX, POINT, or PATH.
        coords: Aggregated coordinates (median of weighted inputs).
        mean_entropy: Average entropy across contributing primitives.
        weight: Total aggregation weight.
        num_contributors: Number of clients that contributed.
        contributor_ids: List of contributing client IDs.
        conformity_score: 0-1, how much the result was dominated by majority.
            High score = potential conformity suppression issue.
    """
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


@dataclass
class AggregationResult:
    """Result of one round of entropy-weighted primitive aggregation.

    Attributes:
        round_id: FL round number.
        aggregated: List of aggregated primitives.
        total_input: Total primitives received from all clients.
        total_output: Total primitives after aggregation.
        strategy: Aggregation strategy used.
        entropy_stats: Statistics about entropy distribution.
        conformity_report: Analysis of conformity effects.
        client_summaries: Per-client contribution summary.
    """
    round_id: int
    aggregated: List[AggregatedPrimitive]
    total_input: int
    total_output: int
    strategy: str
    entropy_stats: Dict[str, float] = field(default_factory=dict)
    conformity_report: Dict[str, Any] = field(default_factory=dict)
    client_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "round_id": self.round_id,
            "aggregated": [a.to_dict() for a in self.aggregated],
            "total_input": self.total_input,
            "total_output": self.total_output,
            "strategy": self.strategy,
            "entropy_stats": self.entropy_stats,
            "conformity_report": self.conformity_report,
            "client_summaries": self.client_summaries,
        }, ensure_ascii=False)


class EntropyWeightedAggregator:
    """Entropy-weighted aggregator for visual primitives.

    Usage:
        agg = EntropyWeightedAggregator(strategy="entropy_weighted")
        result = agg.aggregate(batches)  # List[PrimitiveBatch]
    """

    def __init__(
        self,
        strategy: str = "entropy_weighted",
        entropy_threshold: float = 5.0,
        iou_threshold: float = 0.3,
        min_contributors: int = 1,
    ):
        """Initialize aggregator.

        Args:
            strategy: Aggregation strategy name.
            entropy_threshold: Primitives with entropy above this are filtered out.
                Default 5.0 corresponds to ~exp(-5) ≈ 0.7% confidence.
            iou_threshold: IoU threshold for matching primitives across clients.
                Used to group primitives that refer to the same object.
            min_contributors: Minimum number of clients required for aggregation.
        """
        self.strategy = AggregationStrategy(strategy)
        self.entropy_threshold = entropy_threshold
        self.iou_threshold = iou_threshold
        self.min_contributors = min_contributors

    # ── Weight Computation ────────────────────────────────────

    @staticmethod
    def compute_weight(entropy: float, strategy: AggregationStrategy) -> float:
        """Compute aggregation weight from entropy.

        Args:
            entropy: Shannon entropy value.
            strategy: Weighting strategy.

        Returns:
            Non-negative weight. Higher = more trusted.
        """
        eps = 1e-8

        if strategy == AggregationStrategy.EQUAL_WEIGHT:
            return 1.0

        elif strategy == AggregationStrategy.ENTROPY_WEIGHTED:
            # weight = 1 / (1 + H)
            return 1.0 / (1.0 + entropy)

        elif strategy == AggregationStrategy.CONFIDENCE_WEIGHTED:
            # weight = exp(-H), maps entropy to [0, 1]
            return np.exp(-entropy)

        elif strategy == AggregationStrategy.INVERSE_ENTROPY:
            # weight = 1 / (H + eps)
            return 1.0 / (entropy + eps)

        return 1.0

    # ── Primitive Matching ────────────────────────────────────

    @staticmethod
    def compute_iou(box_a: List[int], box_b: List[int]) -> float:
        """Compute IoU between two normalized bounding boxes.

        Args:
            box_a, box_b: [x1, y1, x2, y2] in 0-999 coordinates.
        """
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union = area_a + area_b - intersection

        return intersection / max(union, 1e-8)

    @staticmethod
    def compute_point_distance(pt_a: List[int], pt_b: List[int]) -> float:
        """Euclidean distance between two normalized points."""
        return np.sqrt((pt_a[0] - pt_b[0]) ** 2 + (pt_a[1] - pt_b[1]) ** 2)

    def match_primitives(
        self,
        primitives: List[VisualPrimitive],
    ) -> List[List[VisualPrimitive]]:
        """Group primitives across clients that refer to the same object.

        Uses IoU for boxes and distance for points.

        Args:
            primitives: All primitives from all clients for one round.

        Returns:
            List of groups, where each group contains matched primitives.
        """
        if not primitives:
            return []

        # Separate by type
        by_type: Dict[PrimitiveType, List[VisualPrimitive]] = {}
        for p in primitives:
            by_type.setdefault(p.primitive_type, []).append(p)

        groups = []

        # Match BOX primitives by IoU
        if PrimitiveType.BOX in by_type:
            boxes = by_type[PrimitiveType.BOX]
            used = [False] * len(boxes)

            for i, p1 in enumerate(boxes):
                if used[i]:
                    continue
                group = [p1]
                used[i] = True

                for j in range(i + 1, len(boxes)):
                    if used[j]:
                        continue
                    p2 = boxes[j]

                    # Must be from different clients
                    if p1.source_client == p2.source_client:
                        continue

                    # Check IoU
                    if p1.coords and p2.coords and len(p1.coords[0]) == 4 and len(p2.coords[0]) == 4:
                        iou = self.compute_iou(p1.coords[0], p2.coords[0])
                        if iou >= self.iou_threshold:
                            group.append(p2)
                            used[j] = True

                groups.append(group)

        # Match POINT primitives by distance
        if PrimitiveType.POINT in by_type:
            points = by_type[PrimitiveType.POINT]
            used = [False] * len(points)
            distance_threshold = 50  # 5% of 999 coordinate space

            for i, p1 in enumerate(points):
                if used[i]:
                    continue
                group = [p1]
                used[i] = True

                for j in range(i + 1, len(points)):
                    if used[j]:
                        continue
                    p2 = points[j]

                    if p1.source_client == p2.source_client:
                        continue

                    if p1.coords and p2.coords and len(p1.coords[0]) == 2 and len(p2.coords[0]) == 2:
                        dist = self.compute_point_distance(p1.coords[0], p2.coords[0])
                        if dist <= distance_threshold:
                            group.append(p2)
                            used[j] = True

                groups.append(group)

        # PATH primitives: group by label similarity
        if PrimitiveType.PATH in by_type:
            paths = by_type[PrimitiveType.PATH]
            label_groups: Dict[str, List[VisualPrimitive]] = {}
            for p in paths:
                label_groups.setdefault(p.ref, []).append(p)
            groups.extend(label_groups.values())

        return groups

    # ── Aggregation ───────────────────────────────────────────

    def aggregate(
        self,
        batches: List[PrimitiveBatch],
    ) -> AggregationResult:
        """Aggregate primitives from multiple clients.

        Args:
            batches: List of PrimitiveBatch from different clients.

        Returns:
            AggregationResult with aggregated primitives and analysis.
        """
        if not batches:
            return AggregationResult(
                round_id=0, aggregated=[], total_input=0, total_output=0,
                strategy=self.strategy.value,
            )

        round_id = batches[0].round_id

        # Collect all primitives
        all_primitives = []
        client_counts: Dict[str, int] = {}

        for batch in batches:
            client_counts[batch.client_id] = len(batch.primitives)
            for p in batch.primitives:
                # Filter by entropy threshold
                if p.token_entropy <= self.entropy_threshold:
                    all_primitives.append(p)

        total_input = sum(len(b.primitives) for b in batches)
        filtered_out = total_input - len(all_primitives)

        # Match primitives across clients
        groups = self.match_primitives(all_primitives)

        # Aggregate each group
        aggregated = []
        all_entropies = []

        for group in groups:
            if len(group) < self.min_contributors:
                # Singleton: keep as-is
                p = group[0]
                w = self.compute_weight(p.token_entropy, self.strategy)
                aggregated.append(AggregatedPrimitive(
                    ref=p.ref,
                    primitive_type=p.primitive_type,
                    coords=p.coords,
                    mean_entropy=p.token_entropy,
                    weight=w,
                    num_contributors=1,
                    contributor_ids=[p.source_client],
                    conformity_score=0.0,
                ))
                all_entropies.append(p.token_entropy)
                continue

            # Compute weights
            weights = np.array([
                self.compute_weight(p.token_entropy, self.strategy) for p in group
            ])
            weights = weights / np.sum(weights)  # normalize

            # Weighted coordinate aggregation (median for robustness)
            if group[0].primitive_type == PrimitiveType.BOX and group[0].coords:
                n_coords = len(group[0].coords[0])  # typically 4
                agg_coords = []
                for dim in range(n_coords):
                    dim_values = [p.coords[0][dim] for p in group if p.coords and len(p.coords[0]) > dim]
                    if dim_values:
                        dim_weights = weights[:len(dim_values)]
                        # Weighted median
                        sorted_idx = np.argsort(dim_values)
                        sorted_vals = np.array(dim_values)[sorted_idx]
                        sorted_w = dim_weights[sorted_idx]
                        cum_w = np.cumsum(sorted_w)
                        median_idx = np.searchsorted(cum_w, 0.5)
                        agg_coords.append(int(sorted_vals[min(median_idx, len(sorted_vals) - 1)]))
                coords = [agg_coords]
            elif group[0].primitive_type == PrimitiveType.POINT and group[0].coords:
                n_coords = len(group[0].coords[0])  # typically 2
                agg_coords = []
                for dim in range(n_coords):
                    dim_values = [p.coords[0][dim] for p in group if p.coords and len(p.coords[0]) > dim]
                    if dim_values:
                        dim_weights = weights[:len(dim_values)]
                        sorted_idx = np.argsort(dim_values)
                        sorted_vals = np.array(dim_values)[sorted_idx]
                        sorted_w = dim_weights[sorted_idx]
                        cum_w = np.cumsum(sorted_w)
                        median_idx = np.searchsorted(cum_w, 0.5)
                        agg_coords.append(int(sorted_vals[min(median_idx, len(sorted_vals) - 1)]))
                coords = [agg_coords]
            else:
                coords = group[0].coords

            # Majority vote for label
            ref_counts: Dict[str, float] = {}
            for p, w in zip(group, weights):
                ref_counts[p.ref] = ref_counts.get(p.ref, 0) + w
            best_ref = max(ref_counts, key=ref_counts.get)

            # Entropy stats
            entropies = [p.token_entropy for p in group]
            mean_ent = float(np.mean(entropies))
            all_entropies.extend(entropies)

            # Conformity score: how much one client dominates
            client_weights: Dict[str, float] = {}
            for p, w in zip(group, weights):
                client_weights[p.source_client] = client_weights.get(p.source_client, 0) + w
            max_client_w = max(client_weights.values())
            conformity = max_client_w  # 1.0 = single client dominates

            total_w = float(np.sum(weights))

            aggregated.append(AggregatedPrimitive(
                ref=best_ref,
                primitive_type=group[0].primitive_type,
                coords=coords,
                mean_entropy=mean_ent,
                weight=total_w,
                num_contributors=len(group),
                contributor_ids=list(set(p.source_client for p in group)),
                conformity_score=conformity,
            ))

        # Entropy statistics
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
        conformity_scores = [a.conformity_score for a in aggregated]
        high_conformity = sum(1 for s in conformity_scores if s > 0.7)
        conformity_report = {
            "avg_conformity": round(float(np.mean(conformity_scores)), 4) if conformity_scores else 0.0,
            "high_conformity_count": high_conformity,
            "high_conformity_ratio": round(high_conformity / max(len(aggregated), 1), 4),
            "minority_suppressed": high_conformity,  # primitives where 1 client > 70% weight
        }

        # Client summaries
        client_summaries = {}
        for batch in batches:
            if batch.primitives:
                entropies = [p.token_entropy for p in batch.primitives]
                client_summaries[batch.client_id] = {
                    "num_primitives": len(batch.primitives),
                    "avg_entropy": round(float(np.mean(entropies)), 4),
                    "filtered": sum(1 for p in batch.primitives if p.token_entropy > self.entropy_threshold),
                    "bytes": batch.size_bytes(),
                }

        return AggregationResult(
            round_id=round_id,
            aggregated=aggregated,
            total_input=total_input,
            total_output=len(aggregated),
            strategy=self.strategy.value,
            entropy_stats=entropy_stats,
            conformity_report=conformity_report,
            client_summaries=client_summaries,
        )

    # ── Comparison: FedAvg Baseline ───────────────────────────

    def compare_with_fedavg(
        self,
        batches: List[PrimitiveBatch],
    ) -> Dict[str, Any]:
        """Compare entropy-weighted aggregation vs equal-weight (FedAvg) baseline.

        Args:
            batches: List of PrimitiveBatch from different clients.

        Returns:
            Comparison report with metrics for both strategies.
        """
        # Entropy-weighted
        ew_result = self.aggregate(batches)

        # FedAvg baseline (equal weight)
        fedavg_agg = EntropyWeightedAggregator(
            strategy="equal_weight",
            entropy_threshold=self.entropy_threshold,
            iou_threshold=self.iou_threshold,
        )
        fedavg_result = fedavg_agg.aggregate(batches)

        return {
            "entropy_weighted": {
                "output_count": ew_result.total_output,
                "avg_entropy": ew_result.entropy_stats.get("mean", 0),
                "conformity_ratio": ew_result.conformity_report.get("high_conformity_ratio", 0),
                "minority_suppressed": ew_result.conformity_report.get("minority_suppressed", 0),
            },
            "fedavg_baseline": {
                "output_count": fedavg_result.total_output,
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
