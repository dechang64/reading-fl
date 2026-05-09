# ── python/analysis/gradcam.py ──
"""
Grad-CAM for PCB Defect Classification (twc-core wrapper)
==========================================================
Delegates to twc_core.gradcam.GradCAM.
Adds PCB-specific defect report generation.
"""

import numpy as np
from typing import Optional
from twc_core.gradcam import GradCAM as _GradCAM

__all__ = ["GradCAM", "generate_defect_report"]


class GradCAM(_GradCAM):
    """PCB Defect-FL GradCAM — delegates to twc_core.gradcam.GradCAM."""
    pass


def generate_defect_report(
    heatmap: np.ndarray,
    defect_type: str,
    confidence: float,
    severity: str,
    morphology: Optional[dict] = None,
) -> str:
    """Human-readable defect analysis report."""
    lines = [
        f"## PCB Defect Analysis Report",
        f"",
        f"**Defect Type**: {defect_type.replace('_', ' ').title()}",
        f"**Confidence**: {confidence:.1%}",
        f"**Severity**: {severity.upper()}",
        f"",
        f"### Visual Attention",
    ]

    h, w = heatmap.shape
    center = heatmap[h//4:3*h//4, w//4:3*w//4].mean()
    edge = (heatmap.mean() - center * 0.25) / 0.75
    if center > edge:
        lines.append(f"- Model focused on **central defect region**")
    else:
        lines.append(f"- Model focused on **boundary/transition region** (subtle defect)")

    if morphology:
        lines.append(f"")
        lines.append(f"### Defect Morphology")
        lines.append(f"- Area: {morphology.get('area', 0)} px²")
        lines.append(f"- Circularity: {morphology.get('circularity', 0):.2f}")
        lines.append(f"- Solidity: {morphology.get('solidity', 0):.2f}")

    if severity == "critical":
        lines.append(f"")
        lines.append(f"⚠️ **CRITICAL**: Immediate inspection required. This defect may cause board failure.")

    lines.append(f"")
    lines.append(f"*Defect-FL Grad-CAM Analysis*")
    return "\n".join(lines)
