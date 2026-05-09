<div align="center">

### 📖 坐忘书房 · Reading-FL v2

**联邦学习驱动的AI读书会平台**

读者感悟永不离开设备 — 但情感理解在社群间流动

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c?logo=pytorch)](https://pytorch.org/)
[![DINOv2](https://img.shields.io/badge/DINOv2-Meta-blueviolet)](https://github.com/facebookresearch/dinov2)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

</div>

---

## 🆕 v2 Features

| Feature | v1 | v2 |
|---------|----|----|
| Feature Extraction | NumPy BoW (64-dim) | **DINOv2 + Sentence-BERT (768-dim)** |
| FL Engine | NumPy MLP | **PyTorch** (autograd + GPU) |
| Emotions | 6 types | **6 types** (joy, sadness, anger, fear, surprise, contemplation) |
| Predict API | — | **predict()** with probabilities |
| Backward Compat | — | **Legacy BOW mode** supported |

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Feature extraction
python -c "
from core.feature_extractor import ReadingFeatureExtractor
ext = ReadingFeatureExtractor(mode='legacy', dim=64)
vec = ext.extract_text('这本书让我感动得流泪')
print(f'Feature dim: {len(vec)}')
"

# Federated training
python -c "
from core.fl_engine import ReadingFLEngine
import numpy as np
engine = ReadingFLEngine(input_dim=64, num_emotions=6)
features = np.random.randn(200, 64).astype(np.float32)
labels = np.random.randint(0, 6, 200).astype(np.int64)
history = engine.run(features, labels, n_clients=3, rounds=5)
print(f'Final accuracy: {history[-1][\"val_acc\"]:.1%}')
"
```

## 📊 Tests

```bash
python -m pytest tests/ -v
# 10 passed
```

## 🤝 Related Projects

| Project | Domain | Shared Infra |
|---------|--------|-------------|
| [organoid-fl](https://github.com/dechang64/organoid-fl) | Medical imaging | DINOv2, FedAvg |
| [embodied-fl](https://github.com/dechang64/embodied-fl) | Robotics | DINOv2, Multi-Task FL |
| [defect-fl](https://github.com/dechang64/defect-fl) | PCB inspection | DINOv2, FedAvg |
| [FundFL](https://github.com/dechang64/fundfl) | Finance | HNSW, audit |

## 📄 License

Apache 2.0

---

<div align="center">

**Reading-FL v2** — 联邦学习驱动的AI读书会平台

</div>
