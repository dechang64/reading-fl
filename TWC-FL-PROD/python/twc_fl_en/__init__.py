"""
TWC-FL Platform - Three-Way Catalyst Federated Learning Collaboration Platform

Python core package. Modules:
    - data_vault: Formula data management (import/anonymization/quality report/similarity search)
    - knowledge_hub: TWC domain knowledge base (FAQ query/literature recommendation)
    - bayesian_optimizer: Bayesian formula optimization (surrogate model/candidate recommendation)
    - fl_engine: Federated learning engine (node management/FedAvg aggregation/model distribution)
    - audit_chain: Blockchain audit chain (data attestation/chain verification)
    - primitive_codec: Visual primitive encoder/decoder (box/point/path + token entropy)
    - entropy_weighted_aggregator: Entropy-weighted primitive aggregation (conformity suppression)
"""

from .data_vault import DataVault, FormulaRecord, DataQualityReport
from .knowledge_hub import KnowledgeHub, FAQEntry, LiteratureRef
from .bayesian_optimizer import BayesianOptimizer, CandidateFormula, OptimizationResult
from .fl_engine import FLEngine, FLClient, FLConfig, AggregationResult
from .audit_chain import AuditChain, AuditEntry
from .primitive_codec import (
    PrimitiveCodec, VisualPrimitive, PrimitiveBatch, PrimitiveType,
)
from .entropy_weighted_aggregator import (
    EntropyWeightedAggregator, AggregatedPrimitive, AggregationResult as PrimitiveAggResult,
    AggregationStrategy,
)

__version__ = "1.2.0"
__all__ = [
    "DataVault", "FormulaRecord", "DataQualityReport",
    "KnowledgeHub", "FAQEntry", "LiteratureRef",
    "BayesianOptimizer", "CandidateFormula", "OptimizationResult",
    "FLEngine", "FLClient", "FLConfig", "AggregationResult",
    "AuditChain", "AuditEntry",
    "PrimitiveCodec", "VisualPrimitive", "PrimitiveBatch", "PrimitiveType",
    "EntropyWeightedAggregator", "AggregatedPrimitive", "PrimitiveAggResult",
    "AggregationStrategy",
]
