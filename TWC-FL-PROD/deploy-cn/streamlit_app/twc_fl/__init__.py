"""
TWC-FL Platform — 三元催化配方联邦学习协作平台

Python core package. Modules:
    - data_vault: 配方数据管理（导入/脱敏/质量报告/相似度检索）
    - knowledge_hub: TWC领域知识库（问题查询/文献摘要/配方推荐）
    - bayesian_optimizer: 贝叶斯配方优化（Surrogate Model/候选推荐/实验回填）
    - fl_engine: 联邦学习引擎（节点管理/FedAvg聚合/模型分发）
    - audit_chain: 区块链审计链（数据存证/链验证）
"""

from .data_vault import DataVault, FormulaRecord, DataQualityReport
from .knowledge_hub import KnowledgeHub, FAQEntry, LiteratureRef
from .bayesian_optimizer import BayesianOptimizer, CandidateFormula, OptimizationResult
from .fl_engine import FLEngine, FLClient, FLConfig, AggregationResult
from .audit_chain import AuditChain, AuditEntry

__version__ = "1.0.0"
__all__ = [
    "DataVault", "FormulaRecord", "DataQualityReport",
    "KnowledgeHub", "FAQEntry", "LiteratureRef",
    "BayesianOptimizer", "CandidateFormula", "OptimizationResult",
    "FLEngine", "FLClient", "FLConfig", "AggregationResult",
    "AuditChain", "AuditEntry",
]
