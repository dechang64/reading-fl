"""
HNSW 向量检索器 — 基于 hnswlib 的高性能近似最近邻搜索

复用 fundfl-upgrade 的 HNSW 设计，Python 实现用于 MVP。
Phase 4 迁移到 Rust 原生实现。
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

import hnswlib
import numpy as np

logger = logging.getLogger(__name__)


class HnswRetriever:
    """
    HNSW 向量检索器。

    支持：
      - 插入/批量插入向量
      - KNN 搜索
      - 持久化到磁盘
      - 元数据关联
    """

    def __init__(
        self,
        dimension: int = 768,
        max_elements: int = 100000,
        ef_construction: int = 200,
        m: int = 16,
        space: str = "cosine",
    ):
        self.dimension = dimension
        self.max_elements = max_elements
        self.ef_construction = ef_construction
        self.m = m
        self.space = space

        self._index = hnswlib.Index(space=space, dim=dimension)
        self._index.init_index(
            max_elements=max_elements,
            ef_construction=ef_construction,
            M=m,
        )
        self._index.set_ef(50)  # 搜索时的 ef

        self._ids: list[str] = []
        self._id_to_label: dict[str, int] = {}
        self._label_to_id: dict[int, str] = {}
        self._metadata: dict[str, dict] = {}
        self._next_label = 0

    @property
    def count(self) -> int:
        """当前索引中的向量数量"""
        return len(self._ids)

    def insert(self, id: str, vector: np.ndarray | list[float], metadata: Optional[dict] = None) -> None:
        """插入单个向量"""
        if id in self._id_to_label:
            raise ValueError(f"ID {id} already exists in index")

        label = self._next_label
        self._next_label += 1

        vec = np.asarray(vector, dtype=np.float32)
        if vec.shape != (self.dimension,):
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {vec.shape[0]}")

        self._index.add_items(vec.reshape(1, -1), [label])
        self._ids.append(id)
        self._id_to_label[id] = label
        self._label_to_id[label] = id
        if metadata:
            self._metadata[id] = metadata

    def insert_batch(
        self,
        entries: list[tuple[str, list[float], Optional[dict]]],
    ) -> int:
        """
        批量插入向量。

        Args:
            entries: [(id, vector, metadata_or_None), ...]

        Returns:
            插入的向量数量
        """
        ids = []
        vecs = []
        metas = []
        for id, vector, meta in entries:
            if id in self._id_to_label:
                raise ValueError(f"ID {id} already exists in index")
            ids.append(id)
            vecs.append(vector)
            metas.append(meta or {})

        vecs_arr = np.asarray(vecs, dtype=np.float32)
        if vecs_arr.ndim != 2 or vecs_arr.shape[1] != self.dimension:
            raise ValueError(f"Vectors shape mismatch: expected (N, {self.dimension}), got {vecs_arr.shape}")

        labels = list(range(self._next_label, self._next_label + len(ids)))
        self._index.add_items(vecs_arr, labels)

        for i, id in enumerate(ids):
            self._ids.append(id)
            self._id_to_label[id] = labels[i]
            self._label_to_id[labels[i]] = id
            if metas[i]:
                self._metadata[id] = metas[i]

        self._next_label += len(ids)
        return len(ids)

    def delete(self, id: str) -> bool:
        """
        标记删除一个向量。

        注意：hnswlib 不支持真正的删除，这里只是从映射中移除。
        搜索结果会自动过滤已删除的 ID。

        Returns:
            True 如果成功删除，False 如果 ID 不存在
        """
        if id not in self._id_to_label:
            return False

        label = self._id_to_label.pop(id)
        self._label_to_id.pop(label, None)
        self._ids.remove(id)
        self._metadata.pop(id, None)
        # 注意：hnswlib 内部索引不删除，但 search 时 _label_to_id 找不到就跳过
        return True

    def search(
        self,
        query_vector: np.ndarray | list[float],
        k: int = 10,
        ef_search: Optional[int] = None,
    ) -> list[tuple[str, float, dict]]:
        """
        搜索最近的 k 个邻居。

        Returns:
            [(id, distance, metadata), ...] 按距离升序排列
        """
        if self.count == 0:
            return []

        if ef_search:
            self._index.set_ef(ef_search)

        vec = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        labels, distances = self._index.knn_query(vec, k=min(k, self.count))

        results = []
        for label, dist in zip(labels[0], distances[0]):
            id = self._label_to_id.get(int(label))
            if id:  # 跳过已删除的（label 不在映射中）
                meta = self._metadata.get(id, {})
                results.append((id, float(dist), meta))

        return results

    def save(self, path: str | Path) -> None:
        """持久化索引到磁盘"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        self._index.save_index(str(path / "index.bin"))

        meta = {
            "dimension": self.dimension,
            "max_elements": self.max_elements,
            "ef_construction": self.ef_construction,
            "m": self.m,
            "space": self.space,
            "ids": self._ids,
            "id_to_label": self._id_to_label,
            "metadata": self._metadata,
            "next_label": self._next_label,
        }
        with open(path / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved HNSW index ({self.count} vectors) to {path}")

    @classmethod
    def load(cls, path: str | Path) -> "HnswRetriever":
        """从磁盘加载索引"""
        path = Path(path)

        with open(path / "meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)

        retriever = cls(
            dimension=meta["dimension"],
            max_elements=meta["max_elements"],
            ef_construction=meta["ef_construction"],
            m=meta["m"],
            space=meta["space"],
        )

        retriever._index = hnswlib.Index(space=meta["space"], dim=meta["dimension"])
        retriever._index.load_index(str(path / "index.bin"))
        retriever._ids = meta["ids"]
        retriever._id_to_label = meta["id_to_label"]
        retriever._label_to_id = {int(v): k for k, v in meta["id_to_label"].items()}
        retriever._metadata = meta.get("metadata", {})
        retriever._next_label = meta["next_label"]

        logger.info(f"Loaded HNSW index ({retriever.count} vectors) from {path}")
        return retriever
