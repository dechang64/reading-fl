"""
FedPageIndex 单元测试
"""

import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import numpy as np

from src.router import route_query, QueryType
from src.retriever.hnsw_retriever import HnswRetriever
from src.retriever.hybrid_retriever import HybridRetriever


# ── 查询路由测试 ──────────────────────────────────────────────

class TestQueryRouter:
    def test_structural_chinese_chapter(self):
        result = route_query("第三章讲了什么？", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.STRUCTURAL

    def test_structural_section(self):
        result = route_query("What does Section 5 say about risk?", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.STRUCTURAL

    def test_structural_definition(self):
        result = route_query("什么是差分隐私？", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.STRUCTURAL

    def test_semantic_similar(self):
        result = route_query("找跟联邦学习相似的论文", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.SEMANTIC

    def test_semantic_recommend(self):
        result = route_query("推荐几只高Sharpe比率的基金", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.SEMANTIC

    def test_hybrid_mixed_signals(self):
        result = route_query("比较第三章和第五章的方法", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.HYBRID

    def test_hybrid_no_signal(self):
        # 中等长度、无明确结构/语义信号 → 走混合
        result = route_query("请帮我查一下关于这个主题的详细信息", has_pageindex=True, has_hnsw=True)
        assert result.query_type == QueryType.HYBRID

    def test_no_pageindex_fallback(self):
        result = route_query("第三章讲了什么？", has_pageindex=False, has_hnsw=True)
        assert result.query_type == QueryType.SEMANTIC

    def test_no_hnsw_fallback(self):
        result = route_query("找相似的基金", has_pageindex=True, has_hnsw=False)
        assert result.query_type == QueryType.STRUCTURAL


# ── HNSW 检索测试 ─────────────────────────────────────────────

class TestHnswRetriever:
    def setup_method(self):
        self.retriever = HnswRetriever(dimension=8, max_elements=100)

    def test_insert_and_count(self):
        self.retriever.insert("v1", [0.1] * 8)
        assert self.retriever.count == 1

    def test_insert_batch(self):
        vectors = [
            ("v1", [0.1] * 8, None),
            ("v2", [0.2] * 8, {"label": "test"}),
            ("v3", [0.3] * 8, None),
        ]
        count = self.retriever.insert_batch(vectors)
        assert count == 3
        assert self.retriever.count == 3

    def test_search_basic(self):
        # 使用正交基向量，确保余弦距离有意义
        for i in range(10):
            vec = [0.0] * 8
            vec[i % 8] = 1.0
            self.retriever.insert(f"v{i}", vec)

        # 查询向量最接近 v5（第5维为1）
        query = [0.0] * 8
        query[5] = 1.0
        results = self.retriever.search(query, k=3)
        assert len(results) == 3
        # 最近邻应该是 v5
        assert results[0][0] == "v5"

    def test_search_with_metadata(self):
        vec_a = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        self.retriever.insert("f1", vec_a, metadata={"name": "Fund A"})
        self.retriever.insert("f2", vec_b, metadata={"name": "Fund B"})

        results = self.retriever.search(vec_a, k=2)
        assert results[0][2]["name"] == "Fund A"

    def test_duplicate_id_raises(self):
        self.retriever.insert("v1", [0.1] * 8)
        with pytest.raises(ValueError, match="already exists"):
            self.retriever.insert("v1", [0.2] * 8)

    def test_delete(self):
        self.retriever.insert("v1", [0.1] * 8)
        self.retriever.insert("v2", [0.2] * 8)
        self.retriever.delete("v1")
        assert self.retriever.count == 1

    def test_save_and_load(self, tmp_path):
        for i in range(5):
            self.retriever.insert(f"v{i}", [i * 0.1] * 8, metadata={"idx": i})

        save_path = tmp_path / "hnsw_test"
        self.retriever.save(save_path)

        loaded = HnswRetriever.load(save_path)
        assert loaded.count == 5

        results = loaded.search([0.3] * 8, k=2)
        assert len(results) == 2

    def test_dimension_mismatch(self):
        with pytest.raises(Exception):
            self.retriever.insert("v1", [0.1] * 4)  # 4 != 8


# ── RRF 融合测试 ──────────────────────────────────────────────

class TestRRFFusion:
    def setup_method(self):
        self.hybrid = HybridRetriever()

    def test_rrf_basic(self):
        pi_results = [
            {"id": "doc1", "title": "A", "score": 0.9, "content": "", "metadata": {}},
            {"id": "doc2", "title": "B", "score": 0.7, "content": "", "metadata": {}},
        ]
        hnsw_results = [
            {"id": "doc3", "title": "C", "score": 0.95, "content": "", "metadata": {}},
            {"id": "doc1", "title": "A", "score": 0.85, "content": "", "metadata": {}},
        ]

        fused = self.hybrid._rrf_fuse(pi_results, hnsw_results)
        assert len(fused) == 3  # doc1, doc2, doc3

        # doc1 在两个检索器中都出现，RRF 分数应该最高
        assert fused[0]["id"] == "doc1"
        assert "pageindex" in fused[0]["metadata"]["sources"]
        assert "hnsw" in fused[0]["metadata"]["sources"]

    def test_rrf_single_source(self):
        pi_results = [
            {"id": "doc1", "title": "A", "score": 0.9, "content": "", "metadata": {}},
        ]
        hnsw_results = []

        fused = self.hybrid._rrf_fuse(pi_results, hnsw_results)
        assert len(fused) == 1
        assert fused[0]["id"] == "doc1"

    def test_rrf_empty(self):
        fused = self.hybrid._rrf_fuse([], [])
        assert len(fused) == 0

    def test_rrf_scores_decreasing(self):
        pi_results = [
            {"id": f"doc{i}", "title": f"D{i}", "score": 0.9 - i * 0.1, "content": "", "metadata": {}}
            for i in range(5)
        ]
        hnsw_results = [
            {"id": f"doc{i}", "title": f"D{i}", "score": 0.8 - i * 0.1, "content": "", "metadata": {}}
            for i in range(5)
        ]

        fused = self.hybrid._rrf_fuse(pi_results, hnsw_results)
        # RRF 分数应该递减
        for i in range(len(fused) - 1):
            assert fused[i]["rrf_score"] >= fused[i + 1]["rrf_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
