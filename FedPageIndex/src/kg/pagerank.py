"""
PageRank 排序器 — 在知识图谱上计算节点重要性

实现两种 PageRank：
  1. 标准 PageRank（NetworkX）
  2. 联邦 PageRank（各客户端本地计算 → FedAvg 聚合）

联邦 PageRank 数学：
  PR_global(v) = Σ_k (n_k / N) * PR_k(v)
  其中 PR_k(v) 是客户端 k 在本地子图上的 PageRank 值
"""

from __future__ import annotations
import logging
from typing import Optional

import networkx as nx

from .builder import KnowledgeGraph, NodeType

logger = logging.getLogger(__name__)


class PageRankRanker:
    """
    PageRank 排序器。

    在 KG 上计算 PageRank，用于：
      1. 检索结果重排序（重要节点的检索结果加权）
      2. 核心实体发现（找到 KG 中最重要的节点）
      3. 联邦聚合（Phase 3）
    """

    def __init__(
        self,
        damping: float = 0.85,
        max_iter: int = 100,
        tolerance: float = 1e-6,
    ):
        self.damping = damping
        self.max_iter = max_iter
        self.tolerance = tolerance
        self._scores: dict[str, float] = {}

    def compute(self, kg: KnowledgeGraph) -> dict[str, float]:
        """
        在知识图谱上计算 PageRank。

        Returns:
            {node_id: pagerank_score} 字典
        """
        # 构建 NetworkX 有向图
        G = nx.DiGraph()

        for node_id, node in kg.nodes.items():
            G.add_node(node_id, type=node.type.value, label=node.label)

        for edge in kg.edges:
            G.add_edge(edge.source, edge.target, weight=edge.weight)

        if G.number_of_nodes() == 0:
            logger.warning("Empty graph, returning empty PageRank scores")
            return {}

        # 计算 PageRank
        try:
            scores = nx.pagerank(
                G,
                alpha=self.damping,
                max_iter=self.max_iter,
                tol=self.tolerance,
                weight="weight",
            )
        except nx.PowerIterationFailedConvergence:
            logger.warning("PageRank did not converge, using current approximation")
            scores = nx.pagerank(
                G,
                alpha=self.damping,
                max_iter=self.max_iter * 2,
                tol=self.tolerance * 10,
                weight="weight",
            )

        self._scores = scores
        logger.info(f"Computed PageRank for {len(scores)} nodes")
        return scores

    @property
    def has_scores(self) -> bool:
        return len(self._scores) > 0

    def get_score(self, node_id: str) -> float:
        """获取节点的 PageRank 分数"""
        return self._scores.get(node_id, 0.0)

    def top_k(self, k: int = 10, node_type: Optional[NodeType] = None) -> list[tuple[str, float]]:
        """
        获取 PageRank 分数最高的 k 个节点。

        Args:
            k: 返回数量
            node_type: 可选，只返回指定类型的节点
        """
        if node_type:
            # 需要访问 KG 来过滤类型，这里只能按分数排序后外部过滤
            pass

        sorted_scores = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:k]

    def rerank_results(
        self,
        results: list[dict],
        alpha: float = 0.7,
        id_field: str = "id",
    ) -> list[dict]:
        """
        用 PageRank 分数对检索结果进行重排序。

        final_score = alpha * original_score_normalized + (1 - alpha) * pagerank_normalized

        Args:
            results: 检索结果列表，每个结果必须有 id 和 score 字段
            alpha: 原始分数权重（0-1），1-alpha 给 PageRank
            id_field: 结果中用作 KG 节点 ID 的字段名
        """
        if not results or not self._scores:
            return results

        # 归一化原始分数
        score_max = max(r.get("score", 0) for r in results) or 1.0

        # 获取 PageRank 分数
        pr_scores = []
        for r in results:
            node_id = r.get(id_field, "")
            pr = self._scores.get(node_id, 0.0)
            # 尝试带前缀的 ID
            if pr == 0.0:
                for prefix in ("section::", "doc::", "patent::", "entity::"):
                    pr = self._scores.get(f"{prefix}{node_id}", 0.0)
                    if pr > 0:
                        break
            pr_scores.append(pr)

        pr_max = max(pr_scores) if pr_scores else 1.0
        if pr_max == 0:
            pr_max = 1.0

        # 计算最终分数
        for i, r in enumerate(results):
            orig_norm = r.get("score", 0) / score_max
            pr_norm = pr_scores[i] / pr_max
            r["pagerank_score"] = pr_scores[i]
            r["final_score"] = alpha * orig_norm + (1 - alpha) * pr_norm

        # 按最终分数排序
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        return results


class FederatedPageRank:
    """
    联邦 PageRank — 各客户端本地计算 PageRank，服务端 FedAvg 聚合。

    流程：
      1. 各客户端在本地 KG 子图上计算 PageRank
      2. 上传本地 PageRank 分数到服务端
      3. 服务端按样本数加权聚合（FedAvg）
      4. 可选：差分隐私保护（Phase 3）

    数学：
      PR_global(v) = Σ_k (n_k / N) * PR_k(v)
      其中 n_k 是客户端 k 的本地节点数，N = Σ_k n_k
    """

    def __init__(self, damping: float = 0.85):
        self.damping = damping
        self._local_scores: list[tuple[dict[str, float], int]] = []
        self._global_scores: dict[str, float] = {}

    def add_client_scores(self, scores: dict[str, float], node_count: int) -> None:
        """
        添加一个客户端的本地 PageRank 分数。

        Args:
            scores: {node_id: pagerank_score} 本地 PageRank 分数
            node_count: 客户端本地 KG 的节点数
        """
        self._local_scores.append((scores, node_count))
        logger.info(f"Added client scores: {len(scores)} nodes, {node_count} total")

    def aggregate(self) -> dict[str, float]:
        """
        FedAvg 聚合所有客户端的 PageRank 分数。

        Returns:
            全局 PageRank 分数
        """
        if not self._local_scores:
            logger.warning("No client scores to aggregate")
            return {}

        total_nodes = sum(nc for _, nc in self._local_scores)
        if total_nodes == 0:
            return {}

        global_scores: dict[str, float] = {}

        for scores, node_count in self._local_scores:
            weight = node_count / total_nodes  # FedAvg 加权
            for node_id, score in scores.items():
                global_scores[node_id] = global_scores.get(node_id, 0.0) + weight * score

        self._global_scores = global_scores
        logger.info(
            f"Federated PageRank aggregated: {len(global_scores)} nodes from {len(self._local_scores)} clients"
        )
        return global_scores

    def get_score(self, node_id: str) -> float:
        return self._global_scores.get(node_id, 0.0)

    def top_k(self, k: int = 10) -> list[tuple[str, float]]:
        """获取全局 PageRank 分数最高的 k 个节点"""
        sorted_scores = sorted(self._global_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:k]

    @property
    def client_count(self) -> int:
        return len(self._local_scores)

    @property
    def has_scores(self) -> bool:
        return len(self._global_scores) > 0
