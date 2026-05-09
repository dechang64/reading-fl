# twc-core v0.1.0

**Unified ML Infrastructure for Federated Learning Projects**

Layer 1 shared modules extracted from 12 FL projects (organoid-fl, defect-fl, embodied-fl, FundFL, reading-fl, mural-restoration, embroidery-agent, TWC-FL-PROD, PAI).

## Architecture

```
Layer 3: Applications (Streamlit Apps, Papers, Products)
Layer 2: Domain Frameworks (organoid-fl, defect-fl, embodied-fl, ...)
Layer 1: twc-core (this package) ← shared Python ML modules
Layer 0: Rust Infrastructure (gRPC, HNSW native, Audit Chain native)
```

## Modules

| Module | Source | Description |
|--------|--------|-------------|
| `fl_engine` | TWC-FL-PROD | FedAvg + DP, NumPy-only, Streamlit Cloud compatible |
| `audit` | organoid-fl | SHA-256 audit chain, tamper detection |
| `features` | organoid-fl | DINOv2 (384/768/1024-dim) + ResNet18 feature extraction |
| `detector` | organoid-fl | Unified YOLOv11 wrapper |
| `gradcam` | organoid-fl | Grad-CAM explainability |
| `vector` | organoid-fl | In-memory cosine similarity search (HNSW fallback) |
| `ewa.primitives` | TWC-FL-PROD | Visual primitive codec (BOX/POINT/PATH) |
| `ewa.aggregator` | TWC-FL-PROD | Entropy-weighted aggregation + conformity detection |

## Quick Start

```python
from twc_core import FLEngine, AuditEngine, DINOv2Extractor, GradCAM, Detector
from twc_core import EntropyWeightedAggregator, PrimitiveCodec

# Federated Learning
engine = FLEngine(num_rounds=10)
engine.add_client("lab_a", num_samples=100)
engine.add_client("lab_b", num_samples=80)
for result in engine.run_simulation():
    print(f"Round {result.round_id}: loss={result.global_loss}")

# Audit Chain
audit = AuditEngine("my-project")
audit.append("training", {"round": 1, "loss": 0.34})
assert audit.verify_chain()

# Feature Extraction
extractor = DINOv2Extractor("facebook/dinov2-base")
features = extractor.extract("image.jpg")  # (768,)

# Object Detection
det = Detector(model_name="yolo11n.pt", classes=["healthy", "defect"])
detections = det.detect("image.jpg")

# Explainability
cam = GradCAM(model, target_layer=model.layer4)
heatmap = cam.generate(image_tensor)

# Entropy-Weighted Aggregation
codec = PrimitiveCodec()
agg = EntropyWeightedAggregator()
result = agg.aggregate(primitive_batches)
```

## Tests

```bash
python tests/test_core.py  # 56 tests, all pass
```

## Projects Using twc-core

- organoid-fl-upgrade (medical image FL)
- defect-fl-upgrade (PCB defect detection)
- embodied-fl-upgrade (robotics FL)
- fundfl-upgrade (fund risk analysis)
- reading-fl-upgrade (reading community FL)
- mural-restoration-upgrade (mural restoration)
- embroidery-agent (embroidery design)
- TWC-FL-PROD (unified FL platform)
- PAI (philanthropic asset intelligence)
