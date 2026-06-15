"""
FedPageIndex — 联邦混合检索与知识图谱排序系统

四层架构：
  1. 混合检索层：PageIndex 树推理 + HNSW 向量检索
  2. 融合排序层：RRF (Reciprocal Rank Fusion) + 查询路由
  3. 知识图谱层：三元组存储 + PageRank 排序（Phase 2）
  4. 联邦学习层：FedAvg 聚合（Phase 3）
"""

__version__ = "0.1.0"
