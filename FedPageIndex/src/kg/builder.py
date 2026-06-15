"""
知识图谱构建器 — 从 PageIndex 树节点和文档内容中抽取实体与关系

抽取策略（MVP）：
  1. 结构关系：从 PageIndex 树的父子节点自动生成 hierarchy 边
  2. 实体抽取：基于规则的 NER（Phase 2 升级为 LLM）
  3. 关系抽取：基于规则的模式匹配

KG 存储格式：
  - 节点：{id, type, label, properties}
  - 边：{source, target, type, weight, properties}
"""

from __future__ import annotations
import json
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────────

class NodeType(Enum):
    DOCUMENT = "document"
    SECTION = "section"
    ENTITY = "entity"
    CONCEPT = "concept"
    PATENT = "patent"
    TECHNOLOGY = "technology"


class EdgeType(Enum):
    CONTAINS = "contains"
    REFERENCES = "references"
    RELATES_TO = "relates_to"
    DEPENDS_ON = "depends_on"
    MENTIONS = "mentions"
    BELONGS_TO = "belongs_to"


@dataclass
class KGNode:
    id: str
    type: NodeType
    label: str
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "properties": self.properties,
        }


@dataclass
class KGEdge:
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "weight": self.weight,
            "properties": self.properties,
        }


class KnowledgeGraph:
    """
    知识图谱 — 内存存储，支持节点/边的增删查和导出。
    """

    def __init__(self):
        self.nodes: dict[str, KGNode] = {}
        self.edges: list[KGEdge] = []
        self._adj_out: dict[str, list[KGEdge]] = defaultdict(list)
        self._adj_in: dict[str, list[KGEdge]] = defaultdict(list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def add_node(self, node: KGNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: KGEdge) -> None:
        self.edges.append(edge)
        self._adj_out[edge.source].append(edge)
        self._adj_in[edge.target].append(edge)

    def get_node(self, node_id: str) -> Optional[KGNode]:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str, direction: str = "out") -> list[str]:
        """获取邻居节点 ID。direction: 'out' 出边, 'in' 入边, 'both' 双向"""
        neighbors = set()
        if direction in ("out", "both"):
            for edge in self._adj_out.get(node_id, []):
                neighbors.add(edge.target)
        if direction in ("in", "both"):
            for edge in self._adj_in.get(node_id, []):
                neighbors.add(edge.source)
        return list(neighbors)

    def get_edges(self, source: Optional[str] = None, target: Optional[str] = None,
                  edge_type: Optional[EdgeType] = None) -> list[KGEdge]:
        """按条件查询边"""
        result = self.edges
        if source:
            result = [e for e in result if e.source == source]
        if target:
            result = [e for e in result if e.target == target]
        if edge_type:
            result = [e for e in result if e.type == edge_type]
        return result

    def subgraph(self, node_ids: set[str]) -> "KnowledgeGraph":
        """提取子图"""
        sg = KnowledgeGraph()
        for nid in node_ids:
            node = self.nodes.get(nid)
            if node:
                sg.add_node(node)
        for edge in self.edges:
            if edge.source in node_ids and edge.target in node_ids:
                sg.add_edge(edge)
        return sg

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved KG ({self.node_count} nodes, {self.edge_count} edges) to {path}")

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeGraph":
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        kg = cls()
        for nid, ndata in data["nodes"].items():
            kg.add_node(KGNode(
                id=nid,
                type=NodeType(ndata["type"]),
                label=ndata["label"],
                properties=ndata.get("properties", {}),
            ))
        for edata in data["edges"]:
            kg.add_edge(KGEdge(
                source=edata["source"],
                target=edata["target"],
                type=EdgeType(edata["type"]),
                weight=edata.get("weight", 1.0),
                properties=edata.get("properties", {}),
            ))
        logger.info(f"Loaded KG ({kg.node_count} nodes, {kg.edge_count} edges) from {path}")
        return kg


# ── 实体抽取规则 ──────────────────────────────────────────────

