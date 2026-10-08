"""The baseline submission: mean log band-power + logistic regression.

Deliberately simple and channel-count agnostic (features are averaged over
channels). It exists so the leaderboard has a first row, not to be good.
See brainbench.submission for the contract it implements.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import welch

from brainbench.submission import TASKS, Window, run

BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 70), "high_gamma": (70, 134)}


def bandpower_features(x: np.ndarray, sfreq: float) -> np.ndarray:
    """Mean over channels of log band-power, plus log total power."""
    f, p = welch(x, fs=sfreq, nperseg=min(x.shape[1], int(sfreq)), axis=1)
    feats = [np.log(p[:, (f >= lo) & (f < hi)].mean(axis=1) + 1e-20).mean() for lo, hi in BANDS.values()]
    feats.append(np.log(p.mean() + 1e-20))
    return np.array(feats)


class BandpowerLogReg:
    def __init__(self):
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        self.pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))

    def fit(self, windows) -> None:
        X, y = [], []
        for x, _, sfreq, label in windows:
            X.append(bandpower_features(x, sfreq))
            y.append(label)
        classes = sorted(set(y))
        if len(classes) < 2:
            raise ValueError(f"training data has a single class: {classes}")
        self.pipeline.fit(np.array(X), np.array([classes.index(c) for c in y]))

    def predict_proba(self, x: np.ndarray, channels: pd.DataFrame, sfreq: float) -> float:
        return float(self.pipeline.predict_proba(bandpower_features(x, sfreq)[None])[0, 1])


def run_baseline(release: Path, task_name: str = "media_vs_rest", max_per_recording: int | None = 200) -> dict:
    return run(BandpowerLogReg(), release, task_name, max_per_recording=max_per_recording)


def main(argv: list[str] | None = None) -> None:
    import argparse

    p = argparse.ArgumentParser(prog="brainbench-baseline")
    p.add_argument("release", type=Path)
    p.add_argument("--task", default="media_vs_rest", choices=sorted(TASKS))
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    result = run_baseline(args.release, args.task)
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text)


if __name__ == "__main__":
    main()
