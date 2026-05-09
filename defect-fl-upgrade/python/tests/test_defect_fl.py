# ── python/tests/test_defect_fl.py ──
"""Tests for Defect-FL modules."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import numpy as np
import torch
from analysis.detector import PCBDefectDetector, DefectDetection
from analysis.feature_extractor import DINOv2PCBExtractor
from analysis.fl_engine import DefectFLEngine


class TestDefectDetection:
    def test_creation(self):
        d = DefectDetection(bbox=[10,20,100,200], class_name="short_circuit",
                           class_id=0, confidence=0.95, cx=55, cy=110,
                           width=90, height=180, area=16200, severity="critical")
        assert d.severity == "critical"

    def test_to_dict(self):
        d = DefectDetection(bbox=[0,0,50,50], class_name="spur",
                           class_id=4, confidence=0.8, cx=25, cy=25,
                           width=50, height=50, area=2500, severity="minor")
        assert d.to_dict()["severity"] == "minor"


class TestPCBDefectDetector:
    def test_init(self):
        det = PCBDefectDetector(model_size="n")
        assert len(det.DEFECT_CLASSES) == 6

    def test_summary_empty(self):
        det = PCBDefectDetector(model_size="n")
        assert det.summary([])["total"] == 0

    def test_severity_map(self):
        det = PCBDefectDetector(model_size="n")
        assert det.SEVERITY_MAP["short_circuit"] == "critical"
        assert det.SEVERITY_MAP["spur"] == "minor"


class TestDINOv2PCBExtractor:
    def test_dims(self):
        assert DINOv2PCBExtractor.MODEL_DIMS["base"] == 768


class TestDefectFLEngine:
    def test_init(self):
        engine = DefectFLEngine(input_dim=64, num_classes=6, hidden_dim=16)
        assert engine.num_classes == 6

    def test_training(self):
        engine = DefectFLEngine(input_dim=64, num_classes=6, hidden_dim=16, lr=0.01, local_epochs=1)
        features = np.random.randn(200, 64).astype(np.float32)
        labels = np.random.randint(0, 6, 200).astype(np.int64)
        history = engine.run(features, labels, n_clients=3, rounds=3)
        assert len(history) == 3
        assert history[-1]["val_acc"] >= 0.05

    def test_classifier_dims(self):
        engine = DefectFLEngine(input_dim=128, num_classes=6)
        x = torch.randn(2, 128)
        assert engine.classifier(x).shape == (2, 6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
