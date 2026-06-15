"""
混合检索器 — PageIndex + HNSW 双通道检索 + RRF 融合 + PageRank 重排序

核心算法：
  1. RRF (Reciprocal Rank Fusion):
     score(d) = Σ_r 1 / (k + rank_r(d))

  2. PageRank 重排序:
     final_score = alpha * rrf_score + (1 - alpha) * pagerank_score
"""

from __future__ import annotations
import logging
from typing import Optional

from .hnsw_retriever import HnswRetriever
from .pageindex_retriever import PageIndexRetriever
from ..router import route_query, QueryType, RoutingResult

logger = logging.getLogger(__name__)

# RRF 默认参数
RRF_K = 60  # 原论文默认值


class HybridRetriever:
    """
    混合检索器。

    查询路由 → 双通道检索 → RRF 融合 → PageRank 重排序
    """

    def __init__(
        self,
        hnsw: Optional[HnswRetriever] = None,
        pageindex: Optional[PageIndexRetriever] = None,
        pagerank_scores: Optional[dict[str, float]] = None,
        rrf_k: int = RRF_K,
        pagerank_alpha: float = 0.7,  # RRF 权重，1-alpha 给 PageRank
    ):
        self.hnsw = hnsw
        self.pageindex = pageindex
        self._pagerank_scores = pagerank_scores or {}
        self.rrf_k = rrf_k
        self.pagerank_alpha = pagerank_alpha

    @property
    def has_pagerank(self) -> bool:
        return len(self._pagerank_scores) > 0

    def set_pagerank_scores(self, scores: dict[str, float]) -> None:
        """设置 PageRank 分数（由外部 KG + PageRank 模块计算后注入）"""
        self._pagerank_scores = scores

    def search(
        self,
        query: str,
        query_vector: Optional[list[float]] = None,
        k: int = 10,
        doc_id: Optional[str] = None,
    ) -> dict:
        """
        混合检索主入口。

        Args:
            query: 查询文本
            query_vector: 查询向量（语义检索需要）
            k: 返回结果数量
            doc_id: 指定文档 ID（PageIndex 用）

        Returns:
            {
                "routing": {...},
                "results": [{id, title, score, content, metadata, rrf_score, pagerank_score?, final_score?}, ...],
                "pageindex_results": [...],
                "hnsw_results": [...],
            }
        """
        # 1. 路由
        has_pi = self.pageindex is not None and self.pageindex.doc_count > 0
        has_hnsw = self.hnsw is not None and self.hnsw.count > 0

        routing = route_query(query, has_pageindex=has_pi, has_hnsw=has_hnsw)
        logger.info(f"Routing: {routing.query_type.value} (confidence={routing.confidence:.2f}, reason={routing.reason})")

        # 2. 各通道检索
        pi_results = []
        hnsw_results = []

        if routing.query_type in (QueryType.STRUCTURAL, QueryType.HYBRID) and has_pi:
            try:
                pi_results = self.pageindex.search(query, doc_id=doc_id, top_k=k)
                logger.info(f"PageIndex returned {len(pi_results)} results")
            except Exception as e:
                logger.error(f"PageIndex search failed: {e}")

        if routing.query_type in (QueryType.SEMANTIC, QueryType.HYBRID) and has_hnsw and query_vector:
            try:
                hnsw_raw = self.hnsw.search(query_vector, k=k)
                hnsw_results = [
                    {
                        "id": id,
                        "title": meta.get("title", id),
                        "score": 1.0 - dist,  # 距离转相似度
                        "content": meta.get("content", ""),
                        "metadata": {**meta, "source": "hnsw"},
                    }
                    for id, dist, meta in hnsw_raw
                ]
                logger.info(f"HNSW returned {len(hnsw_results)} results")
            except Exception as e:
                logger.error(f"HNSW search failed: {e}")

        # 3. RRF 融合
        fused = self._rrf_fuse(pi_results, hnsw_results)

        # 4. PageRank 重排序
        if self.has_pagerank:
            fused = self._pagerank_rerank(fused)

        return {
            "routing": {
                "query_type": routing.query_type.value,
                "confidence": routing.confidence,
                "reason": routing.reason,
            },
            "results": fused[:k],
            "pageindex_results": pi_results,
            "hnsw_results": hnsw_results,
        }

    def _rrf_fuse(
        self,
        pi_results: list[dict],
        hnsw_results: list[dict],
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion 融合两个检索器的结果。

        RRF score(d) = Σ_r 1/(k + rank_r(d))
        """
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

        # PageIndex 结果
        for rank, result in enumerate(pi_results, start=1):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
            if doc_id not in result_map:
                result_map[doc_id] = result.copy()
            else:
                result_map[doc_id]["metadata"]["sources"] = result_map[doc_id]["metadata"].get("sources", [])
                if "pageindex" not in result_map[doc_id]["metadata"].get("sources", []):
                    result_map[doc_id]["metadata"]["sources"].append("pageindex")

        # HNSW 结果
        for rank, result in enumerate(hnsw_results, start=1):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
            if doc_id not in result_map:
                result_map[doc_id] = result.copy()
            else:
                result_map[doc_id]["metadata"]["sources"] = result_map[doc_id]["metadata"].get("sources", ["pageindex"])
                if "hnsw" not in result_map[doc_id]["metadata"]["sources"]:
                    result_map[doc_id]["metadata"]["sources"].append("hnsw")

        # 按 RRF 分数排序
        fused = []
        for doc_id, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            entry = result_map[doc_id]
            entry["rrf_score"] = score
            fused.append(entry)

        return fused

    def _pagerank_rerank(self, results: list[dict]) -> list[dict]:
        """
        用 PageRank 分数对 RRF 融合结果进行重排序。

        final_score = alpha * rrf_score_normalized + (1 - alpha) * pagerank_score_normalized
        """
        if not results:
            return results

        # 归一化 RRF 分数到 [0, 1]
        rrf_max = max(r.get("rrf_score", 0) for r in results) or 1.0

        # 获取 PageRank 分数并归一化
        pr_scores = []
        for r in results:
            node_id = r["id"]
            pr = self._pagerank_scores.get(node_id, 0.0)
            # 尝试 KG 节点格式匹配
            if pr == 0.0:
                for key, val in self._pagerank_scores.items():
                    if key.endswith(f"::{node_id}") or node_id.endswith(f"::{key}"):
                        pr = val
                        break
            pr_scores.append(pr)

        pr_max = max(pr_scores) if pr_scores else 1.0
        if pr_max == 0:
            pr_max = 1.0

        # 计算最终分数
        for i, r in enumerate(results):
            rrf_norm = r.get("rrf_score", 0) / rrf_max
            pr_norm = pr_scores[i] / pr_max
            r["pagerank_score"] = pr_scores[i]
            r["final_score"] = self.pagerank_alpha * rrf_norm + (1 - self.pagerank_alpha) * pr_norm

        # 按最终分数重排序
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        return results
