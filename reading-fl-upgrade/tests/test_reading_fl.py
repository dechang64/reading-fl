# ── tests/test_reading_fl.py ──
"""Tests for Reading-FL v2 modules."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import numpy as np
import torch
from core.feature_extractor import ReadingFeatureExtractor
from core.fl_engine import ReadingFLEngine


class TestReadingFeatureExtractor:
    def test_legacy_mode(self):
        ext = ReadingFeatureExtractor(mode="legacy", dim=64)
        vec = ext.extract_text("这本书让我感动得流泪")
        assert len(vec) == 64
        assert vec.dtype == np.float32

    def test_consistency(self):
        ext = ReadingFeatureExtractor(mode="legacy", dim=64)
        v1 = ext.extract_text("测试文本")
        v2 = ext.extract_text("测试文本")
        assert np.allclose(v1, v2)

    def test_different_texts(self):
        ext = ReadingFeatureExtractor(mode="legacy", dim=64)
        v1 = ext.extract_text("这是一本关于爱情的小说")
        v2 = ext.extract_text("量子力学的数学基础")
        assert not np.allclose(v1, v2)

    def test_cosine_similarity(self):
        ext = ReadingFeatureExtractor(mode="legacy", dim=64)
        v1 = ext.extract_text("人工智能的未来")
        v2 = ext.extract_text("AI的发展趋势")
        sim = ReadingFeatureExtractor.cosine_similarity(v1, v2)
        assert 0 <= sim <= 1

    def test_visual_fallback(self):
        ext = ReadingFeatureExtractor(mode="legacy", dim=64)
        vec = ext.extract_visual("/nonexistent/image.jpg")
        assert len(vec) == 64


class TestReadingFLEngine:
    def test_init(self):
        engine = ReadingFLEngine(input_dim=64, num_emotions=6, hidden_dim=16)
        assert engine.num_emotions == 6

    def test_training(self):
        engine = ReadingFLEngine(input_dim=64, num_emotions=6, hidden_dim=16, lr=0.01, local_epochs=1)
        features = np.random.randn(200, 64).astype(np.float32)
        labels = np.random.randint(0, 6, 200).astype(np.int64)
        history = engine.run(features, labels, n_clients=3, rounds=3)
        assert len(history) == 3
        assert history[-1]["val_acc"] > 0.05

    def test_classifier_dims(self):
        engine = ReadingFLEngine(input_dim=128, num_emotions=6)
        x = torch.randn(2, 128)
        assert engine.classifier(x).shape == (2, 6)

    def test_predict(self):
        engine = ReadingFLEngine(input_dim=64, num_emotions=6, hidden_dim=16)
        features = np.random.randn(5, 64).astype(np.float32)
        preds, probs = engine.predict(features)
        assert preds.shape == (5,)
        assert probs.shape == (5, 6)
        assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)

    def test_emotions_list(self):
        assert len(ReadingFLEngine.EMOTIONS) == 6
        assert "joy" in ReadingFLEngine.EMOTIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
