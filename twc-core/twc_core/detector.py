"""
twc_core.detector — YOLOv11 Object Detector
=============================================
Unified detector extracted from organoid-fl (OrganoidDetector),
defect-fl (PCBDefectDetector), and embodied-fl (RobotSceneDetector).

Usage:
    from twc_core.detector import Detector
    det = Detector(model_name="yolo11n.pt", classes=["healthy", "defect"])
    detections = det.detect("image.jpg")
    print(det.summary(detections))
"""

from __future__ import annotations
import numpy as np
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Detection:
    """Single detection result."""
    bbox: list  # [x1, y1, x2, y2]
    class_name: str
    class_id: int
    confidence: float
    cx: float = 0.0
    cy: float = 0.0
    width: float = 0.0
    height: float = 0.0
    area: float = 0.0

    def __post_init__(self):
        if len(self.bbox) == 4:
            self.cx = (self.bbox[0] + self.bbox[2]) / 2
            self.cy = (self.bbox[1] + self.bbox[3]) / 2
            self.width = self.bbox[2] - self.bbox[0]
            self.height = self.bbox[3] - self.bbox[1]
            self.area = self.width * self.height

    def to_dict(self) -> dict:
        return {
            "bbox": self.bbox, "class_name": self.class_name,
            "class_id": self.class_id, "confidence": self.confidence,
            "cx": self.cx, "cy": self.cy,
            "width": self.width, "height": self.height, "area": self.area,
        }


class Detector:
    """Unified YOLOv11 detector for any domain.

    Usage:
        det = Detector(model_name="yolo11n.pt", classes=["cat", "dog"])
        det.train_local("data.yaml", epochs=50)
        results = det.detect("image.jpg")
    """

    def __init__(self, model_name: str = "yolo11n.pt", classes: Optional[List[str]] = None):
        self.model_name = model_name
        self.classes = classes or []
        self._model = None

    def _ensure_model(self):
        """Lazy-load YOLO model."""
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.model_name)

    def detect(self, image_path: str, conf_threshold: float = 0.25) -> List[Detection]:
        """Run detection on an image.

        Args:
            image_path: Path to image file.
            conf_threshold: Minimum confidence threshold.

        Returns:
            List of Detection objects.
        """
        self._ensure_model()
        results = self._model(image_path, conf=conf_threshold)
        detections = []

        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = self.classes[cls_id] if cls_id < len(self.classes) else f"class_{cls_id}"
                detections.append(Detection(
                    bbox=xyxy, class_name=cls_name,
                    class_id=cls_id, confidence=conf,
                ))
        return detections

    def train_local(self, data_yaml: str, epochs: int = 50, **kwargs):
        """Train model on local data.

        Args:
            data_yaml: Path to YOLO data.yaml config.
            epochs: Number of training epochs.
        """
        self._ensure_model()
        self._model.train(data=data_yaml, epochs=epochs, **kwargs)

    def export_weights(self) -> dict:
        """Export model weights for FL aggregation."""
        self._ensure_model()
        return {k: v.cpu().numpy() for k, v in self._model.model.state_dict().items()}

    def load_weights(self, state_dict: dict):
        """Load aggregated weights from FL server."""
        import torch
        self._ensure_model()
        state = {k: torch.tensor(v) for k, v in state_dict.items()}
        try:
            self._model.model.load_state_dict(state)
        except RuntimeError as e:
            raise ValueError(
                f"Weight shape mismatch: {e}. "
                "Ensure the state dict comes from a compatible model."
            ) from e

    def get_trainable_params(self) -> dict:
        """Alias for export_weights (FL interface compatibility)."""
        return self.export_weights()

    def count_by_class(self, detections: List[Detection]) -> dict:
        """Count detections per class."""
        counts = {}
        for d in detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return counts

    def summary(self, detections: List[Detection]) -> dict:
        """Generate detection summary statistics."""
        if not detections:
            return {"total": 0, "classes": {}, "avg_confidence": 0, "avg_area": 0}
        return {
            "total": len(detections),
            "classes": self.count_by_class(detections),
            "avg_confidence": round(float(np.mean([d.confidence for d in detections])), 4),
            "avg_area": round(float(np.mean([d.area for d in detections])), 2),
            "min_area": round(float(min(d.area for d in detections)), 2),
            "max_area": round(float(max(d.area for d in detections)), 2),
        }
