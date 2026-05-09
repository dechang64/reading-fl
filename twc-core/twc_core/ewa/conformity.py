"""
twc_core.ewa.conformity — Conformity Detector (v2)
===================================================
Tracks class-level conformity across FL rounds.

Monitors whether minority expert clients' domain knowledge is being
suppressed by majority clients in the aggregated class prototypes.

Usage:
    from twc_core.ewa.conformity import ConformityDetector
    detector = ConformityDetector()
    for round_result in fl_rounds:
        detector.update(round_result)
    report = detector.get_report()
"""
from __future__ import annotations

import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class RoundSnapshot:
    """Conformity metrics for one FL round."""
    round_id: int
    avg_conformity: float
    high_conformity_ratio: float
    minority_suppressed: int
    avg_entropy: float
    num_clients: int
    num_primitives: int
    num_classes: int
    strategy: str
    # Per-class detail
    class_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ConformityAlert:
    """Alert when conformity exceeds threshold."""
    round_id: int
    severity: str  # "warning" | "critical"
    class_label: str
    message: str
    details: Dict[str, Any]


class ConformityDetector:
    """Tracks conformity trends across FL rounds.

    Conformity score per class: 0.0 (healthy) to 1.0 (total suppression).
    - 0.0: No conformity issue detected
    - 0.5: Partial suppression — expert contributes but is underweighted
    - 1.0: Total suppression — expert's knowledge absent from prototype

    Global conformity: average across all classes.
    """

    def __init__(
        self,
        warning_threshold: float = 0.5,
        critical_threshold: float = 0.8,
        window_size: int = 5,
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.window_size = window_size
        self.history: List[RoundSnapshot] = []
        self.alerts: List[ConformityAlert] = []

    def update(self, aggregation_result) -> RoundSnapshot:
        """Record conformity metrics from one aggregation round.

        Args:
            aggregation_result: AggregationResult from EntropyWeightedAggregator.

        Returns:
            RoundSnapshot for this round.
        """
        conf_report = aggregation_result.conformity_report
        ent_stats = aggregation_result.entropy_stats
        per_class = conf_report.get("per_class", {})

        # Check per-class conformity and generate alerts
        for class_label, class_info in per_class.items():
            score = class_info.get("conformity_score", 0.0)
            status = class_info.get("status", "healthy")

            if status == "suppressed" and score >= self.critical_threshold:
                self.alerts.append(ConformityAlert(
                    round_id=aggregation_result.round_id,
                    severity="critical",
                    class_label=class_label,
                    message=f"Critical: {class_label} — expert knowledge likely suppressed "
                            f"(conformity={score:.2f})",
                    details=class_info,
                ))
            elif status == "partial" and score >= self.warning_threshold:
                self.alerts.append(ConformityAlert(
                    round_id=aggregation_result.round_id,
                    severity="warning",
                    class_label=class_label,
                    message=f"Warning: {class_label} — partial conformity detected "
                            f"(conformity={score:.2f})",
                    details=class_info,
                ))

        snapshot = RoundSnapshot(
            round_id=aggregation_result.round_id,
            avg_conformity=conf_report.get("avg_conformity", 0.0),
            high_conformity_ratio=conf_report.get("high_conformity_ratio", 0.0),
            minority_suppressed=conf_report.get("minority_suppressed", 0),
            avg_entropy=ent_stats.get("mean", 0.0),
            num_clients=len(aggregation_result.client_summaries),
            num_primitives=aggregation_result.total_input,
            num_classes=aggregation_result.total_output,
            strategy=aggregation_result.strategy,
            class_details=per_class,
        )
        self.history.append(snapshot)
        return snapshot

    def get_trend(self) -> Dict[str, Any]:
        """Analyze conformity trend over recent rounds."""
        if len(self.history) < 2:
            return {"status": "insufficient_data", "rounds": len(self.history)}

        recent = self.history[-self.window_size:]
        conformities = [s.avg_conformity for s in recent]

        x = np.arange(len(conformities))
        if len(conformities) > 1:
            slope = float(np.polyfit(x, conformities, 1)[0])
        else:
            slope = 0.0

        if slope > 0.02:
            direction = "rising"
        elif slope < -0.02:
            direction = "falling"
        else:
            direction = "stable"

        return {
            "status": direction,
            "current": round(conformities[-1], 4),
            "slope": round(slope, 4),
            "window_avg": round(float(np.mean(conformities)), 4),
            "window_max": round(float(np.max(conformities)), 4),
            "window_min": round(float(np.min(conformities)), 4),
            "total_rounds": len(self.history),
            "total_alerts": len(self.alerts),
        }

    def get_report(self) -> Dict[str, Any]:
        """Generate full conformity report."""
        trend = self.get_trend()

        # Per-class analysis from most recent round
        class_analysis = {}
        if self.history:
            latest = self.history[-1]
            class_analysis = latest.class_details

        # Recommendations
        recommendations = []
        if trend["status"] == "rising":
            recommendations.append(
                "Conformity is increasing. Consider: "
                "(1) Adding more diverse clients, "
                "(2) Using entropy-weighted aggregation, "
                "(3) Reviewing data distribution for severe Non-IID."
            )
        critical_count = sum(1 for a in self.alerts if a.severity == "critical")
        if critical_count > 0:
            recommendations.append(
                f"{critical_count} critical alerts. "
                "Minority expertise may be lost. "
                "Review client data quality and class balance."
            )
        if not recommendations:
            recommendations.append("Conformity levels are healthy. No action needed.")

        return {
            "trend": trend,
            "class_analysis": class_analysis,
            "alerts": [
                {"round": a.round_id, "severity": a.severity,
                 "class": a.class_label, "message": a.message,
                 "details": a.details}
                for a in self.alerts[-20:]
            ],
            "recommendations": recommendations,
            "total_rounds_tracked": len(self.history),
        }

    def reset(self):
        """Clear all history and alerts."""
        self.history = []
        self.alerts = []
