"""
PageIndex 树检索器 — 封装 VectifyAI/PageIndex 的树索引和推理检索

核心流程：
  1. index() — 将文档解析为层级树索引
  2. search() — LLM 在树上推理导航，找到最相关节点
  3. retrieve() — 返回节点的原始内容
"""

from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# PageIndex 源码路径
PAGEINDEX_SRC = Path(__file__).parent.parent.parent.parent / "PageIndex"

logger = logging.getLogger(__name__)


class PageIndexRetriever:
    """
    PageIndex 树检索器。

    封装 PageIndexClient，提供统一的 search 接口。
    """

    def __init__(
        self,
        workspace: Optional[str | Path] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._client = None
        self._workspace = Path(workspace) if workspace else PAGEINDEX_SRC / "examples" / "workspace"
        self._model = model
        self._api_key = api_key
        self._doc_ids: list[str] = []  # 已索引的文档 ID 列表

    def _ensure_client(self):
        """延迟初始化 PageIndexClient"""
        if self._client is not None:
            return

        # 将 PageIndex 源码加入 sys.path
        src = str(PAGEINDEX_SRC)
        if src not in sys.path:
            sys.path.insert(0, src)

        from pageindex.client import PageIndexClient

        kwargs = {"workspace": str(self._workspace)}
        if self._model:
            kwargs["model"] = self._model
        if self._api_key:
            kwargs["api_key"] = self._api_key

        self._client = PageIndexClient(**kwargs)
        # 记录已有文档
        self._doc_ids = list(self._client.documents.keys())
        logger.info(f"PageIndex client initialized, {len(self._doc_ids)} docs loaded")

    def index(self, pdf_path: str | Path) -> str:
        """
        索引一个 PDF 文档。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            doc_id: 文档 ID
        """
        self._ensure_client()
        pdf_path = Path(pdf_path)

        # 检查是否已索引
        for doc_id, doc in self._client.documents.items():
            if doc.get("doc_name") == pdf_path.name:
                logger.info(f"Document already indexed: {doc_id}")
                return doc_id

        doc_id = self._client.index(pdf_path)
        self._doc_ids.append(doc_id)
        logger.info(f"Indexed document: {pdf_path.name} → {doc_id}")
        return doc_id

    def search(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        在树索引上搜索。

        返回格式统一为 [{id, title, score, content, metadata}, ...]
        与 HnswRetriever.search() 返回格式对齐。

        Args:
            query: 查询文本
            doc_id: 指定文档 ID（None 则搜索所有文档）
            top_k: 返回结果数量

        Returns:
            检索结果列表
        """
        self._ensure_client()

        results = []
        doc_ids = [doc_id] if doc_id else self._doc_ids

        for did in doc_ids:
            try:
                # 获取文档树结构
                structure_json = self._client.get_document_structure(did)
                structure = json.loads(structure_json)

                # 遍历树节点，计算与查询的相关性
                scored_nodes = self._score_nodes(query, structure)
                scored_nodes.sort(key=lambda x: x["score"], reverse=True)

                for node in scored_nodes[:top_k]:
                    # 获取节点内容
                    content = self._get_node_content(did, node)
                    results.append({
                        "id": f"{did}::{node.get('node_id', '')}",
                        "title": node.get("title", ""),
                        "score": node["score"],
                        "content": content,
                        "metadata": {
                            "doc_id": did,
                            "node_id": node.get("node_id", ""),
                            "start_index": node.get("start_index"),
                            "end_index": node.get("end_index"),
                            "source": "pageindex",
                        },
                    })
            except Exception as e:
                logger.error(f"Error searching doc {did}: {e}")

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _score_nodes(self, query: str, structure: list[dict]) -> list[dict]:
        """
        基于关键词匹配对树节点评分。

        MVP 用简单的关键词重叠度，Phase 2 升级为 LLM 推理评分。
        """
        query_terms = set(query.lower().split())
        scored = []

        def _traverse(nodes, depth=0):
            for node in nodes:
                title = node.get("title", "").lower()
                summary = node.get("summary", "").lower()
                text = node.get("text", "").lower()

                # 标题匹配权重最高
                title_terms = set(title.split())
                title_overlap = len(query_terms & title_terms) / max(len(query_terms), 1)

                # 摘要匹配
                summary_terms = set(summary.split())
                summary_overlap = len(query_terms & summary_terms) / max(len(query_terms), 1)

                # 全文匹配
                text_terms = set(text.split())
                text_overlap = len(query_terms & text_terms) / max(len(query_terms), 1)

                # 加权得分：标题 3x，摘要 2x，全文 1x
                # 深度惩罚：越深的节点越具体，适当加分
                depth_bonus = 0.1 * depth
                score = (3.0 * title_overlap + 2.0 * summary_overlap + 1.0 * text_overlap + depth_bonus)

                scored.append({**node, "score": min(score, 1.0)})

                if node.get("nodes"):
                    _traverse(node["nodes"], depth + 1)

        _traverse(structure)
        return scored

    def _get_node_content(self, doc_id: str, node: dict) -> str:
        """获取节点的原始文本内容"""
        start = node.get("start_index")
        end = node.get("end_index")

        if start is None or end is None:
            return node.get("text", "")

        try:
            pages_str = f"{start}-{end}"
            content_json = self._client.get_page_content(doc_id, pages_str)
            content = json.loads(content_json)
            if isinstance(content, list):
                return "\n".join(
                    page.get("content", "") for page in content
                )
            return str(content)
        except Exception as e:
            logger.warning(f"Failed to get page content for {doc_id}: {e}")
            return node.get("text", "")

    @property
    def doc_count(self) -> int:
        """已索引文档数量"""
        return len(self._doc_ids)

    def get_document_structure(self, doc_id: str) -> list[dict]:
        """获取文档的树结构"""
        self._ensure_client()
        structure_json = self._client.get_document_structure(doc_id)
        return json.loads(structure_json)
