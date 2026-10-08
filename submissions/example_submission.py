"""A complete, minimal submission. Copy this file and replace the model.

brain-bench runs:   brainbench-evaluate run example_submission.py --train <train> --test <test>

`build()` must return an object with
    fit(windows)                       windows: iterable of (x, channels, sfreq, label)
    predict_proba(x, channels, sfreq)  -> float, probability of the positive class

x is float32 [channels, samples] (good channels only); channel counts vary.
"""

import numpy as np


class MeanPowerModel:
    """Classifies by total log power with a single learned threshold."""

    def fit(self, windows):
        feats, labels = [], []
        for x, channels, sfreq, label in windows:
            feats.append(np.log(np.mean(x.astype(np.float64) ** 2) + 1e-20))
            labels.append(label)
        classes = sorted(set(labels))
        feats, labels = np.array(feats), np.array(labels)
        self.positive = classes[1]
        self.mu = {c: feats[labels == c].mean() for c in classes}
        self.scale = feats.std() + 1e-9

    def predict_proba(self, x, channels, sfreq):
        f = np.log(np.mean(x.astype(np.float64) ** 2) + 1e-20)
        other = next(c for c in self.mu if c != self.positive)
        z = (abs(f - self.mu[other]) - abs(f - self.mu[self.positive])) / self.scale
        return float(1 / (1 + np.exp(-z)))


def build():
    return MeanPowerModel()
