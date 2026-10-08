"""Read a brain-bench release.

    bb = BrainBench("data/release")
    for rec in bb.recordings(split="train"):
        for x, t0 in windows(rec.signal, rec.sfreq, length_s=4.0):
            ...

The schema supports the three common ways of handling variable channel counts:
  - pad + mask:            pad_and_mask([rec.signal, ...])
  - per-channel tokens:    iterate rec.signal rows with rec.channels
  - coordinate embeddings: rec.channels[["x", "y", "z"]] (null where unknown)
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Recording:
    recording_id: str
    subject_id: str
    source: str
    sfreq: float
    signal: np.ndarray  # memory-mapped float32 [channels, samples]
    channels: pd.DataFrame
    events: pd.DataFrame
    provenance: dict


class BrainBench:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest = json.loads((self.root / "manifest.json").read_text())
        self.splits = json.loads((self.root / "splits.json").read_text())

    @cached_property
    def recordings_table(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "recordings.parquet")

    @cached_property
    def channels_table(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "channels.parquet")

    @cached_property
    def events_table(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "events.parquet")

    @cached_property
    def subjects_table(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "subjects.parquet")

    @cached_property
    def _provenance(self) -> dict[str, dict]:
        with open(self.root / "provenance.jsonl") as f:
            return {p["recording_id"]: p for p in map(json.loads, f)}

    def subjects_in(self, split: str) -> list[str]:
        return self.splits["subjects"][split]

    def recording_ids(self, split: str | None = None) -> list[str]:
        df = self.recordings_table
        if split is not None:
            df = df[df["subject_id"].isin(self.subjects_in(split))]
        return df["recording_id"].tolist()

    def load(self, recording_id: str) -> Recording:
        row = self.recordings_table.set_index("recording_id").loc[recording_id]
        ch = self.channels_table
        ev = self.events_table
        return Recording(
            recording_id=recording_id,
            subject_id=row["subject_id"],
            source=row["source"],
            sfreq=float(row["sfreq"]),
            signal=np.load(self.root / row["signal_path"], mmap_mode="r"),
            channels=ch[ch["recording_id"] == recording_id].sort_values("index").reset_index(drop=True),
            events=ev[ev["recording_id"] == recording_id].reset_index(drop=True),
            provenance=self._provenance[recording_id],
        )

    def recordings(self, split: str | None = None) -> Iterator[Recording]:
        for rid in self.recording_ids(split):
            yield self.load(rid)


def windows(signal: np.ndarray, sfreq: float, length_s: float, step_s: float | None = None) -> Iterator[tuple[np.ndarray, float]]:
    """Yield (window [channels, samples], start time in seconds). Drops the incomplete tail."""
    n = int(round(length_s * sfreq))
    step = int(round((step_s or length_s) * sfreq))
    for start in range(0, signal.shape[1] - n + 1, step):
        yield signal[:, start : start + n], start / sfreq


def pad_and_mask(signals: list[np.ndarray], n_channels: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Stack [c_i, t] arrays into [batch, C, t] with a [batch, C] boolean mask of real channels."""
    t = {s.shape[1] for s in signals}
    if len(t) != 1:
        raise ValueError(f"all signals must have the same length, got {sorted(t)}")
    c = n_channels or max(s.shape[0] for s in signals)
    out = np.zeros((len(signals), c, t.pop()), dtype=np.float32)
    mask = np.zeros((len(signals), c), dtype=bool)
    for i, s in enumerate(signals):
        k = min(c, s.shape[0])
        out[i, :k] = s[:k]
        mask[i, :k] = True
    return out, mask
