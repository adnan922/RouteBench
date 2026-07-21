"""Feature extraction for the Phase 1 router classifier.

Two kinds of features, deliberately kept separate:

- Hand-crafted (`hand_crafted_features` / `hand_crafted_vector`): cheap,
  interpretable, pure-Python signals — no model inference. The router has to
  decide which tier to use *before* paying for any real inference, so this
  part has to stay fast and free, and fully testable without a network call.
- Embeddings (`QueryEmbedder`): a dense semantic representation via fastembed
  (ONNX-based, no PyTorch — light enough for the home server's 4GB RAM /
  no-AVX2 CPU). Default model is BAAI/bge-small-en-v1.5, 384-dim, downloaded
  from Hugging Face Hub on first use and cached locally after that.

`combined_features()` / `combined_features_batch()` concatenate both into the
actual classifier input.
"""

from __future__ import annotations

import re
from typing import Protocol

HAND_CRAFTED_FEATURE_NAMES = [
    "char_length",
    "word_count",
    "avg_word_length",
    "digit_count",
    "number_count",
    "math_operator_count",
    "has_multiple_choice_markers",
    "question_mark_count",
    "uppercase_ratio",
]

_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")
_MATH_OPERATOR_RE = re.compile(r"[+\-*/=%^]")
_MC_MARKER_RE = re.compile(r"(?m)^[A-D][.)]\s")


def hand_crafted_features(query: str) -> dict[str, float]:
    """Simple, interpretable signals that correlate with query difficulty/type.

    Note `has_multiple_choice_markers` in particular is a strong proxy for
    "this is MMLU, not GSM8K" in our specific benchmark — worth being honest
    about in the write-up, since it makes the classification task somewhat
    easier than it would be on genuinely blended real-world queries where
    format doesn't line up so neatly with difficulty.
    """
    words = query.split()
    word_count = len(words)
    char_length = len(query)

    return {
        "char_length": float(char_length),
        "word_count": float(word_count),
        "avg_word_length": float(char_length / word_count) if word_count else 0.0,
        "digit_count": float(sum(c.isdigit() for c in query)),
        "number_count": float(len(_NUMBER_RE.findall(query))),
        "math_operator_count": float(len(_MATH_OPERATOR_RE.findall(query))),
        "has_multiple_choice_markers": 1.0 if _MC_MARKER_RE.search(query) else 0.0,
        "question_mark_count": float(query.count("?")),
        "uppercase_ratio": float(sum(c.isupper() for c in query) / char_length) if char_length else 0.0,
    }


def hand_crafted_vector(query: str) -> list[float]:
    """hand_crafted_features(), as a fixed-order vector for a classifier."""
    features = hand_crafted_features(query)
    return [features[name] for name in HAND_CRAFTED_FEATURE_NAMES]


class EmbedderLike(Protocol):
    """Structural type for anything with .embed()/.embed_one() matching
    QueryEmbedder — lets tests substitute a fake embedder."""

    def embed_one(self, text: str) -> list[float]: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class QueryEmbedder:
    """Thin, lazily-initialized wrapper around fastembed's TextEmbedding.

    Lazy on purpose: importing this module, and even constructing this class,
    should never trigger a model download by itself (blocked in
    network-restricted environments) — only actually calling .embed()/
    .embed_one() does. The model downloads once and fastembed caches it
    locally after that.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._model = None
        self._dim: int | None = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)

    @property
    def dimensions(self) -> int:
        """Discovered from the model itself on first use, rather than
        hardcoded — stays correct even if model_name is swapped out."""
        if self._dim is None:
            self._dim = len(self.embed_one("probe"))
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Batched embedding — fastembed batches internally, meaningfully
        faster than calling embed_one() in a loop for more than a handful of
        texts."""
        self._ensure_loaded()
        return [vector.tolist() for vector in self._model.embed(texts)]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def combined_features(query: str, embedder: EmbedderLike) -> list[float]:
    """Concatenate a query's embedding with its hand-crafted features into
    one flat vector — this is what actually feeds the router classifier."""
    return embedder.embed_one(query) + hand_crafted_vector(query)


def combined_features_batch(queries: list[str], embedder: EmbedderLike) -> list[list[float]]:
    """Batched version of combined_features() — uses fastembed's internal
    batching instead of embedding one query at a time."""
    embeddings = embedder.embed(queries)
    return [
        embedding + hand_crafted_vector(query) for embedding, query in zip(embeddings, queries)
    ]