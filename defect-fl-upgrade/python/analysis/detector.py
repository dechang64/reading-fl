# ── python/analysis/detector.py ──
"""
YOLOv11 PCB Defect Detector (twc-core wrapper)
================================================
Delegates base detection to twc_core.detector.Detector.
PCBDefectDetector adds PCB-specific severity classification.
"""

import numpy as np
from twc_core.detector import Detection, Detector

__all__ = ["DefectDetection", "PCBDefectDetector"]


class DefectDetection(Detection):
    """PCB defect detection with severity classification."""

    def __init__(self, bbox, class_name, class_id, confidence,
                 cx=0, cy=0, width=0, height=0, area=0, severity="minor"):
        super().__init__(bbox=bbox, class_name=class_name,
                        class_id=class_id, confidence=confidence)
        self.severity = severity

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["severity"] = self.severity
        return d


class PCBDefectDetector(Detector):
    """YOLOv11-based PCB defect detector with severity mapping."""

    DEFECT_CLASSES = [
        "short_circuit", "open_circuit", "spurious_copper",
        "missing_hole", "spur", "good",
    ]

    SEVERITY_MAP = {
        "short_circuit": "critical",
        "open_circuit": "critical",
        "spurious_copper": "major",
        "missing_hole": "major",
        "spur": "minor",
        "good": "none",
    }

    def __init__(self, model_size: str = "n", device=None):
        super().__init__(model_name=f"yolo11{model_size}.pt",
                        classes=self.DEFECT_CLASSES)
        self.model_size = model_size

    def detect(self, image) -> list:
        """Detect defects in PCB image. Returns DefectDetection list."""
        if self.mock:
            return self._mock_detect(image)
        self._ensure_model()
        results = self.model(image)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_name = self.model.names[int(box.cls)]
                detections.append(DefectDetection(
                    bbox=box.xyxy[0].tolist(),
                    class_name=cls_name,
                    class_id=int(box.cls),
                    confidence=float(box.conf),
                    severity=self.SEVERITY_MAP.get(cls_name, "minor"),
                ))
        return detections

    def summary(self, detections: list) -> dict:
        """PCB-specific summary with defect rate and severity counts."""
        if not detections:
            return {"total": 0, "defects": 0, "severity": {}}
        defects = [d for d in detections if d.class_name != "good"]
        severity_counts = {}
        for d in defects:
            sev = d.severity if hasattr(d, 'severity') else "minor"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        return {
            "total": len(detections),
            "defects": len(defects),
            "defect_rate": len(defects) / max(len(detections), 1),
            "severity": severity_counts,
            "avg_confidence": round(float(np.mean([d.confidence for d in detections])), 4),
        }
