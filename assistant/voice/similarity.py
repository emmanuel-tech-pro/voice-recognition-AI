"""Vector helpers for speaker embeddings (pure Python, no numpy required)."""

from __future__ import annotations

import math
from collections.abc import Sequence


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two equal-length vectors, in [-1, 1]."""
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} != {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def mean_vector(vectors: Sequence[Sequence[float]]) -> list[float]:
    """Average several embeddings into one profile embedding."""
    if not vectors:
        raise ValueError("no vectors to average")
    length = len(vectors[0])
    if any(len(v) != length for v in vectors):
        raise ValueError("all vectors must have the same length")
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(length)]
