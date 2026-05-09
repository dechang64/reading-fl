# ── python/analysis/feature_extractor.py ──
"""
DINOv2 PCB Feature Extractor (twc-core wrapper)
=================================================
Delegates to twc_core.features.DINOv2Extractor.
"""

from twc_core.features import DINOv2Extractor

__all__ = ["DINOv2PCBExtractor"]


class DINOv2PCBExtractor(DINOv2Extractor):
    """DINOv2 feature extractor for PCB images — thin wrapper over twc_core."""

    pass  # All functionality inherited
