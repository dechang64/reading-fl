"""
twc_core.vector — Vector Search Engine
======================================
In-memory vector search with cosine similarity.
Python fallback for Rust HNSW (production).

Usage:
    from twc_core.vector import VectorEngine
    engine = VectorEngine(dimension=768)
    engine.insert("img_001", np.random.randn(768))
    results = engine.search(query, k=5)
"""

import numpy as np
from typing import Optional, List, Tuple
from collections import OrderedDict


class VectorEngine:
    """In-memory vector search engine with cosine similarity.

    For production, replace with Rust HNSW via gRPC.
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.vectors: OrderedDict[str, np.ndarray] = OrderedDict()
        self.metadata: dict[str, dict] = {}

    def insert(self, id: str, vector: np.ndarray, metadata: Optional[dict] = None) -> None:
        """Insert a vector."""
        if len(vector) != self.dimension:
            raise ValueError(f"Expected dimension {self.dimension}, got {len(vector)}")
        self.vectors[id] = vector.astype(np.float32)
        self.metadata[id] = metadata or {}

    def bulk_insert(self, ids: List[str], vectors: np.ndarray,
                    metadata: Optional[List[dict]] = None) -> int:
        """Insert multiple vectors."""
        count = 0
        for i, vid in enumerate(ids):
            meta = metadata[i] if metadata else None
            self.insert(vid, vectors[i], meta)
            count += 1
        return count

    def search(self, query: np.ndarray, k: int = 5) -> List[Tuple[str, float]]:
        """Search for k most similar vectors.

        Returns:
            List of (id, similarity_score) tuples, sorted descending.
        """
        if len(self.vectors) == 0:
            return []

        query = query.astype(np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        results = []
        for vid, vec in self.vectors.items():
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            similarity = float(np.dot(query, vec) / (query_norm * vec_norm))
            results.append((vid, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def delete(self, ids: List[str]) -> int:
        """Delete vectors by IDs."""
        count = 0
        for vid in ids:
            if vid in self.vectors:
                del self.vectors[vid]
                self.metadata.pop(vid, None)
                count += 1
        return count

    def __len__(self) -> int:
        return len(self.vectors)

    def __repr__(self) -> str:
        return f"VectorEngine(dimension={self.dimension}, vectors={len(self)})"

    def get_stats(self) -> dict:
        """Return engine statistics."""
        return {
            "total_vectors": len(self),
            "dimension": self.dimension,
        }
