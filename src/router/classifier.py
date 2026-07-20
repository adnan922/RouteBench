"""Router classifier: predicts whether the cheap model will get a query right.

Trained on (features, label) pairs where label = whether the always-cheap
baseline (from src/eval/runners.py) answered correctly. A calibrated
probability output lets the cascade (built next) threshold on "how confident
are we the cheap tier succeeds" rather than trusting a raw, uncalibrated
decision score — raw logistic-regression scores are notoriously unreliable
as actual probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import joblib
from sklearn.calibration import CalibratedClassifierCV
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
        """Return the calibrated probability that the cheap tier succeeds on
        this query. Higher = more confident the cheap tier is enough."""
        proba = self.calibrated_estimator.predict_proba([features])
        return float(proba[0][1])  # P(class=1, i.e. "cheap tier succeeds")


def train_router(
    X: list[list[float]],
    y: list[bool],
    method: str = "sigmoid",
    cv: int = 3,
) -> RouterModel:
    """Train a calibrated router classifier.

    A StandardScaler is included because our real feature vectors mix wildly
    different scales — raw embedding dimensions (roughly [-1, 1]) alongside
    hand-crafted features like char_length (can run into the hundreds) —
    and plain logistic regression is scale-sensitive.

    `method="sigmoid"` (Platt scaling) is the default rather than "isotonic"
    deliberately: isotonic regression needs a lot of calibration samples to
    avoid overfitting (scikit-learn's own docs warn against it under ~1000
    samples), and Phase 1's benchmark is on the order of dozens to a couple
    hundred examples, not thousands.
    """
    pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    calibrated = CalibratedClassifierCV(estimator=pipeline, method=method, cv=cv)
    calibrated.fit(X, y)
    return RouterModel(calibrated_estimator=calibrated)


def save_router(router: RouterModel, path: str) -> None:
    joblib.dump(router.calibrated_estimator, path)


def load_router(path: str) -> RouterModel:
    return RouterModel(calibrated_estimator=joblib.load(path))