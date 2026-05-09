"""EWA-Fed: Entropy-Weighted Aggregation for Federated Learning.

A monitoring framework that detects conformity effects in FL training
by analyzing visual primitives with entropy-weighted class prototypes.
"""

from .primitives import VisualPrimitive, PrimitiveBatch, PrimitiveType, PrimitiveCodec
from .aggregator import (
    AggregationStrategy, AggregatedPrimitive, AggregationResult,
    ClassPrototype, EntropyWeightedAggregator,
)
from .conformity import ConformityDetector, ConformityAlert, RoundSnapshot

__version__ = "0.1.0"
__all__ = [
    "VisualPrimitive", "PrimitiveBatch", "PrimitiveType", "PrimitiveCodec",
    "AggregationStrategy", "AggregatedPrimitive", "AggregationResult",
    "ClassPrototype", "EntropyWeightedAggregator",
    "ConformityDetector", "ConformityAlert", "RoundSnapshot",
]
