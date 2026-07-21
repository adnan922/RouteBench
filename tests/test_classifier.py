"""Tests for src/router/classifier.py.

Entirely network-free: pure scikit-learn on synthetic feature vectors, so
these run the same everywhere — this sandbox, CI, or the home server.
"""

import random

from src.router.classifier import RouterModel, load_router, save_router, train_router


def _make_synthetic_dataset(n: int = 40, seed: int = 0) -> tuple[list[list[float]], list[bool]]:
    """A synthetic, roughly linearly-separable dataset: feature[0] above
    ~0.5 (plus a little noise) means the label is True most of the time.
    Two irrelevant features are included alongside it, same as a real
    classifier would see plenty of uninformative dimensions."""
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        f0 = rng.uniform(0, 1)
        noise = rng.gauss(0, 0.05)
        X.append([f0, rng.uniform(0, 1), rng.uniform(0, 1)])
        y.append((f0 + noise) > 0.5)
    return X, y


class TestTrainRouter:
    def test_fits_without_error(self):
        X, y = _make_synthetic_dataset()
        router = train_router(X, y)
        assert isinstance(router, RouterModel)

    def test_predict_confidence_returns_valid_probability(self):
        X, y = _make_synthetic_dataset()
        router = train_router(X, y)
        confidence = router.predict_confidence([0.5, 0.5, 0.5])
        assert 0.0 <= confidence <= 1.0

    def test_high_signal_feature_yields_higher_confidence_than_low(self):
        X, y = _make_synthetic_dataset(n=60, seed=1)
        router = train_router(X, y)
        high_confidence = router.predict_confidence([0.95, 0.5, 0.5])
        low_confidence = router.predict_confidence([0.05, 0.5, 0.5])
        assert high_confidence > low_confidence

    def test_isotonic_method_also_works(self):
        X, y = _make_synthetic_dataset(n=80, seed=2)
        router = train_router(X, y, method="isotonic")
        confidence = router.predict_confidence([0.5, 0.5, 0.5])
        assert 0.0 <= confidence <= 1.0


class TestSaveLoadRouter:
    def test_round_trip_predicts_the_same_value(self, tmp_path):
        X, y = _make_synthetic_dataset(n=60, seed=3)
        router = train_router(X, y)
        query_features = [0.7, 0.3, 0.6]
        original_confidence = router.predict_confidence(query_features)

        save_path = tmp_path / "router.joblib"
        save_router(router, str(save_path))
        loaded_router = load_router(str(save_path))

        assert loaded_router.predict_confidence(query_features) == original_confidence