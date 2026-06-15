"""
Dataset builder for FL training.

Converts raw reflections into PyTorch datasets for each campus.
"""

import numpy as np
from typing import List, Tuple, Optional
from collections import Counter

from .reflection import Reflection, EMOTION_LABELS


class TextTokenizer:
    """
    Simple character-level + word-level hybrid tokenizer.
    No external dependencies required.
    """

    def __init__(self, vocab_size: int = 10000, max_length: int = 256):
        self.vocab_size = vocab_size
        self.max_length = max_length
        self.char_to_idx = {"<PAD>": 0, "<UNK>": 1, "<CLS>": 2, "<SEP>": 3}
        self.idx_to_char = {v: k for k, v in self.char_to_idx.items()}
        self._built = False

    def fit(self, texts: List[str]):
        """Build vocabulary from texts"""
        char_counts = Counter()
        for text in texts:
            char_counts.update(text)

        # Top vocab_size characters
        most_common = char_counts.most_common(self.vocab_size - len(self.char_to_idx))
        for char, _ in most_common:
            if char not in self.char_to_idx:
                idx = len(self.char_to_idx)
                self.char_to_idx[char] = idx
                self.idx_to_char[idx] = char

        self._built = True

    def encode(self, text: str) -> np.ndarray:
        """Encode text to fixed-length integer sequence"""
        tokens = [self.char_to_idx.get("<CLS>")]
        for char in text[:self.max_length - 2]:
            tokens.append(self.char_to_idx.get(char, self.char_to_idx.get("<UNK>")))
        tokens.append(self.char_to_idx.get("<SEP>"))

        # Pad or truncate
        if len(tokens) < self.max_length:
            tokens += [self.char_to_idx.get("<PAD>")] * (self.max_length - len(tokens))
        else:
            tokens = tokens[:self.max_length]

        return np.array(tokens, dtype=np.int64)

    def decode(self, indices: np.ndarray) -> str:
        """Decode indices back to text"""
        chars = []
        for idx in indices:
            char = self.idx_to_char.get(int(idx), "")
            if char in ("<PAD>", "<CLS>", "<SEP>"):
                continue
            chars.append(char)
        return "".join(chars)

    @property
    def actual_vocab_size(self) -> int:
        return len(self.char_to_idx)


class ReflectionDataset:
    """
    Dataset for FL training.

    Each sample: (excerpt_tokens, reflection_tokens, emotion_label, quality_score)
    """

    def __init__(self, reflections: List[Reflection], tokenizer: TextTokenizer):
        self.reflections = reflections
        self.tokenizer = tokenizer

        # Encode all texts
        self.excerpt_tokens = []
        self.reflection_tokens = []
        self.emotion_labels = []
        self.quality_scores = []

        for r in reflections:
            # Combine excerpt + reflection as input
            combined = f"{r.excerpt.text} {r.reflection_text}"
            tokens = tokenizer.encode(combined)
            self.excerpt_tokens.append(tokens)

            # Reflection only for quality head
            ref_tokens = tokenizer.encode(r.reflection_text)
            self.reflection_tokens.append(ref_tokens)

            # Emotion label
            label_idx = EMOTION_LABELS.index(r.emotion_label) if r.emotion_label in EMOTION_LABELS else 0
            self.emotion_labels.append(label_idx)

            # Quality score from reflection depth
            self.quality_scores.append(r.reflection_depth)

        self.excerpt_tokens = np.array(self.excerpt_tokens)
        self.reflection_tokens = np.array(self.reflection_tokens)
        self.emotion_labels = np.array(self.emotion_labels, dtype=np.int64)
        self.quality_scores = np.array(self.quality_scores, dtype=np.float32)

    def __len__(self) -> int:
        return len(self.reflections)

    def get_batch(self, indices: List[int]) -> dict:
        """Get a batch of data"""
        return {
            "input_ids": self.excerpt_tokens[indices],
            "reflection_ids": self.reflection_tokens[indices],
            "emotion_labels": self.emotion_labels[indices],
            "quality_scores": self.quality_scores[indices],
        }

    def get_random_batch(self, batch_size: int) -> dict:
        """Get a random batch"""
        indices = np.random.choice(len(self), size=min(batch_size, len(self)), replace=False)
        return self.get_batch(indices.tolist())


def build_campus_datasets(
    campus_data: dict,
    tokenizer: Optional[TextTokenizer] = None,
    max_length: int = 256,
) -> Tuple[dict, TextTokenizer]:
    """
    Build datasets for all campuses.

    Returns:
        (campus_datasets, tokenizer)
    """
    if tokenizer is None:
        # Collect all texts for tokenizer fitting
        all_texts = []
        for cid, data in campus_data.items():
            for r in data["reflections"]:
                all_texts.append(f"{r.excerpt.text} {r.reflection_text}")
                all_texts.append(r.reflection_text)

        tokenizer = TextTokenizer(max_length=max_length)
        tokenizer.fit(all_texts)

    campus_datasets = {}
    for cid, data in campus_data.items():
        dataset = ReflectionDataset(data["reflections"], tokenizer)
        campus_datasets[cid] = dataset

    return campus_datasets, tokenizer
