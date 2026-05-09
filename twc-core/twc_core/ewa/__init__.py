"""twc_core.ewa — Entropy-Weighted Aggregation subpackage."""

from .primitives import VisualPrimitive, PrimitiveBatch, PrimitiveType, PrimitiveCodec
from .aggregator import (
    AggregationStrategy, AggregatedPrimitive, AggregationResult,
    ClassPrototype, EntropyWeightedAggregator,
)
from .conformity import ConformityDetector, ConformityAlert, RoundSnapshot

__all__ = [
    "VisualPrimitive", "PrimitiveBatch", "PrimitiveType", "PrimitiveCodec",
    "AggregationStrategy", "AggregatedPrimitive", "AggregationResult",
    "ClassPrototype", "EntropyWeightedAggregator",
    "ConformityDetector", "ConformityAlert", "RoundSnapshot",
]
