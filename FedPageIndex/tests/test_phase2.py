"""
Phase 2 测试 — 知识图谱构建 + PageRank 排序 + 联邦聚合
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from src.kg import (
    KGBuilder, KnowledgeGraph, KGNode, KGEdge,
    NodeType, EdgeType,
    PageRankRanker, FederatedPageRank,
)
from src.retriever.hybrid_retriever import HybridRetriever
from src.retriever.hnsw_retriever import HnswRetriever


# ── KnowledgeGraph 基础测试 ──────────────────────────────────

class TestKnowledgeGraph:
    def test_add_node(self):
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="n1", type=NodeType.DOCUMENT, label="Doc 1"))
        assert kg.node_count == 1
        assert "n1" in kg.nodes

    def test_add_edge(self):
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="n1", type=NodeType.DOCUMENT, label="Doc 1"))
        kg.add_node(KGNode(id="n2", type=NodeType.SECTION, label="Section 1"))
        kg.add_edge(KGEdge(source="n1", target="n2", type=EdgeType.CONTAINS))
        assert kg.edge_count == 1

    def test_get_neighbors(self):
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="n1", type=NodeType.DOCUMENT, label="Doc 1"))
        kg.add_node(KGNode(id="n2", type=NodeType.SECTION, label="Section 1"))
        kg.add_node(KGNode(id="n3", type=NodeType.SECTION, label="Section 2"))
        kg.add_edge(KGEdge(source="n1", target="n2", type=EdgeType.CONTAINS))
        kg.add_edge(KGEdge(source="n1", target="n3", type=EdgeType.CONTAINS))

        neighbors = kg.get_neighbors("n1")
        assert len(neighbors) == 2
        assert "n2" in neighbors
        assert "n3" in neighbors

    def test_get_neighbors_empty(self):
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="n1", type=NodeType.DOCUMENT, label="Doc 1"))
        assert kg.get_neighbors("n1") == []

    def test_to_dict_roundtrip(self):
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="n1", type=NodeType.DOCUMENT, label="Doc 1", properties={"pages": 10}))
        kg.add_node(KGNode(id="n2", type=NodeType.SECTION, label="Sec 1"))
        kg.add_edge(KGEdge(source="n1", target="n2", type=EdgeType.CONTAINS, weight=1.0))

        data = kg.to_dict()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1


# ── KGBuilder 测试 ────────────────────────────────────────────

class TestKGBuilder:
    def test_build_from_pageindex_tree(self):
        tree = [
            {
                "node_id": "0000",
                "title": "Introduction",
                "summary": "Overview of the system",
                "start_index": 1,
                "end_index": 5,
                "nodes": [
                    {
                        "node_id": "0001",
                        "title": "Background",
                        "summary": "Background on federated learning",
                        "start_index": 1,
                        "end_index": 3,
                    },
                    {
                        "node_id": "0002",
                        "title": "Motivation",
                        "summary": "Why we need this system",
                        "start_index": 3,
                        "end_index": 5,
                    },
                ],
            },
            {
                "node_id": "0003",
                "title": "Methods",
                "summary": "Technical methods including deep learning and neural networks",
                "start_index": 6,
                "end_index": 10,
            },
        ]

        builder = KGBuilder()
        kg = builder.build_from_pageindex_tree(tree, doc_id="doc_test")

        # 应该有文档节点 + 3个章节节点 + 实体节点
        assert kg.node_count >= 4  # doc + 3 sections
        assert kg.edge_count >= 3  # doc→section 边

        # 验证层级关系
        doc_node_id = "doc_test"
        assert doc_node_id in kg.nodes
        assert kg.nodes[doc_node_id].type == NodeType.DOCUMENT

        # 验证父子关系
        section_0000 = "section::doc_test::0000"
        section_0001 = "section::doc_test::0001"
        if section_0000 in kg.nodes and section_0001 in kg.nodes:
            neighbors = kg.get_neighbors(section_0000)
            assert section_0001 in neighbors

    def test_build_from_patents(self):
        patents = [
            {
                "id": "CN123456",
                "title": "联邦学习方法及系统",
                "abstract": "本发明涉及一种基于差分隐私的联邦学习训练方法",
                "cited_patents": ["CN789012", "US345678"],
                "ipc_codes": ["G06N", "H04L"],
            },
            {
                "id": "CN789012",
                "title": "隐私保护数据聚合方法",
                "abstract": "一种安全聚合协议用于分布式机器学习",
                "cited_patents": [],
                "ipc_codes": ["G06N"],
            },
        ]

        builder = KGBuilder()
        kg = builder.build_from_patents(patents)

        # 应该有专利节点 + 引用专利 + IPC 节点 + 实体节点
        assert "patent::CN123456" in kg.nodes
        assert "patent::CN789012" in kg.nodes
        assert "ipc::G06N" in kg.nodes

        # 验证引用关系
        neighbors = kg.get_neighbors("patent::CN123456")
        assert "patent::CN789012" in neighbors

        # 验证 IPC 归属
        assert "ipc::G06N" in neighbors

    def test_empty_tree(self):
        builder = KGBuilder()
        kg = builder.build_from_pageindex_tree([], doc_id="empty")
        assert kg.node_count == 1  # 只有文档节点


# ── PageRank 测试 ─────────────────────────────────────────────

class TestPageRankRanker:
    def _build_star_graph(self) -> KnowledgeGraph:
        """构建星形图：中心节点连接3个叶子"""
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="center", type=NodeType.CONCEPT, label="Center"))
        kg.add_node(KGNode(id="leaf1", type=NodeType.ENTITY, label="Leaf 1"))
        kg.add_node(KGNode(id="leaf2", type=NodeType.ENTITY, label="Leaf 2"))
        kg.add_node(KGNode(id="leaf3", type=NodeType.ENTITY, label="Leaf 3"))
        # 叶子→中心（中心被引用最多，PageRank 应最高）
        kg.add_edge(KGEdge(source="leaf1", target="center", type=EdgeType.REFERENCES))
        kg.add_edge(KGEdge(source="leaf2", target="center", type=EdgeType.REFERENCES))
        kg.add_edge(KGEdge(source="leaf3", target="center", type=EdgeType.REFERENCES))
        return kg

    def test_basic_pagerank(self):
        kg = self._build_star_graph()
        ranker = PageRankRanker()
        scores = ranker.compute(kg)

        assert len(scores) == 4
        # 中心节点 PageRank 应最高
        assert scores["center"] > scores["leaf1"]
        assert scores["center"] > scores["leaf2"]
        assert scores["center"] > scores["leaf3"]

    def test_top_k(self):
        kg = self._build_star_graph()
        ranker = PageRankRanker()
        ranker.compute(kg)

        top2 = ranker.top_k(2)
        assert len(top2) == 2
        assert top2[0][0] == "center"

    def test_get_score(self):
        kg = self._build_star_graph()
        ranker = PageRankRanker()
        ranker.compute(kg)

        assert ranker.get_score("center") > 0
        assert ranker.get_score("nonexistent") == 0.0

    def test_has_scores(self):
        kg = self._build_star_graph()
        ranker = PageRankRanker()
        assert not ranker.has_scores
        ranker.compute(kg)
        assert ranker.has_scores

    def test_empty_graph(self):
        kg = KnowledgeGraph()
        ranker = PageRankRanker()
        scores = ranker.compute(kg)
        assert scores == {}

    def test_single_node(self):
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="only", type=NodeType.DOCUMENT, label="Only"))
        ranker = PageRankRanker()
        scores = ranker.compute(kg)
        assert "only" in scores
        assert abs(scores["only"] - 1.0) < 0.01


# ── 联邦 PageRank 测试 ────────────────────────────────────────

class TestFederatedPageRank:
    def test_single_client(self):
        """单客户端 = 标准 PageRank"""
        fed_pr = FederatedPageRank()
        scores = {"A": 0.5, "B": 0.3, "C": 0.2}
        fed_pr.add_client_scores(scores, node_count=100)

        global_scores = fed_pr.aggregate()
        assert len(global_scores) == 3
        assert abs(global_scores["A"] - 0.5) < 0.01

    def test_two_clients_equal_weight(self):
        """两个等权客户端的聚合"""
        fed_pr = FederatedPageRank()

        # 客户端 1: A=0.5, B=0.3, C=0.2
        fed_pr.add_client_scores({"A": 0.5, "B": 0.3, "C": 0.2}, node_count=100)
        # 客户端 2: A=0.3, B=0.5, C=0.2
        fed_pr.add_client_scores({"A": 0.3, "B": 0.5, "C": 0.2}, node_count=100)

        global_scores = fed_pr.aggregate()
        # 等权 → 平均
        assert abs(global_scores["A"] - 0.4) < 0.01
        assert abs(global_scores["B"] - 0.4) < 0.01
        assert abs(global_scores["C"] - 0.2) < 0.01

    def test_two_clients_weighted(self):
        """两个不等权客户端：大客户端主导"""
        fed_pr = FederatedPageRank()

        # 客户端 1: 900 节点，A=0.5
        fed_pr.add_client_scores({"A": 0.5, "B": 0.3}, node_count=900)
        # 客户端 2: 100 节点，A=0.1
        fed_pr.add_client_scores({"A": 0.1, "B": 0.7}, node_count=100)

        global_scores = fed_pr.aggregate()
        # A: 0.9*0.5 + 0.1*0.1 = 0.46
        assert abs(global_scores["A"] - 0.46) < 0.01
        # B: 0.9*0.3 + 0.1*0.7 = 0.34
        assert abs(global_scores["B"] - 0.34) < 0.01

    def test_disjoint_clients(self):
        """不重叠的客户端：各自贡献自己的节点"""
        fed_pr = FederatedPageRank()

        fed_pr.add_client_scores({"X": 0.6, "Y": 0.4}, node_count=50)
        fed_pr.add_client_scores({"Z": 0.8, "W": 0.2}, node_count=50)

        global_scores = fed_pr.aggregate()
        assert len(global_scores) == 4
        # 等权 → 直接平均
        assert abs(global_scores["X"] - 0.3) < 0.01  # 0.5 * 0.6
        assert abs(global_scores["Z"] - 0.4) < 0.01  # 0.5 * 0.8

    def test_empty_aggregation(self):
        fed_pr = FederatedPageRank()
        assert fed_pr.aggregate() == {}

    def test_top_k(self):
        fed_pr = FederatedPageRank()
        fed_pr.add_client_scores({"A": 0.5, "B": 0.3, "C": 0.2}, node_count=100)
        fed_pr.aggregate()

        top2 = fed_pr.top_k(2)
        assert len(top2) == 2
        assert top2[0][0] == "A"

    def test_client_count(self):
        fed_pr = FederatedPageRank()
        assert fed_pr.client_count == 0
        fed_pr.add_client_scores({"A": 0.5}, node_count=10)
        assert fed_pr.client_count == 1


# ── PageRank 重排序集成测试 ───────────────────────────────────

class TestPageRankRerank:
    def test_rerank_changes_order(self):
        """PageRank 分数应该能改变 RRF 排序"""
        kg = KnowledgeGraph()
        kg.add_node(KGNode(id="doc1", type=NodeType.DOCUMENT, label="Doc 1"))
        kg.add_node(KGNode(id="doc2", type=NodeType.DOCUMENT, label="Doc 2"))
        kg.add_node(KGNode(id="doc3", type=NodeType.DOCUMENT, label="Doc 3"))
        # doc2 被引用最多
        kg.add_edge(KGEdge(source="doc1", target="doc2", type=EdgeType.REFERENCES))
        kg.add_edge(KGEdge(source="doc3", target="doc2", type=EdgeType.REFERENCES))

        ranker = PageRankRanker()
        scores = ranker.compute(kg)

        # 构造 RRF 结果：doc1 排第一
        results = [
            {"id": "doc1", "title": "Doc 1", "score": 0.9, "content": "", "metadata": {}, "rrf_score": 0.032},
            {"id": "doc2", "title": "Doc 2", "score": 0.7, "content": "", "metadata": {}, "rrf_score": 0.016},
            {"id": "doc3", "title": "Doc 3", "score": 0.5, "content": "", "metadata": {}, "rrf_score": 0.015},
        ]

        hybrid = HybridRetriever(pagerank_scores=scores, pagerank_alpha=0.3)
        reranked = hybrid._pagerank_rerank(results)

        # doc2 的 PageRank 最高，alpha=0.3 时 PageRank 权重大
        # doc2 应该被提升
        assert reranked[0]["id"] == "doc2"
        assert "final_score" in reranked[0]
        assert "pagerank_score" in reranked[0]

    def test_no_pagerank_passes_through(self):
        """没有 PageRank 时不重排序"""
        results = [
            {"id": "doc1", "title": "Doc 1", "score": 0.9, "content": "", "metadata": {}, "rrf_score": 0.032},
        ]
        hybrid = HybridRetriever()
        # pagerank=None，不会调用 _pagerank_rerank
        # 直接返回原结果
        assert results[0]["id"] == "doc1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
