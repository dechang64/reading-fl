<div align="center">

# Defect-FL v2

### PCB Defect Federated Detection Platform

**Privacy-preserving PCB quality control — defect images never leave the factory.**

[![Rust](https://img.shields.io/badge/Rust-1.70+-orange?logo=rust)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c?logo=pytorch)](https://pytorch.org/)
[![YOLOv11](https://img.shields.io/badge/YOLO-v11-9b59b6)](https://docs.ultralytics.com/)
[![DINOv2](https://img.shields.io/badge/DINOv2-Meta-blueviolet)](https://github.com/facebookresearch/dinov2)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

</div>

---

## 🎯 Problem

PCB quality control needs deep learning, but:
- **Data silos**: Each factory's defect images are NDA-protected
- **Class imbalance**: Rare defects underrepresented in any single factory
- **Domain shift**: Different PCB designs → different defect distributions

## 🆕 v2 Features

| Feature | v1 | v2 |
|---------|----|----|
| Detection | — | **YOLOv11** (6 defect types) |
| Features | — | **DINOv2** (768-dim, self-supervised) |
| FL Engine | — | **FedAvg** with class imbalance weighting |
| Backend | — | **Rust** (HNSW + gRPC + audit chain) |
| Proto | — | **Complete gRPC** service definition |

## Defect Types

| # | Type | Severity |
|---|------|----------|
| 1 | Short Circuit | 🔴 Critical |
| 2 | Open Circuit | 🔴 Critical |
| 3 | Spurious Copper | 🟡 Major |
| 4 | Missing Hole | 🟡 Major |
| 5 | Spur | 🟢 Minor |
| 6 | Good | ✅ Normal |

## 🚀 Quick Start

```bash
# Server
cargo run

# Client
cd python && pip install -r requirements.txt
python -c "from analysis import PCBDefectDetector; print('OK')"
```

## 📊 Tests

```bash
cd python && python -m pytest tests/ -v
# 9 passed
```

## 🤝 Related Projects

| Project | Domain | Shared Infra |
|---------|--------|-------------|
| [organoid-fl](https://github.com/dechang64/organoid-fl) | Medical imaging | YOLOv11, DINOv2, SAM2, Grad-CAM |
| [embodied-fl](https://github.com/dechang64/embodied-fl) | Robotics | DINOv2, Multi-Task FL |
| [FundFL](https://github.com/dechang64/fundfl) | Finance | HNSW, audit chain |
| [Reading-FL](https://github.com/dechang64/reading-fl) | Reading | DINOv2, FedAvg |

## 📄 License

Apache-2.0

---

<div align="center">

**Defect-FL v2** — Privacy-preserving PCB defect detection via federated learning

</div>
