"""
twc-core — Unified ML Infrastructure for Federated Learning Projects
====================================================================

Layer 1 shared modules extracted from:
  - TWC-FL-PROD (fl_engine, audit_chain, data_vault, entropy_weighted_aggregator, primitive_codec)
  - organoid-fl-upgrade (detector, feature_extractor, gradcam, vector_engine, audit_engine)
  - defect-fl-upgrade (detector, gradcam)
  - embodied-fl-upgrade (detector, feature_extractor, gradcam)
  - reading-fl-upgrade (hnsw_index, audit/chain)

Architecture:
  Layer 0: Rust infrastructure (gRPC, HNSW native, audit chain native)
  Layer 1: twc-core (this package) — shared Python ML modules
  Layer 2: Domain frameworks (organoid-fl, defect-fl, embodied-fl, etc.)
  Layer 3: Applications (Streamlit apps, papers, products)

Usage:
  from twc_core import FLEngine, AuditEngine, DINOv2Extractor, GradCAM
  from twc_core import EntropyWeightedAggregator, PrimitiveCodec
"""

__version__ = "0.1.0"
__all__ = [
    # Federated Learning
    "FLConfig", "FLClient", "ClientUpdate", "AggregationResult",
    "FLEngine",
    # Audit Chain
    "AuditBlock", "AuditEngine",
    # Feature Extraction
    "DINOv2Extractor", "ResNet18Extractor", "get_extractor",
    # Object Detection
    "Detection", "Detector",
    # Explainability
    "GradCAM",
    # Vector Search
    "VectorEngine",
    # Entropy-Weighted Aggregation
    "VisualPrimitive", "PrimitiveBatch", "PrimitiveType", "PrimitiveCodec",
    "EntropyWeightedAggregator", "AggregatedPrimitive", "ClassPrototype",
    "ConformityDetector", "ConformityAlert", "RoundSnapshot",
]

# Lazy imports to avoid hard dependencies
def __getattr__(name):
    _lazy = {
        # FL
        "FLConfig": ("twc_core.fl_engine", "FLConfig"),
        "FLClient": ("twc_core.fl_engine", "FLClient"),
        "ClientUpdate": ("twc_core.fl_engine", "ClientUpdate"),
        "AggregationResult": ("twc_core.fl_engine", "AggregationResult"),
        "FLEngine": ("twc_core.fl_engine", "FLEngine"),
        # Audit
        "AuditBlock": ("twc_core.audit", "AuditBlock"),
        "AuditEngine": ("twc_core.audit", "AuditEngine"),
        # Features
        "DINOv2Extractor": ("twc_core.features", "DINOv2Extractor"),
        "ResNet18Extractor": ("twc_core.features", "ResNet18Extractor"),
        "get_extractor": ("twc_core.features", "get_extractor"),
        # Detection
        "Detection": ("twc_core.detector", "Detection"),
        "Detector": ("twc_core.detector", "Detector"),
        # Explainability
        "GradCAM": ("twc_core.gradcam", "GradCAM"),
        # Vector
        "VectorEngine": ("twc_core.vector", "VectorEngine"),
        # EWA
        "VisualPrimitive": ("twc_core.ewa.primitives", "VisualPrimitive"),
        "PrimitiveBatch": ("twc_core.ewa.primitives", "PrimitiveBatch"),
        "PrimitiveType": ("twc_core.ewa.primitives", "PrimitiveType"),
        "PrimitiveCodec": ("twc_core.ewa.primitives", "PrimitiveCodec"),
        "EntropyWeightedAggregator": ("twc_core.ewa.aggregator", "EntropyWeightedAggregator"),
        "AggregatedPrimitive": ("twc_core.ewa.aggregator", "AggregatedPrimitive"),
        "ClassPrototype": ("twc_core.ewa.aggregator", "ClassPrototype"),
        "ConformityDetector": ("twc_core.ewa.conformity", "ConformityDetector"),
        "ConformityAlert": ("twc_core.ewa.conformity", "ConformityAlert"),
        "RoundSnapshot": ("twc_core.ewa.conformity", "RoundSnapshot"),
    }
    if name in _lazy:
        import importlib
        mod_path, attr = _lazy[name]
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