# 技术实体模式
TECH_PATTERNS = [
    (r"(?:联邦学习|federated learning)", "technology"),
    (r"(?:差分隐私|differential privacy)", "technology"),
    (r"(?:知识图谱|knowledge graph)", "technology"),
    (r"(?:向量数据库|vector database)", "technology"),
    (r"(?:深度学习|deep learning)", "technology"),
    (r"(?:强化学习|reinforcement learning)", "technology"),
    (r"(?:自然语言处理|NLP|natural language processing)", "technology"),
    (r"(?:计算机视觉|computer vision)", "technology"),
    (r"(?:图神经网络|graph neural network|GNN)", "technology"),
    (r"(?:Transformer|注意力机制|attention mechanism)", "technology"),
    (r"(?:HNSW|近似最近邻|approximate nearest neighbor)", "technology"),
    (r"(?:PageRank|页面排序)", "technology"),
    (r"(?:RAG|检索增强生成|retrieval augmented generation)", "technology"),
]

# 机构实体模式
ORG_PATTERNS = [
    (r"(?:大学|university|institute|学院|研究院)", "organization"),
    (r"(?:公司|corporation|inc\.|ltd\.|集团)", "organization"),
    (r"(?:Google|Microsoft|Meta|OpenAI|Anthropic)", "organization"),
]


