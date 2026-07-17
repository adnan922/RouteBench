"""Tests for src/router/features.py.

Hand-crafted feature tests are pure logic — no network, always run. The
QueryEmbedder tests need to download a model from Hugging Face Hub on first
use, so they're marked `network` and skip gracefully if unreachable — same
pattern as tests/test_dataset.py's load_benchmark() test.
"""

import pytest

from src.router.features import (
    HAND_CRAFTED_FEATURE_NAMES,
    QueryEmbedder,
    combined_features,
    combined_features_batch,
    hand_crafted_features,
    hand_crafted_vector,
)


class TestHandCraftedFeatures:
    def test_basic_counts(self):
        f = hand_crafted_features("What is 2 + 2?")
        assert f["char_length"] == len("What is 2 + 2?")
        assert f["word_count"] == 5  # "What", "is", "2", "+", "2?" — "+" is its own whitespace-separated token
        assert f["question_mark_count"] == 1

    def test_number_count(self):
        f = hand_crafted_features("If John has 5 apples and buys 3 more, how many total?")
        assert f["number_count"] == 2

    def test_math_operator_count(self):
        f = hand_crafted_features("2 + 2 - 1 = 3")
        assert f["math_operator_count"] == 3  # +, -, =

    def test_multiple_choice_marker_detected(self):
        query = "Pick one:\nA. wrong\nB. right\nC. also wrong\nD. nope"
        f = hand_crafted_features(query)
        assert f["has_multiple_choice_markers"] == 1.0

    def test_no_multiple_choice_marker(self):
        f = hand_crafted_features("What is the capital of France?")
        assert f["has_multiple_choice_markers"] == 0.0

    def test_empty_string_does_not_crash(self):
        f = hand_crafted_features("")
        assert f["word_count"] == 0
        assert f["avg_word_length"] == 0.0
        assert f["uppercase_ratio"] == 0.0

    def test_uppercase_ratio(self):
        f = hand_crafted_features("ABC")
        assert f["uppercase_ratio"] == 1.0


class TestHandCraftedVector:
    def test_vector_matches_feature_order(self):
        query = "What is 2 + 2?"
        vector = hand_crafted_vector(query)
        features = hand_crafted_features(query)
        assert vector == [features[name] for name in HAND_CRAFTED_FEATURE_NAMES]

    def test_vector_length_matches_feature_names(self):
        assert len(hand_crafted_vector("test")) == len(HAND_CRAFTED_FEATURE_NAMES)


@pytest.mark.network
class TestQueryEmbedder:
    def test_embed_one_returns_expected_dimension(self):
        embedder = QueryEmbedder()
        try:
            vector = embedder.embed_one("What is 2 + 2?")
        except Exception as exc:
            pytest.skip(f"Could not load embedding model: {exc}")
        assert len(vector) == 384
        assert embedder.dimensions == 384

    def test_embed_is_deterministic(self):
        embedder = QueryEmbedder()
        try:
            v1 = embedder.embed_one("hello world")
            v2 = embedder.embed_one("hello world")
        except Exception as exc:
            pytest.skip(f"Could not load embedding model: {exc}")
        assert v1 == pytest.approx(v2)

    def test_embed_batch_matches_embed_one(self):
        embedder = QueryEmbedder()
        try:
            batch = embedder.embed(["first query", "second query"])
            single = embedder.embed_one("first query")
        except Exception as exc:
            pytest.skip(f"Could not load embedding model: {exc}")
        assert batch[0] == pytest.approx(single)


@pytest.mark.network
def test_combined_features_length():
    embedder = QueryEmbedder()
    try:
        vector = combined_features("What is 2 + 2?", embedder)
    except Exception as exc:
        pytest.skip(f"Could not load embedding model: {exc}")
    assert len(vector) == 384 + len(HAND_CRAFTED_FEATURE_NAMES)


@pytest.mark.network
def test_combined_features_batch_matches_single_calls():
    embedder = QueryEmbedder()
    queries = ["What is 2 + 2?", "Pick one:\nA. wrong\nB. right"]
    try:
        batch_result = combined_features_batch(queries, embedder)
        individual_results = [combined_features(q, embedder) for q in queries]
    except Exception as exc:
        pytest.skip(f"Could not load embedding model: {exc}")
    for batch_row, individual_row in zip(batch_result, individual_results):
        assert batch_row == pytest.approx(individual_row)