"""Tests for src/router/classifier.py.

Entirely network-free: pure scikit-learn on synthetic feature vectors, so
these run the same everywhere — this sandbox, CI, or the home server.
"""

import random
from unittest.mock import patch

from sklearn.decomposition import PCA

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


class TestZeroEmbeddingColumns:
    """The all-handcrafted-features case: n_handcrafted_features equal to
    the full width of X, so n_embedding_features computes to 0.

    This is the exact path the hand-crafted-only ablation (src/eval/ablation.py)
    depends on, and it was never actually exercised by a test before this —
    the existing tests above cover the normal case (embedding + hand-crafted
    mixed together) with the *default* n_handcrafted_features=9, but never
    called train_router() with n_handcrafted_features equal to len(X[0]).
    Flagged by the PM as the same category of bug that bit this project
    twice already (the cv auto-cap, the PCA per-fold sizing) — looks correct
    by reading the code, unverified at the actual boundary.
    """

    def test_trains_without_error_when_all_columns_are_handcrafted(self):
        X, y = _make_synthetic_dataset(n=40, seed=5)
        router = train_router(X, y, n_handcrafted_features=3)  # 3 == len(X[0])
        assert isinstance(router, RouterModel)

    def test_predict_confidence_is_still_a_valid_probability(self):
        X, y = _make_synthetic_dataset(n=40, seed=6)
        router = train_router(X, y, n_handcrafted_features=3)
        confidence = router.predict_confidence([0.5, 0.5, 0.5])
        assert 0.0 <= confidence <= 1.0

    def test_still_discriminates_on_the_signal_feature(self):
        """Same style check as the combined-feature test above — confirms
        the handcrafted-only path isn't just running without error, it's
        genuinely learning from the data, not silently degrading to a
        constant prediction."""
        X, y = _make_synthetic_dataset(n=60, seed=7)
        router = train_router(X, y, n_handcrafted_features=3)
        high_confidence = router.predict_confidence([0.95, 0.5, 0.5])
        low_confidence = router.predict_confidence([0.05, 0.5, 0.5])
        assert high_confidence > low_confidence

    def test_pca_is_never_instantiated_when_there_are_no_embedding_columns(self):
        """The behavioral confirmation the PM actually asked for: not just
        'training succeeds' (it could succeed while still quietly trying to
        PCA a 0-column slice, or PCA'ing the wrong columns), but that the
        PCA branch is provably never entered. Patches PCA at the point
        classifier.py imports it, so this is version-independent — it
        doesn't rely on introspecting CalibratedClassifierCV's internal
        attribute names, which have changed across sklearn versions before.
        """
        X, y = _make_synthetic_dataset(n=40, seed=8)
        with patch("src.router.classifier.PCA") as mock_pca:
            train_router(X, y, n_handcrafted_features=3)
        mock_pca.assert_not_called()

    def test_pca_is_instantiated_in_the_normal_mixed_feature_case(self):
        """Contrast check: confirms the mock-based test above is actually
        discriminating between 'PCA ran' and 'PCA didn't run', rather than
        PCA never being called under any circumstances (which would make
        the previous test pass for the wrong reason).

        Uses wraps=PCA rather than a bare MagicMock — a bare mock's
        fit_transform() returns a Mock object, not a real 2D array, which
        ColumnTransformer's own output validation correctly rejects once it
        actually runs inside a real pipeline. wraps= keeps the call
        countable while still executing the real PCA underneath.
        """
        X, y = _make_synthetic_dataset(n=40, seed=9)
        with patch("src.router.classifier.PCA", wraps=PCA) as mock_pca:
            train_router(X, y, n_handcrafted_features=1)  # 1 < 3 == embedding cols exist
        mock_pca.assert_called()