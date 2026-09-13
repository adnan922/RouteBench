"""Router classifier: predicts whether the cheap model will get a query right.

Trained on (features, label) pairs where label = whether the always-cheap
baseline (from src/eval/runners.py) answered correctly. A calibrated
probability output lets the cascade threshold on "how confident are we the
cheap tier succeeds" rather than trusting a raw, uncalibrated decision score.

PCA on just the embedding columns (not the hand-crafted ones) reduces the
384-dimensional embedding down to a smaller number of components before
training. This addresses a real problem found in Phase 1's first real run:
393 raw features (384 embedding + 9 hand-crafted) against as few as 56
training examples is a steep enough features-to-samples ratio to produce a
classifier that doesn't discriminate well between tasks, rather than
genuinely separating easy from hard queries.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class RouterLike(Protocol):
    """Structural type for anything with a .predict_confidence() matching
    RouterModel — lets tests substitute a fake router."""

    def predict_confidence(self, features: list[float]) -> float: ...


@dataclass
class RouterModel:
    """A trained, calibrated router. Wraps the fitted estimator — feature
    vectors passed to predict_confidence() must be built the same way
    (same order, same length) as the ones used for training."""

    calibrated_estimator: CalibratedClassifierCV

    def predict_confidence(self, features: list[float]) -> float:
        proba = self.calibrated_estimator.predict_proba([features])
        return float(proba[0][1])


def train_router(
    X: list[list[float]],
    y: list[bool],
    method: str = "sigmoid",
    cv: int = 3,
    n_handcrafted_features: int = 9,
    n_pca_components: int = 20,
) -> RouterModel:
    """Train a calibrated router classifier.

    Feature vectors are assumed to be [embedding..., handcrafted...] with
    `n_handcrafted_features` trailing columns being the hand-crafted ones
    (matches combined_features()'s concatenation order) — those columns
    pass through untouched; everything before that gets PCA'd down to
    `n_pca_components` (capped automatically if the training set is
    smaller than that, since PCA requires n_components <= n_samples).

    A StandardScaler follows PCA because the reduced embedding components
    and the raw hand-crafted features (e.g. char_length can run into the
    hundreds) are on wildly different scales, and plain logistic regression
    is scale-sensitive.

    `cv` is auto-capped to the smallest class's example count —
    CalibratedClassifierCV's stratified folds need at least `cv` examples
    of every class, and without this a too-small training set fails with an
    opaque sklearn internals traceback instead of a clear message.

    `n_pca_components` is capped based on the smallest *per-fold* training
    size, not the full dataset — CalibratedClassifierCV fits PCA separately
    within each cross-validation fold, so the sample count PCA actually sees
    is roughly len(X) * (effective_cv - 1) / effective_cv, smaller than
    len(X) itself. A small extra safety margin is subtracted since fold
    sizes aren't perfectly even.

    Passing n_handcrafted_features == the full width of X (i.e. all columns
    are hand-crafted, none are embedding) is a valid, supported case — the
    embedding branch is simply skipped. This is the exact path the
    hand-crafted-only ablation needs.
    """
    class_counts = Counter(y)
    min_class_count = min(class_counts.values()) if class_counts else 0
    if min_class_count < 2:
        raise ValueError(
            f"train_router needs at least 2 examples of every class to "
            f"calibrate; got class counts {dict(class_counts)}. Provide more "
            f"training data or a benchmark split with a less extreme class balance."
        )
    effective_cv = min(cv, min_class_count)

    n_features = len(X[0]) if X else 0
    n_embedding_features = max(0, n_features - n_handcrafted_features)
    embedding_cols = list(range(n_embedding_features))
    handcrafted_cols = list(range(n_embedding_features, n_features))

    min_fold_train_size = (len(X) * (effective_cv - 1)) // effective_cv
    effective_n_components = max(
        1, min(n_pca_components, min_fold_train_size - 1, n_embedding_features or 1)
    )

    transformers = []
    if embedding_cols:
        transformers.append(("embedding_pca", PCA(n_components=effective_n_components), embedding_cols))
    if handcrafted_cols:
        transformers.append(("handcrafted", "passthrough", handcrafted_cols))

    column_transformer = ColumnTransformer(transformers)
    pipeline = make_pipeline(column_transformer, StandardScaler(), LogisticRegression(max_iter=1000))
    calibrated = CalibratedClassifierCV(estimator=pipeline, method=method, cv=effective_cv)
    calibrated.fit(X, y)
    return RouterModel(calibrated_estimator=calibrated)


def save_router(router: RouterModel, path: str) -> None:
    joblib.dump(router.calibrated_estimator, path)


def load_router(path: str) -> RouterModel:
    return RouterModel(calibrated_estimator=joblib.load(path))