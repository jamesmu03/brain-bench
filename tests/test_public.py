"""Tests that run without any data: the contract, the label logic, the helpers."""

import numpy as np
import pandas as pd

from brainbench import ontology
from brainbench.benchmark import BandpowerLogReg, bandpower_features
from brainbench.loader import Recording, pad_and_mask, windows
from brainbench.submission import TASKS, Model


def _rec(events):
    return Recording(
        recording_id="r", subject_id="s", source="x", sfreq=500.0, signal=np.zeros((2, 5000), dtype=np.float32),
        channels=pd.DataFrame({"is_bad": [False, False]}), events=pd.DataFrame(events), provenance={},
    )


def test_ontology_matches_branches():
    assert ontology.matches("sleep/REM", "sleep/*")
    assert not ontology.matches("seizure/onset", "sleep/*")


def test_window_label_requires_full_containment():
    task = TASKS["media_vs_rest"]
    rec = _rec([{"onset": 0.0, "duration": 10.0, "label": "task/watch_media"}, {"onset": 10.0, "duration": 10.0, "label": "task/rest"}])
    assert task.label_of(rec, 0.0) == "media"
    assert task.label_of(rec, 8.0) is None
    assert task.label_of(rec, 12.0) == "rest"


def test_windows_and_padding():
    sig = np.arange(2 * 1000, dtype=np.float32).reshape(2, 1000)
    assert len(list(windows(sig, 100.0, 2.0, 1.0))) == 9
    x, mask = pad_and_mask([np.ones((3, 10)), np.ones((5, 10))])
    assert x.shape == (2, 5, 10) and mask.sum(axis=1).tolist() == [3, 5]


def test_baseline_is_a_valid_submission():
    model = BandpowerLogReg()
    assert isinstance(model, Model)
    rng = np.random.default_rng(0)
    ch = pd.DataFrame({"name": ["a", "b"]})
    train = [(rng.standard_normal((2, 2000)).astype(np.float32) * (1 + i % 2), ch, 500.0, ["media", "rest"][i % 2]) for i in range(20)]
    model.fit(train)
    p = model.predict_proba(train[0][0], ch, 500.0)
    assert 0.0 <= p <= 1.0
    assert bandpower_features(train[0][0], 500.0).shape == (7,)