class KGBuilder:
    """
    知识图谱构建器。

    从 PageIndex 树结构或专利数据中抽取实体和关系，构建 KG。
    """

    def __init__(self):
        self.kg = KnowledgeGraph()

    def reset(self) -> "KGBuilder":
        self.kg = KnowledgeGraph()
        return self

    def _get_or_create_entity(self, label: str, entity_type: str, source_id: str) -> str:
        """获取或创建实体节点，返回节点 ID"""
        # 标准化标签
        normalized = label.strip().lower()
        entity_id = f"entity::{normalized}"

        if entity_id not in self.kg.nodes:
            node_type = NodeType.ENTITY if entity_type == "entity" else NodeType.TECHNOLOGY
            if entity_type == "organization":
                node_type = NodeType.ENTITY
            self.kg.add_node(KGNode(
                id=entity_id,
                type=node_type,
                label=label.strip(),
                properties={"entity_type": entity_type},
            ))

        # 添加 MENTIONS 边
        self.kg.add_edge(KGEdge(
            source=source_id,
            target=entity_id,
            type=EdgeType.MENTIONS,
            weight=1.0,
        ))

        return entity_id

    def _extract_entities(self, text: str, doc_label: str, source_id: str) -> list[str]:
        """从文本中抽取实体"""
        entity_ids = []

        # 技术实体
        for pattern, etype in TECH_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                eid = self._get_or_create_entity(match.group(), etype, source_id)
                entity_ids.append(eid)

        # 机构实体
        for pattern, etype in ORG_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                eid = self._get_or_create_entity(match.group(), etype, source_id)
                entity_ids.append(eid)

        return entity_ids

    def build_from_pageindex_tree(
        self,
        structure: list[dict],
        doc_name: str = "document",
        doc_id: Optional[str] = None,
    ) -> KnowledgeGraph:
        """
        从 PageIndex 树结构构建知识图谱。

        自动生成：
          - 文档节点 → 章节节点的 CONTAINS 边
          - 章节节点 → 子章节节点的 CONTAINS 边
          - 从标题/摘要中抽取实体 → MENTIONS 边
        """
        if doc_id is None:
            doc_id = f"doc::{doc_name}"

        # 创建文档节点
        self.kg.add_node(KGNode(
            id=doc_id,
            type=NodeType.DOCUMENT,
            label=doc_name,
            properties={"source": "pageindex"},
        ))

        def _process_node(node: dict, parent_id: str):
            node_id = f"section::{doc_id}::{node.get('node_id', uuid.uuid4().hex[:8])}"
            title = node.get("title", "Untitled")
            summary = node.get("summary", "")

            # 创建章节节点
            self.kg.add_node(KGNode(
                id=node_id,
                type=NodeType.SECTION,
                label=title,
                properties={
                    "summary": summary,
                    "start_index": node.get("start_index"),
                    "end_index": node.get("end_index"),
                },
            ))

            # 父 → 子 CONTAINS 边
            self.kg.add_edge(KGEdge(
                source=parent_id,
                target=node_id,
                type=EdgeType.CONTAINS,
                weight=1.0,
            ))

            # 从标题和摘要中抽取实体
            content = f"{title} {summary}"
            self._extract_entities(content, title, node_id)

            # 递归处理子节点
            for child in node.get("nodes", []):
                _process_node(child, node_id)

        for top_node in structure:
            _process_node(top_node, doc_id)

        # 构建实体间的共现关系
        self._build_cooccurrence_edges()

        logger.info(
            f"Built KG from PageIndex tree: {self.kg.node_count} nodes, {self.kg.edge_count} edges"
        )
        return self.kg

    def build_from_patents(self, patents: list[dict]) -> KnowledgeGraph:
        """
        从专利数据构建知识图谱。

        专利数据格式：
          {id, title, abstract, ipc_codes: [...], citations: [...]}
        """
        for patent in patents:
            patent_id = patent.get("id", uuid.uuid4().hex[:8])
            node_id = f"patent::{patent_id}"

            self.kg.add_node(KGNode(
                id=node_id,
                type=NodeType.PATENT,
                label=patent.get("title", f"Patent {patent_id}"),
                properties={
                    "abstract": patent.get("abstract", ""),
                    "ipc_codes": patent.get("ipc_codes", []),
                },
            ))

            # 引用关系
            for cited_id in patent.get("cited_patents", []):
                cited_node_id = f"patent::{cited_id}"
                if cited_node_id not in self.kg.nodes:
                    self.kg.add_node(KGNode(
                        id=cited_node_id,
                        type=NodeType.PATENT,
                        label=f"Patent {cited_id}",
                        properties={"placeholder": True},
                    ))
                self.kg.add_edge(KGEdge(
                    source=node_id,
                    target=cited_node_id,
                    type=EdgeType.REFERENCES,
                    weight=1.0,
                ))

            # IPC 分类
            for ipc in patent.get("ipc_codes", []):
                ipc_id = f"ipc::{ipc}"
                if ipc_id not in self.kg.nodes:
                    self.kg.add_node(KGNode(
                        id=ipc_id,
                        type=NodeType.CONCEPT,
                        label=ipc,
                        properties={"type": "ipc_code"},
                    ))
                self.kg.add_edge(KGEdge(
                    source=node_id,
                    target=ipc_id,
                    type=EdgeType.BELONGS_TO,
                    weight=1.0,
                ))

            # 从标题和摘要中抽取实体
            content = f"{patent.get('title', '')} {patent.get('abstract', '')}"
            self._extract_entities(content, patent_id, node_id)

        self._build_cooccurrence_edges()

        logger.info(
            f"Built KG from patents: {self.kg.node_count} nodes, {self.kg.edge_count} edges"
        )
        return self.kg

    def _build_cooccurrence_edges(self):
        """
        构建实体间的共现关系。

        如果两个实体被同一个节点提及，则它们之间存在 RELATES_TO 边。
        权重 = 共现次数。
        """
        # 找出每个源节点提及的实体
        source_entities: dict[str, list[str]] = defaultdict(list)
        for edge in self.kg.edges:
            if edge.type == EdgeType.MENTIONS:
                source_entities[edge.source].append(edge.target)

        # 统计共现
        cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
        for entities in source_entities.values():
            unique = list(set(entities))
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    pair = tuple(sorted([unique[i], unique[j]]))
                    cooccurrence[pair] += 1

        # 添加共现边
        for (e1, e2), count in cooccurrence.items():
            self.kg.add_edge(KGEdge(
                source=e1,
                target=e2,
                type=EdgeType.RELATES_TO,
                weight=float(count),
            ))
