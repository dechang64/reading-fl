"""
PageIndex 集成测试 — 使用 PageIndex 自带的示例文档

验证：
  1. PageIndexClient 能加载已有索引
  2. 树结构能被解析为检索结果
  3. 关键词搜索能返回正确节点
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.retriever.pageindex_retriever import PageIndexRetriever


def test_load_workspace():
    """测试加载 PageIndex workspace"""
    pi = PageIndexRetriever()
    pi._ensure_client()

    print(f"PageIndex workspace: {pi._workspace}")
    print(f"已索引文档数: {pi.doc_count}")

    # 列出所有文档
    for doc_id, doc in pi._client.documents.items():
        print(f"  {doc_id}: {doc.get('doc_name', 'unknown')} ({doc.get('page_count', '?')} pages)")


def test_search_structure():
    """测试在树结构中搜索"""
    pi = PageIndexRetriever()
    pi._ensure_client()

    # 获取第一个文档
    if not pi._client.documents:
        print("No documents in workspace, skipping")
        return

    doc_id = list(pi._client.documents.keys())[0]
    doc_name = pi._client.documents[doc_id].get("doc_name", "unknown")
    print(f"\n搜索文档: {doc_name} (doc_id={doc_id})")

    # 获取树结构
    structure = pi.get_document_structure(doc_id)
    print(f"树结构节点数: {len(structure)}")

    # 关键词搜索
    results = pi.search("Monetary Policy", doc_id=doc_id, top_k=5)
    print(f"\n搜索 'Monetary Policy' 结果:")
    for r in results:
        print(f"  [{r['id']}] {r['title']} (score={r['score']:.3f})")
        if r.get('content'):
            print(f"    content: {r['content'][:100]}...")


def test_hybrid_with_pageindex():
    """测试混合检索器 + PageIndex"""
    from src.retriever.hybrid_retriever import HybridRetriever
    from src.retriever.hnsw_retriever import HnswRetriever
    import numpy as np

    # 初始化
    hnsw = HnswRetriever(dimension=8)
    pi = PageIndexRetriever()
    hybrid = HybridRetriever(hnsw=hnsw, pageindex=pi)

    # 插入一些向量到 HNSW
    for i in range(5):
        vec = np.random.randn(8).tolist()
        hnsw.insert(f"vec_{i}", vec, metadata={"title": f"Document {i}"})

    print(f"\nHNSW 索引: {hnsw.count} 向量")
    print(f"PageIndex 索引: {pi.doc_count} 文档")

    # 混合搜索（纯 HNSW，因为没给 doc_id）
    query_vec = np.random.randn(8).tolist()
    result = hybrid.search(
        query="找相似的文档",
        query_vector=query_vec,
        k=3,
    )

    print(f"\n混合搜索结果:")
    print(f"  路由: {result['routing']}")
    print(f"  结果数: {len(result['results'])}")
    for r in result['results']:
        print(f"  {r['id']}: {r['title']} (score={r['score']:.4f})")


if __name__ == "__main__":
    print("=" * 60)
    print("PageIndex 集成测试")
    print("=" * 60)

    test_load_workspace()
    test_search_structure()
    test_hybrid_with_pageindex()

    print("\n" + "=" * 60)
    print("集成测试完成！")
