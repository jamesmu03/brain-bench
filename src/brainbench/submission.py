"""The submission contract: what a model must implement to be scored.

A submission is a Python object with two methods:

    fit(windows)                      windows: iterable of (x, channels, sfreq, label)
    predict_proba(x, channels, sfreq) -> probability of the task's positive class

where
    x         float32 array [channels, samples], good channels only
    channels  DataFrame with one row per row of x (see brainbench.schema.CHANNEL_SCHEMA):
              name, type, x/y/z (mm, null if unknown), coord_space, hardware, ...
    sfreq     sampling rate in Hz
    label     class name (one of Task.classes)

Channel counts differ between recordings and between training and test
sources; the model must handle that. Evaluation is run by brain-bench on
held-out data the submitter never sees, and reports per-window balanced
accuracy and AUROC on the in-source test split and on the cross-device split.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from brainbench import ontology
from brainbench.loader import BrainBench, Recording, windows

Window = tuple[np.ndarray, pd.DataFrame, float, str]


@runtime_checkable
class Model(Protocol):
    def fit(self, windows: Iterable[Window]) -> None: ...

    def predict_proba(self, x: np.ndarray, channels: pd.DataFrame, sfreq: float) -> float: ...


class Task:
    """A supervised task: two classes defined as ontology patterns, and a window size."""

    def __init__(self, name: str, classes: dict[str, tuple[str, ...]], window_s: float = 4.0, step_s: float = 4.0):
        if len(classes) != 2:
            raise ValueError("tasks are binary for now")
        self.name = name
        self.classes = classes
        self.class_names = sorted(classes)  # class_names[1] is the positive class
        self.window_s = window_s
        self.step_s = step_s

    def label_of(self, rec: Recording, t0: float) -> str | None:
        """Class of the window [t0, t0 + window_s), or None if it is not fully inside exactly one class."""
        t1 = t0 + self.window_s
        hit = None
        for ev in rec.events.itertuples():
            if ev.onset <= t0 and t1 <= ev.onset + ev.duration:
                for cls, patterns in self.classes.items():
                    if any(ontology.matches(ev.label, p) for p in patterns):
                        if hit is not None and hit != cls:
                            return None
                        hit = cls
        return hit


TASKS = {
    "media_vs_rest": Task(
        "media_vs_rest",
        classes={"media": ("task/watch_media",), "rest": ("task/rest", "task/sleep_or_rest")},
    ),
    # Awake rest only: sleep has strong slow-wave power that is not "rest" in the sense of media_vs_rest.
    "media_vs_awake_rest": Task(
        "media_vs_awake_rest",
        classes={"media": ("task/watch_media",), "rest": ("task/rest",)},
    ),
    "ictal_vs_interictal": Task(
        "ictal_vs_interictal",
        classes={"ictal": ("seizure/ictal",), "interictal": ("seizure/interictal",)},
    ),
}


def iter_windows(bb: BrainBench, task: Task, split: str, max_per_recording: int | None = None) -> Iterator[tuple[Window, Recording]]:
    """Yield ((x, channels, sfreq, label), recording) for every labeled window in a split."""
    for rec in bb.recordings(split):
        good = ~rec.channels["is_bad"].to_numpy()
        channels = rec.channels[good].reset_index(drop=True)
        n = 0
        for x, t0 in windows(rec.signal, rec.sfreq, task.window_s, task.step_s):
            cls = task.label_of(rec, t0)
            if cls is None:
                continue
            yield (np.asarray(x)[good], channels, rec.sfreq, cls), rec
            n += 1
            if max_per_recording and n >= max_per_recording:
                break


def evaluate(model: Model, bb: BrainBench, task: Task, split: str, max_per_recording: int | None = None) -> dict:
    from sklearn.metrics import balanced_accuracy_score, roc_auc_score

    y, prob, subjects = [], [], set()
    for (x, channels, sfreq, cls), rec in iter_windows(bb, task, split, max_per_recording):
        y.append(task.class_names.index(cls))
        prob.append(float(model.predict_proba(x, channels, sfreq)))
        subjects.add(rec.subject_id)
    if len(set(y)) < 2:
        return {"n_windows": len(y), "skipped": "fewer than two classes in this split"}
    y, prob = np.array(y), np.array(prob)
    return {
        "n_windows": int(len(y)),
        "n_subjects": len(subjects),
        "balanced_accuracy": float(balanced_accuracy_score(y, prob > 0.5)),
        "auroc": float(roc_auc_score(y, prob)),
    }


def run(model: Model, release, task_name: str, train_splits=("train", "val"), test_splits=("test", "test_xdevice"), max_per_recording: int | None = None) -> dict:
    """Fit on train_splits, score on test_splits. Returns a result record for the leaderboard."""
    from brainbench.provenance import pipeline_commit

    bb = BrainBench(release)
    task = TASKS[task_name]

    def training():
        for split in train_splits:
            for window, _ in iter_windows(bb, task, split, max_per_recording):
                yield window

    model.fit(training())
    return {
        "task": task_name,
        "model": type(model).__name__,
        "dataset": bb.manifest.get("name"),
        "release": bb.manifest["version"],
        "schema_version": bb.manifest["schema_version"],
        "holdout_source": bb.splits["holdout_source"],
        "pipeline_commit": pipeline_commit(),
        "results": {split: evaluate(model, bb, task, split, max_per_recording) for split in test_splits},
    }
