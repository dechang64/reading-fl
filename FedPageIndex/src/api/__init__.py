"""
FedPageIndex HTTP API — 基于 FastAPI

端点：
  POST /search        — 混合检索
  POST /index/pdf     — 索引 PDF 文档
  POST /index/vector  — 索引向量
  GET  /stats         — 系统统计
  GET  /health        — 健康检查
"""

from __future__ import annotations
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..retriever import HybridRetriever, HnswRetriever, PageIndexRetriever

logger = logging.getLogger(__name__)

# ── Pydantic Models ──────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="查询文本")
    query_vector: Optional[list[float]] = Field(None, description="查询向量（语义检索需要）")
    k: int = Field(10, ge=1, le=100, description="返回结果数量")
    doc_id: Optional[str] = Field(None, description="指定文档 ID")


class SearchResult(BaseModel):
    id: str
    title: str = ""
    score: float = 0.0
    rrf_score: Optional[float] = None
    content: str = ""
    metadata: dict = {}


class SearchResponse(BaseModel):
    routing: dict
    results: list[SearchResult]
    pageindex_count: int = 0
    hnsw_count: int = 0


class IndexPdfRequest(BaseModel):
    pdf_path: str = Field(..., description="PDF 文件路径")


class IndexPdfResponse(BaseModel):
    doc_id: str
    doc_name: str


class IndexVectorRequest(BaseModel):
    id: str = Field(..., description="向量 ID")
    vector: list[float] = Field(..., description="向量值")
    metadata: Optional[dict] = Field(None, description="元数据")


class IndexVectorResponse(BaseModel):
    inserted: int


class StatsResponse(BaseModel):
    hnsw_count: int = 0
    pageindex_doc_count: int = 0
    dimension: int = 0


# ── App Factory ──────────────────────────────────────────────

def create_app(
    hnsw: Optional[HnswRetriever] = None,
    pageindex: Optional[PageIndexRetriever] = None,
) -> FastAPI:
    """创建 FastAPI 应用"""

    hybrid = HybridRetriever(hnsw=hnsw, pageindex=pageindex)

    app = FastAPI(
        title="FedPageIndex",
        description="联邦混合检索与知识图谱排序系统",
        version="0.1.0",
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/stats", response_model=StatsResponse)
    async def stats():
        return StatsResponse(
            hnsw_count=hybrid.hnsw.count if hybrid.hnsw else 0,
            pageindex_doc_count=hybrid.pageindex.doc_count if hybrid.pageindex else 0,
            dimension=hybrid.hnsw.dimension if hybrid.hnsw else 0,
        )

    @app.post("/search", response_model=SearchResponse)
    async def search(req: SearchRequest):
        if not req.query_vector and not hybrid.pageindex:
            raise HTTPException(400, "query_vector required when PageIndex is not available")

        result = hybrid.search(
            query=req.query,
            query_vector=req.query_vector,
            k=req.k,
            doc_id=req.doc_id,
        )

        return SearchResponse(
            routing=result["routing"],
            results=[SearchResult(**r) for r in result["results"]],
            pageindex_count=len(result["pageindex_results"]),
            hnsw_count=len(result["hnsw_results"]),
        )

    @app.post("/index/pdf", response_model=IndexPdfResponse)
    async def index_pdf(req: IndexPdfRequest):
        if not hybrid.pageindex:
            raise HTTPException(400, "PageIndex not configured")

        doc_id = hybrid.pageindex.index(req.pdf_path)
        doc_name = hybrid.pageindex._client.documents[doc_id].get("doc_name", "")

        return IndexPdfResponse(doc_id=doc_id, doc_name=doc_name)

    @app.post("/index/vector", response_model=IndexVectorResponse)
    async def index_vector(req: IndexVectorRequest):
        if not hybrid.hnsw:
            raise HTTPException(400, "HNSW not configured")

        hybrid.hnsw.insert(req.id, req.vector, metadata=req.metadata)
        return IndexVectorResponse(inserted=1)

    return app
