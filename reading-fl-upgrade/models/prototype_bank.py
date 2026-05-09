"""
Reading-FL Quality Prototype Bank

Maintains domain-specific quality prototypes learned from high-quality reflections.
New excerpts are scored by their distance to the nearest prototype.
"""

import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict


class QualityPrototypeBank:
    """
    Quality prototype bank for excerpt evaluation.

    Instead of a single quality threshold, each domain (文学, 哲学, 科幻, etc.)
    maintains its own set of quality prototypes.

    A prototype is a high-dimensional representation of "what a high-quality
    excerpt looks like in this domain." Prototypes are learned from excerpts
    that consistently generate deep, emotionally rich reflections.

    Key insight:
        Quality is not absolute — it's relative to the domain.
        A "good" sci-fi excerpt looks different from a "good" literary excerpt.
        Prototype banks capture this domain-specific notion of quality.
    """

    def __init__(
        self,
        embedding_dim: int = 128,
        n_prototypes_per_domain: int = 8,
        similarity_threshold: float = 0.85,
        quality_percentile: float = 75,
    ):
        self.embedding_dim = embedding_dim
        self.n_prototypes = n_prototypes_per_domain
        self.similarity_threshold = similarity_threshold
        self.quality_percentile = quality_percentile

        # domain -> list of prototype vectors
        self.prototypes: Dict[str, np.ndarray] = {}

        # domain -> list of (excerpt_id, embedding, quality_score)
        self.candidates: Dict[str, List[Tuple[str, np.ndarray, float]]] = defaultdict(list)

        # Statistics
        self.n_updates = 0
        self.n_domains = 0

    def add_candidate(
        self,
        domain: str,
        excerpt_id: str,
        embedding: np.ndarray,
        quality_score: float,
    ):
        """
        Add a candidate excerpt for prototype consideration.

        Candidates are accumulated and periodically used to update prototypes.
        """
        self.candidates[domain].append((excerpt_id, embedding.copy(), quality_score))

    def update_prototypes(self):
        """
        Update prototypes from accumulated candidates.

        For each domain:
        1. Filter candidates above quality percentile
        2. Cluster high-quality candidates
        3. Select cluster centers as new prototypes
        """
        for domain, candidates in self.candidates.items():
            if len(candidates) < 3:
                continue

            embeddings = np.array([c[1] for c in candidates])
            scores = np.array([c[2] for c in candidates])

            # Filter by quality percentile
            threshold = np.percentile(scores, self.quality_percentile)
            mask = scores >= threshold
            high_quality_embs = embeddings[mask]

            if len(high_quality_embs) < 2:
                continue

            # Simple clustering: greedy farthest-point sampling
            new_prototypes = self._select_prototypes(
                high_quality_embs, self.n_prototypes
            )

            # Merge with existing prototypes
            if domain in self.prototypes and len(self.prototypes[domain]) > 0:
                existing = self.prototypes[domain]
                # Keep prototypes that are still relevant
                merged = self._merge_prototypes(existing, new_prototypes)
                self.prototypes[domain] = merged
            else:
                self.prototypes[domain] = new_prototypes

            self.n_domains = len(self.prototypes)

        # Clear candidates after update
        self.candidates.clear()
        self.n_updates += 1

    def _select_prototypes(
        self, points: np.ndarray, n: int
    ) -> np.ndarray:
        """
        Greedy farthest-point sampling to select diverse prototypes.

        This ensures prototypes cover the full space of high-quality content,
        not just a cluster of similar excerpts.
        """
        if len(points) <= n:
            return points

        # Start with the point closest to the centroid
        centroid = points.mean(axis=0)
        distances = np.linalg.norm(points - centroid, axis=1)
        selected = [np.argmin(distances)]

        for _ in range(n - 1):
            # Find the point farthest from all selected points
            selected_points = points[selected]
            min_distances = np.min(
                np.linalg.norm(points[:, None] - selected_points[None, :], axis=2),
                axis=1
            )
            # Exclude already selected
            min_distances[selected] = -1
            selected.append(np.argmax(min_distances))

        return points[selected]

    def _merge_prototypes(
        self, existing: np.ndarray, new: np.ndarray
    ) -> np.ndarray:
        """Merge existing and new prototypes, removing near-duplicates."""
        all_prototypes = np.vstack([existing, new])

        # Greedy deduplication: keep prototype if its cosine distance to all
        # kept prototypes exceeds the dedup threshold.
        # similarity_threshold controls how similar two prototypes must be
        # to be considered duplicates (higher = more aggressive dedup).
        dedup_dist = 1.0 - self.similarity_threshold  # cosine distance threshold
        kept = [0]
        for i in range(1, len(all_prototypes)):
            # Use cosine distance (not L2) to match the similarity metric
            emb_norm = all_prototypes[i] / (np.linalg.norm(all_prototypes[i]) + 1e-8)
            kept_norms = all_prototypes[kept] / (np.linalg.norm(all_prototypes[kept], axis=1, keepdims=True) + 1e-8)
            similarities = kept_norms @ emb_norm
            if similarities.max() >= self.similarity_threshold:
                continue  # Too similar to an existing prototype, skip
            kept.append(i)
            if len(kept) >= self.n_prototypes:
                break

        return all_prototypes[kept]

    def score(self, embedding: np.ndarray, domain: str) -> float:
        """
        Score an excerpt's quality based on prototype similarity.

        Returns:
            Quality score in [0, 1]:
            - 1.0 = very similar to a quality prototype
            - 0.0 = no quality prototypes exist or very dissimilar
        """
        if domain not in self.prototypes or len(self.prototypes[domain]) == 0:
            return 0.5  # Neutral when no prototypes exist

        prototypes = self.prototypes[domain]

        # Cosine similarity to nearest prototype
        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        proto_norms = prototypes / (np.linalg.norm(prototypes, axis=1, keepdims=True) + 1e-8)
        similarities = proto_norms @ emb_norm

        max_sim = similarities.max()
        avg_sim = similarities.mean()

        # Weighted combination: nearest prototype matters more
        score = 0.7 * max_sim + 0.3 * avg_sim
        return round(float(np.clip(score, 0, 1)), 4)

    def score_batch(
        self, embeddings: np.ndarray, domains: List[str]
    ) -> np.ndarray:
        """Score a batch of excerpts."""
        return np.array([
            self.score(emb, domain)
            for emb, domain in zip(embeddings, domains)
        ])

    def get_top_excerpts(
        self,
        excerpt_embeddings: np.ndarray,
        excerpt_ids: List[str],
        domains: List[str],
        k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Get top-k highest quality excerpts across all domains.

        Returns:
            List of (excerpt_id, quality_score) sorted by score descending.
        """
        scores = self.score_batch(excerpt_embeddings, domains)
        ranked = sorted(
            zip(excerpt_ids, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:k]

    def get_domain_stats(self) -> Dict[str, dict]:
        """Get statistics per domain."""
        stats = {}
        for domain, prototypes in self.prototypes.items():
            stats[domain] = {
                "n_prototypes": len(prototypes),
                "avg_inter_proto_dist": float(
                    np.mean([
                        np.linalg.norm(prototypes[i] - prototypes[j])
                        for i in range(len(prototypes))
                        for j in range(i + 1, len(prototypes))
                    ]) if len(prototypes) > 1 else 0
                ),
            }
        return stats

    def __repr__(self) -> str:
        return (
            f"QualityPrototypeBank("
            f"domains={self.n_domains}, "
            f"updates={self.n_updates}, "
            f"prototypes_per_domain={self.n_prototypes})"
        )
