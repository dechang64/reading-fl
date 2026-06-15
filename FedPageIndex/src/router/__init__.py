"""
查询路由器 — 判断查询走哪条检索路径

路由策略：
  - structural: 结构化文档查询 → PageIndex 树搜索
  - semantic: 语义相似查询 → HNSW 向量检索
  - hybrid: 混合查询 → 两条路并行 + RRF 融合

基于关键词 + 规则的路由（MVP），Phase 2 升级为 LLM 路由。
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QueryType(Enum):
    STRUCTURAL = "structural"   # PageIndex 树搜索
    SEMANTIC = "semantic"       # HNSW 向量检索
    HYBRID = "hybrid"           # 两条路并行


@dataclass
class RoutingResult:
    query_type: QueryType
    confidence: float           # 0.0 ~ 1.0
    rewritten_query: str        # 可能重写后的查询
    reason: str                 # 路由理由


# 结构化查询的关键词模式
STRUCTURAL_PATTERNS = [
    r"(?:第[一二三四五六七八九十\d]+[章节条])",      # 第X章/节/条
    r"(?:section|chapter|part)\s+\d+",              # Section X, Chapter Y
    r"(?:目录|索引|目录表|table of contents)",        # 目录相关
    r"(?:哪一页|在哪页|which page)",                  # 页码定位
    r"(?:标题|标题是|what is the title)",             # 标题查询
    r"(?:摘要|summary|abstract)",                    # 摘要查询
    r"(?:定义|definition|什么是|what is .+ defined)", # 定义查询
    r"(?:流程|步骤|procedure|step \d+)",             # 流程/步骤
    r"(?:法规|条例|regulation|act|rule \d+)",        # 法规条文
    r"(?:条款|clause|article \d+)",                  # 条款
]

# 语义查询的关键词模式
SEMANTIC_PATTERNS = [
    r"(?:相似|类似|similar|like)",                   # 相似性查询
    r"(?:相关|related|relevant)",                    # 相关性查询
    r"(?:比较|对比|compare|versus|vs\.?)",           # 比较查询
    r"(?:推荐|recommend|suggest)",                   # 推荐查询
    r"(?:最像|closest|nearest)",                     # 最近邻查询
    r"(?:同类|same kind|same type)",                 # 同类查询
    r"(?:找|find|search for).+(?:基金|专利|论文|文档)", # 搜索类
]


def route_query(query: str, has_pageindex: bool = True, has_hnsw: bool = True) -> RoutingResult:
    """
    路由查询到合适的检索通道。

    Args:
        query: 用户查询文本
        has_pageindex: PageIndex 是否可用
        has_hnsw: HNSW 向量索引是否可用

    Returns:
        RoutingResult with routing decision
    """
    query_lower = query.lower().strip()

    # 如果只有一个通道可用，直接走那个
    if has_pageindex and not has_hnsw:
        return RoutingResult(
            query_type=QueryType.STRUCTURAL,
            confidence=1.0,
            rewritten_query=query,
            reason="HNSW unavailable, routing to PageIndex only"
        )
    if has_hnsw and not has_pageindex:
        return RoutingResult(
            query_type=QueryType.SEMANTIC,
            confidence=1.0,
            rewritten_query=query,
            reason="PageIndex unavailable, routing to HNSW only"
        )

    # 计算模式匹配分数
    structural_score = 0.0
    semantic_score = 0.0

    for pattern in STRUCTURAL_PATTERNS:
        if re.search(pattern, query_lower):
            structural_score += 1.0

    for pattern in SEMANTIC_PATTERNS:
        if re.search(pattern, query_lower):
            semantic_score += 1.0

    # 查询长度启发式：短查询倾向语义，长查询倾向结构
    if len(query) < 15:
        semantic_score += 0.5
    elif len(query) > 50:
        structural_score += 0.5

    # 决策
    total = structural_score + semantic_score
    if total == 0:
        # 无明确信号，走混合
        return RoutingResult(
            query_type=QueryType.HYBRID,
            confidence=0.3,
            rewritten_query=query,
            reason="No clear routing signal, defaulting to hybrid"
        )

    structural_ratio = structural_score / total
    semantic_ratio = semantic_score / total

    if structural_ratio > 0.65:
        return RoutingResult(
            query_type=QueryType.STRUCTURAL,
            confidence=structural_ratio,
            rewritten_query=query,
            reason=f"Structural patterns matched (score={structural_score:.1f})"
        )
    elif semantic_ratio > 0.65:
        return RoutingResult(
            query_type=QueryType.SEMANTIC,
            confidence=semantic_ratio,
            rewritten_query=query,
            reason=f"Semantic patterns matched (score={semantic_score:.1f})"
        )
    else:
        return RoutingResult(
            query_type=QueryType.HYBRID,
            confidence=max(structural_ratio, semantic_ratio),
            rewritten_query=query,
            reason=f"Mixed signals (struct={structural_score:.1f}, semantic={semantic_score:.1f})"
        )
