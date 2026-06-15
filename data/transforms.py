"""
Reading-FL Text Processing

Character n-gram TF-IDF encoder for Chinese + English text.
No external dependencies — pure Python + NumPy.
"""

import numpy as np
import re
import math
from collections import Counter
from typing import List, Dict, Tuple, Optional


class TextEncoder:
    """
    Character n-gram based text encoder.

    Why character n-grams instead of word segmentation:
    1. No dependency on jieba/other segmenters
    2. Handles Chinese + English + mixed text naturally
    3. Robust to typos and informal language
    4. Works well for short texts (reflections, excerpts)
    """

    def __init__(self, max_features: int = 512, ngram_range: Tuple[int, int] = (1, 3)):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.vocab: Dict[str, int] = {}       # ngram -> index
        self.idf: np.ndarray = np.array([])   # IDF weights
        self._fitted = False

    def _extract_ngrams(self, text: str) -> List[str]:
        """Extract character n-grams from text."""
        # Normalize: keep Chinese chars, ASCII letters, digits
        text = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9]', ' ', text)
        text = text.lower().strip()
        if not text:
            return []

        chars = list(text.replace(' ', ''))
        ngrams = []
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(chars) - n + 1):
                ngrams.append(''.join(chars[i:i + n]))
        return ngrams

    def fit(self, texts: List[str], min_df: int = 2, max_df: float = 0.95):
        """
        Build vocabulary and compute IDF from a corpus.

        Args:
            texts: List of documents
            min_df: Minimum document frequency
            max_df: Maximum document frequency (ratio)
        """
        n_docs = len(texts)

        # Count document frequency for each n-gram
        df = Counter()
        for text in texts:
            ngrams = set(self._extract_ngrams(text))
            for ng in ngrams:
                df[ng] += 1

        # Filter by min_df and max_df
        min_count = max(min_df, 1)
        max_count = int(max_df * n_docs)
        valid_ngrams = {
            ng: count for ng, count in df.items()
            if min_count <= count <= max_count
        }

        # Select top max_features by document frequency
        sorted_ngrams = sorted(valid_ngrams.items(), key=lambda x: -x[1])
        if len(sorted_ngrams) > self.max_features:
            sorted_ngrams = sorted_ngrams[:self.max_features]

        self.vocab = {ng: idx for idx, (ng, _) in enumerate(sorted_ngrams)}

        # Compute IDF: log((1 + n) / (1 + df)) + 1 (smooth IDF)
        self.idf = np.zeros(len(self.vocab))
        for ng, idx in self.vocab.items():
            self.idf[idx] = math.log((1 + n_docs) / (1 + df[ng])) + 1

        self._fitted = True
        return self

    def transform(self, texts: List[str]) -> np.ndarray:
        """
        Transform texts to TF-IDF vectors.

        Returns:
            np.ndarray of shape (n_texts, vocab_size)
        """
        if not self._fitted:
            raise RuntimeError("Encoder not fitted. Call fit() first.")

        n_features = len(self.vocab)
        matrix = np.zeros((len(texts), n_features), dtype=np.float32)

        for i, text in enumerate(texts):
            ngrams = self._extract_ngrams(text)
            if not ngrams:
                continue

            # Term frequency
            tf = Counter(ngrams)
            max_tf = max(tf.values())

            for ng, count in tf.items():
                if ng in self.vocab:
                    idx = self.vocab[ng]
                    # Sublinear TF: 1 + log(tf)
                    tf_val = 1 + math.log(count) if count > 0 else 0
                    # Normalized TF × IDF
                    matrix[i, idx] = (tf_val / (1 + math.log(max_tf))) * self.idf[idx]

            # L2 normalize
            norm = np.linalg.norm(matrix[i])
            if norm > 0:
                matrix[i] /= norm

        return matrix

    def fit_transform(self, texts: List[str], **kwargs) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(texts, **kwargs)
        return self.transform(texts)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text to a TF-IDF vector."""
        return self.transform([text])[0]

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)


class TextPreprocessor:
    """
    Preprocessing pipeline for reading reflections and excerpts.
    """

    # Common stop characters (punctuation, whitespace variants)
    STOP_CHARS = set('，。！？、；：""''（）【】《》—…·\n\r\t ')

    @staticmethod
    def clean(text: str) -> str:
        """Basic text cleaning."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    @staticmethod
    def truncate(text: str, max_len: int = 500) -> str:
        """Truncate text to max characters."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    @staticmethod
    def compute_depth_score(reflection_text: str, emotion_intensity: float = 0.5) -> float:
        """
        Compute reflection depth score.

        Depth = f(length, emotion_intensity, has_personal_pronoun, has_question)

        A "deep" reflection is:
        - Long enough to be substantive (>30 chars)
        - Shows emotional engagement
        - Contains personal connection ("我", "自己")
        - Contains questioning ("为什么", "？")
        """
        text = reflection_text

        # Length factor (logarithmic, caps at 200 chars)
        length_factor = min(1.0, math.log(1 + len(text)) / math.log(200))

        # Personal connection factor
        personal_markers = sum(1 for m in ["我", "自己", "让我", "我想", "我觉得"] if m in text)
        personal_factor = min(1.0, personal_markers / 2)

        # Questioning factor
        question_markers = sum(1 for m in ["为什么", "如何", "？", "吗", "呢", "难道"] if m in text)
        question_factor = min(1.0, question_markers / 2)

        # Combined depth score
        depth = (
            0.35 * length_factor +
            0.25 * emotion_intensity +
            0.20 * personal_factor +
            0.20 * question_factor
        )
        return round(depth, 4)
