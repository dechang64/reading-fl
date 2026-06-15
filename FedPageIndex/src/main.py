"""
FedPageIndex 启动入口

用法：
  python -m src.main                          # 启动 API 服务
  python -m src.main --demo                   # 运行演示
  python -m src.main --test                   # 运行测试
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("fedpageindex")


def run_api(host: str = "0.0.0.0", port: int = 8900):
    """启动 FastAPI 服务"""
    import uvicorn
    from .retriever import HnswRetriever, PageIndexRetriever
    from .api import create_app

    # 初始化 HNSW（768 维，适配常见 embedding 模型）
    hnsw = HnswRetriever(dimension=768, max_elements=100000)

    # 初始化 PageIndex
    pageindex = PageIndexRetriever()

    app = create_app(hnsw=hnsw, pageindex=pageindex)

    logger.info(f"Starting FedPageIndex API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


def run_demo():
    """运行混合检索演示"""
    import numpy as np
    from .retriever import HnswRetriever
    from .router import route_query

    print("=" * 60)
    print("FedPageIndex 混合检索演示")
    print("=" * 60)

    # 1. 查询路由演示
    print("\n--- 查询路由演示 ---")
    test_queries = [
        "第三章讲了什么？",
        "找跟联邦学习相关的论文",
        "2023年年报中关于货币政策的摘要",
        "similar funds with high Sharpe ratio",
        "什么是差分隐私？",
    ]

    for q in test_queries:
        result = route_query(q, has_pageindex=True, has_hnsw=True)
        print(f"  Q: {q}")
        print(f"  → {result.query_type.value} (confidence={result.confidence:.2f})")
        print(f"    {result.reason}")
        print()

    # 2. HNSW 检索演示
    print("\n--- HNSW 向量检索演示 ---")
    hnsw = HnswRetriever(dimension=8, max_elements=1000)

    # 模拟基金特征向量
    funds = [
        ("fund_001", [0.1, 0.3, 0.5, 0.7, 0.2, 0.4, 0.6, 0.8], {"title": "华夏成长混合", "category": "混合型"}),
        ("fund_002", [0.2, 0.4, 0.6, 0.8, 0.1, 0.3, 0.5, 0.7], {"title": "易方达蓝筹精选", "category": "混合型"}),
        ("fund_003", [0.9, 0.1, 0.3, 0.5, 0.7, 0.2, 0.4, 0.6], {"title": "招商中证白酒", "category": "指数型"}),
        ("fund_004", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], {"title": "天弘余额宝", "category": "货币型"}),
        ("fund_005", [0.1, 0.3, 0.5, 0.7, 0.2, 0.4, 0.6, 0.9], {"title": "南方中证500", "category": "指数型"}),
    ]

    for fid, vec, meta in funds:
        hnsw.insert(fid, vec, metadata=meta)
    print(f"  已索引 {hnsw.count} 只基金")

    # 搜索
    query_vec = [0.15, 0.35, 0.55, 0.75, 0.2, 0.4, 0.6, 0.85]
    results = hnsw.search(query_vec, k=3)
    print(f"  查询向量: {query_vec}")
    print(f"  Top-3 相似基金:")
    for id, dist, meta in results:
        print(f"    {id}: {meta['title']} (distance={dist:.4f})")

    # 3. RRF 融合演示
    print("\n--- RRF 融合演示 ---")
    from .retriever import HybridRetriever

    hybrid = HybridRetriever(hnsw=hnsw)

    # 模拟 PageIndex 结果
    pi_results = [
        {"id": "fund_001", "title": "华夏成长混合", "score": 0.9, "content": "...", "metadata": {"source": "pageindex"}},
        {"id": "fund_003", "title": "招商中证白酒", "score": 0.7, "content": "...", "metadata": {"source": "pageindex"}},
    ]

    # 模拟 HNSW 结果
    hnsw_results = [
        {"id": "fund_002", "title": "易方达蓝筹精选", "score": 0.95, "content": "...", "metadata": {"source": "hnsw"}},
        {"id": "fund_001", "title": "华夏成长混合", "score": 0.85, "content": "...", "metadata": {"source": "hnsw"}},
        {"id": "fund_005", "title": "南方中证500", "score": 0.6, "content": "...", "metadata": {"source": "hnsw"}},
    ]

    fused = hybrid._rrf_fuse(pi_results, hnsw_results)
    print("  PageIndex 结果: fund_001(0.9), fund_003(0.7)")
    print("  HNSW 结果: fund_002(0.95), fund_001(0.85), fund_005(0.6)")
    print("  RRF 融合后:")
    for r in fused:
        sources = r["metadata"].get("sources", [r["metadata"].get("source", "?")])
        print(f"    {r['id']}: {r['title']} (rrf={r['rrf_score']:.6f}, sources={sources})")

    # 4. 知识图谱 + PageRank 演示
    print("\n--- 知识图谱 + PageRank 演示 ---")
    from .kg import (KGBuilder, KnowledgeGraph, KGNode, KGEdge,
                     NodeType, EdgeType, PageRankRanker, FederatedPageRank)

    # 构建专利知识图谱
    builder = KGBuilder()
    patents = [
        {"id": "CN001", "title": "联邦学习隐私保护方法", "abstract": "基于差分隐私的联邦学习训练框架", "cited_patents": ["CN003"], "ipc_codes": ["G06N"]},
        {"id": "CN002", "title": "分布式模型聚合系统", "abstract": "安全聚合协议用于联邦学习", "cited_patents": ["CN001", "CN003"], "ipc_codes": ["G06N", "H04L"]},
        {"id": "CN003", "title": "差分隐私数据发布方法", "abstract": "拉普拉斯机制与指数机制", "cited_patents": [], "ipc_codes": ["G06F"]},
    ]
    kg = builder.build_from_patents(patents)
    print(f"  知识图谱: {kg.node_count} 节点, {kg.edge_count} 边")

    # 计算 PageRank
    ranker = PageRankRanker()
    scores = ranker.compute(kg)
    print(f"  PageRank Top-5:")
    for node_id, score in ranker.top_k(5):
        label = kg.nodes[node_id].label if node_id in kg.nodes else node_id
        print(f"    {node_id}: {label} (PR={score:.4f})")

    # PageRank 重排序
    hybrid_pr = HybridRetriever(hnsw=hnsw, pagerank_scores=scores, pagerank_alpha=0.5)
    reranked = hybrid_pr._pagerank_rerank(fused[:3])
    print(f"  PageRank 重排序后 (alpha=0.5):")
    for r in reranked:
        pr = r.get("pagerank_score", 0)
        final = r.get("final_score", 0)
        print(f"    {r['id']}: {r['title']} (rrf={r['rrf_score']:.6f}, PR={pr:.4f}, final={final:.4f})")

    # 5. 联邦 PageRank 演示
    print("\n--- 联邦 PageRank 演示 ---")
    fed_pr = FederatedPageRank()

    # 模拟客户端 A（有 CN001, CN003）
    kg_a = KnowledgeGraph()
    kg_a.add_node(KGNode(id="CN001", type=NodeType.PATENT, label="联邦学习隐私保护方法"))
    kg_a.add_node(KGNode(id="CN003", type=NodeType.PATENT, label="差分隐私数据发布方法"))
    kg_a.add_edge(KGEdge(source="CN001", target="CN003", type=EdgeType.REFERENCES))
    ranker_a = PageRankRanker()
    scores_a = ranker_a.compute(kg_a)
    fed_pr.add_client_scores(scores_a, node_count=2)

    # 模拟客户端 B（有 CN002, CN003）
    kg_b = KnowledgeGraph()
    kg_b.add_node(KGNode(id="CN002", type=NodeType.PATENT, label="分布式模型聚合系统"))
    kg_b.add_node(KGNode(id="CN003", type=NodeType.PATENT, label="差分隐私数据发布方法"))
    kg_b.add_edge(KGEdge(source="CN002", target="CN003", type=EdgeType.REFERENCES))
    ranker_b = PageRankRanker()
    scores_b = ranker_b.compute(kg_b)
    fed_pr.add_client_scores(scores_b, node_count=2)

    global_scores = fed_pr.aggregate()
    print(f"  客户端数: {fed_pr.client_count}")
    print(f"  全局 PageRank Top-3:")
    for node_id, score in fed_pr.top_k(3):
        print(f"    {node_id} (PR={score:.4f})")

    print("\n" + "=" * 60)
    print("演示完成！")


def run_tests():
    """运行单元测试"""
    import subprocess
    test_dir = PROJECT_ROOT / "tests"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_dir), "-v"],
        cwd=str(PROJECT_ROOT),
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="FedPageIndex")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--host", default="0.0.0.0", help="API 监听地址")
    parser.add_argument("--port", type=int, default=8900, help="API 监听端口")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.test:
        run_tests()
    else:
        run_api(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
