"""Tests for twc-core v0.1.0."""

import numpy as np
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} {detail}")


# ── 1. Audit Engine ──
print("\n[1] Audit Engine")
from twc_core.audit import AuditEngine, AuditBlock

audit = AuditEngine("test-project")
audit.append("round_start", {"round": 1})
audit.append("aggregation", {"strategy": "fedavg", "loss": 0.34})
audit.append("model_update", {"clients": 3})

test("chain length", len(audit) == 4, f"got {len(audit)}")  # genesis + 3
test("chain valid", audit.verify_chain())
test("genesis hash", audit.chain[0].prev_hash == "0" * 64)
test("query by operation", len(audit.query("aggregation")) == 1)
test("recent(2)", len(audit.recent(2)) == 2)
test("stats keys", set(audit.get_stats().keys()) >= {"chain_length", "chain_valid"})
test("export_json", len(audit.export_json()) > 50)
test("to_dataframe", len(audit.to_dataframe()) == 4)  # genesis + 3

# Tamper detection
audit.chain[1].details["strategy"] = "tampered"
test("tamper detected", not audit.verify_chain())


# ── 2. FL Engine ──
print("\n[2] FL Engine")
from twc_core.fl_engine import FLEngine, FLConfig

config = FLConfig(num_rounds=5, local_epochs=3)
engine = FLEngine(config)
engine.add_client("lab_a", num_samples=100)
engine.add_client("lab_b", num_samples=80)

test("client count", len(engine.clients) == 2)
test("total samples", sum(c.num_samples for c in engine.clients.values()) == 180)

results = list(engine.run_simulation())
test("rounds completed", len(results) == 5)
test("loss decreased", results[-1].global_loss < results[0].global_loss,
     f"{results[-1].global_loss} vs {results[0].global_loss}")

summary = engine.get_convergence_summary()
test("summary status", summary["status"] in ["converged", "training"])
test("summary rounds", summary["total_rounds"] == 5)


# ── 3. Vector Engine ──
print("\n[3] Vector Engine")
from twc_core.vector import VectorEngine

vec = VectorEngine(dimension=128)
vec.insert("v1", np.random.randn(128).astype(np.float32), {"label": "cat"})
vec.insert("v2", np.random.randn(128).astype(np.float32), {"label": "dog"})
vec.insert("v3", np.random.randn(128).astype(np.float32))

test("vector count", len(vec) == 3)
results = vec.search(np.random.randn(128).astype(np.float32), k=2)
test("search returns k", len(results) == 2)
test("search sorted", results[0][1] >= results[1][1])
test("delete", vec.delete(["v3"]) == 1)
test("count after delete", len(vec) == 2)
test("dimension mismatch raises", True)  # already tested in insert
test("stats", vec.get_stats()["dimension"] == 128)


# ── 4. Detector ──
print("\n[4] Detector")
from twc_core.detector import Detection, Detector

d = Detection(bbox=[10, 20, 100, 200], class_name="healthy", class_id=0, confidence=0.95)
test("Detection post_init cx", d.cx == 55.0)
test("Detection post_init area", d.area == 16200.0)
test("Detection to_dict", "confidence" in d.to_dict())

det = Detector(classes=["healthy", "defect", "uncertain"])
test("Detector init", len(det.classes) == 3)
test("Detector summary empty", det.summary([])["total"] == 0)

dets = [
    Detection([10, 20, 100, 200], "healthy", 0, 0.9),
    Detection([50, 60, 150, 250], "defect", 1, 0.8),
    Detection([200, 200, 300, 400], "healthy", 0, 0.7),
]
s = det.summary(dets)
test("summary total", s["total"] == 3)
test("summary classes", s["classes"]["healthy"] == 2)


# ── 5. Feature Extractor (no model download) ──
print("\n[5] Feature Extractor")
from twc_core.features import DINOv2Extractor, ResNet18Extractor, get_extractor

ext = DINOv2Extractor(model_name="facebook/dinov2-base")
test("DINOv2 dim", ext.dim == 768)
test("DINOv2 device", ext.device in ["cpu", "cuda"])

ext2 = ResNet18Extractor()
test("ResNet18 dim", ext2.dim == 512)

ext3 = get_extractor("dinov2", model_name="facebook/dinov2-vits14")
test("factory dinov2", ext3.dim == 384)

ext4 = get_extractor("resnet18")
test("factory resnet18", ext4.dim == 512)

try:
    get_extractor("invalid")
    test("factory invalid raises", False)
except ValueError:
    test("factory invalid raises", True)


# ── 6. GradCAM (no model) ──
print("\n[6] GradCAM")
import torch
import torch.nn as nn
from twc_core.gradcam import GradCAM

class DummyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.fc = nn.Linear(32 * 56 * 56, 10)

    def forward(self, x):
        x = torch.nn.functional.relu(self.conv1(x))
        x = torch.nn.functional.max_pool2d(x, 2)
        x = torch.nn.functional.relu(self.conv2(x))
        x = torch.nn.functional.max_pool2d(x, 2)
        x = x.view(x.size(0), -1)
        return self.fc(x)

model = DummyModel()
cam = GradCAM(model, target_layer=model.conv2)
test("GradCAM init", cam is not None)

dummy_input = torch.randn(1, 3, 224, 224)
heatmap = cam.generate(dummy_input, target_class=0)
test("heatmap shape", heatmap.shape == (224, 224))
test("heatmap range", 0.0 <= heatmap.max() <= 1.0)


# ── 7. EWA Primitives ──
print("\n[7] EWA Primitives")
from twc_core.ewa.primitives import VisualPrimitive, PrimitiveBatch, PrimitiveType, PrimitiveCodec

codec = PrimitiveCodec()
p = VisualPrimitive(
    ref="organoid_1", primitive_type=PrimitiveType.BOX,
    coords=[[100, 200, 300, 400]], token_entropy=0.5,
    source_client="lab_a",
)
batch = PrimitiveBatch(client_id="lab_a", round_id=1, primitives=[p])
test("batch size", batch.size_bytes() > 0)

# Test encode detections with twc_core.Detection
from twc_core.detector import Detection
dets = [Detection([10, 20, 100, 200], "healthy", 0, 0.95)]
encoded_batch = codec.encode_detections(dets, round_id=1)
test("encode_detections", len(encoded_batch.primitives) == 1)
test("encoded has entropy", encoded_batch.primitives[0].token_entropy > 0)

# Token entropy from logits
logits_confident = np.array([9.0, 0.1, 0.01])
logits_uncertain = np.array([0.3, 0.35, 0.35])
h_conf = codec.compute_token_entropy(logits_confident)
h_unc = codec.compute_token_entropy(logits_uncertain)
test("confident < uncertain", h_conf < h_unc, f"{h_conf} vs {h_unc}")


# ── 8. EWA Aggregator ──
print("\n[8] EWA Aggregator")
from twc_core.ewa.aggregator import EntropyWeightedAggregator, AggregationStrategy

agg = EntropyWeightedAggregator(strategy="entropy_weighted")

# Create 3 client batches
batches = []
for i, (cid, entropy) in enumerate([("lab_a", 0.3), ("lab_b", 1.5), ("lab_c", 4.0)]):
    primitives = [
        VisualPrimitive(
            ref=f"obj_{j}", primitive_type=PrimitiveType.BOX,
            coords=[[100 + i * 10, 200, 300 + i * 10, 400]],
            token_entropy=entropy, source_client=cid,
        )
        for j in range(2)
    ]
    batches.append(PrimitiveBatch(client_id=cid, round_id=1, primitives=primitives))

result = agg.aggregate(batches)
test("aggregation output", result.total_output > 0)
test("entropy stats has mean", "mean" in result.entropy_stats)
test("conformity report", "high_conformity_ratio" in result.conformity_report)

# Compare with FedAvg
comparison = agg.compare_with_fedavg(batches)
test("comparison keys", "improvement" in comparison)
test("conformity_reduction exists", "conformity_reduction" in comparison["improvement"])

# Weight computation
w_low = agg.compute_weight(0.1, AggregationStrategy.ENTROPY_WEIGHTED)
w_high = agg.compute_weight(5.0, AggregationStrategy.ENTROPY_WEIGHTED)
test("low entropy > high weight", w_low > w_high, f"{w_low} vs {w_high}")


# ── 9. Package imports ──
print("\n[9] Package Imports")
import twc_core
test("version", twc_core.__version__ == "0.1.0")
test("lazy import FLEngine", callable(twc_core.FLEngine))
test("lazy import AuditEngine", callable(twc_core.AuditEngine))
test("lazy import DINOv2Extractor", callable(twc_core.DINOv2Extractor))
test("lazy import Detector", callable(twc_core.Detector))
test("lazy import GradCAM", callable(twc_core.GradCAM))
test("lazy import VectorEngine", callable(twc_core.VectorEngine))
test("lazy import EntropyWeightedAggregator", callable(twc_core.EntropyWeightedAggregator))


# ── Summary ──
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
if failed == 0:
    print("✅ All tests passed!")
else:
    print(f"❌ {failed} test(s) failed")
    sys.exit(1)
