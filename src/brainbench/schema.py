"""The brain-bench schema: the contract every recording is converted into.

A recording in the release is:

- signal:     float32 array [channels, samples] at CANONICAL_SFREQ
- channels:   one row per channel (CHANNEL_SCHEMA)
- subject:    one row per subject (SUBJECT_SCHEMA)
- events:     zero or more rows (EVENT_SCHEMA), labels from brainbench.ontology
- provenance: dict (PROVENANCE_KEYS) recording source, license and every step applied

Missing values are explicit nulls. Columns are never dropped, so every
recording has the same table shape regardless of source.
"""

from __future__ import annotations

import pyarrow as pa

SCHEMA_VERSION = "0.1.0"

# 500 Hz keeps content up to 250 Hz (covers high gamma) at half the storage of 1 kHz.
# The original rate is always kept in the recording's provenance.
CANONICAL_SFREQ = 500.0

CHANNEL_TYPES = ("seeg", "ecog", "depth", "strip", "grid", "ref", "misc")
REFERENCE_SCHEMES = ("original", "car", "bipolar")

# Upper band limit of every release signal. A recording whose acquisition
# hardware cut lower reports that in recordings.effective_lowpass.
LOWPASS = 200.0

CHANNEL_SCHEMA = pa.schema(
    [
        pa.field("recording_id", pa.string(), nullable=False),
        pa.field("index", pa.int32(), nullable=False),  # row in the signal array
        pa.field("name", pa.string(), nullable=False),  # normalized name
        pa.field("original_name", pa.string(), nullable=False),
        pa.field("type", pa.string(), nullable=True),  # one of CHANNEL_TYPES
        pa.field("x", pa.float32(), nullable=True),  # mm in coord_space; null if unknown
        pa.field("y", pa.float32(), nullable=True),
        pa.field("z", pa.float32(), nullable=True),
        pa.field("coord_space", pa.string(), nullable=True),  # "MNI" when normalized, else native (e.g. "ACPC")
        pa.field("anat_label", pa.string(), nullable=True),
        pa.field("reference", pa.string(), nullable=True),  # one of REFERENCE_SCHEMES
        pa.field("is_bad", pa.bool_(), nullable=False),  # flagged, never deleted
        pa.field("bad_reason", pa.string(), nullable=True),
        pa.field("hardware", pa.string(), nullable=True),  # vendor/system
    ]
)

SUBJECT_SCHEMA = pa.schema(
    [
        pa.field("subject_id", pa.string(), nullable=False),  # "<source>-<native id>"
        pa.field("source", pa.string(), nullable=False),
        pa.field("pathology", pa.string(), nullable=True),
        pa.field("coverage", pa.string(), nullable=True),  # "left", "right", "bilateral"
        pa.field("age", pa.float32(), nullable=True),
        pa.field("sex", pa.string(), nullable=True),
    ]
)

RECORDING_SCHEMA = pa.schema(
    [
        pa.field("recording_id", pa.string(), nullable=False),
        pa.field("subject_id", pa.string(), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("task", pa.string(), nullable=True),
        pa.field("session", pa.string(), nullable=True),
        pa.field("run", pa.string(), nullable=True),
        pa.field("n_channels", pa.int32(), nullable=False),
        pa.field("n_samples", pa.int64(), nullable=False),
        pa.field("sfreq", pa.float32(), nullable=False),
        pa.field("original_sfreq", pa.float32(), nullable=False),
        # Highest frequency with real signal (<= LOWPASS).
        pa.field("effective_lowpass", pa.float32(), nullable=False),
        pa.field("signal_path", pa.string(), nullable=False),  # relative to the release root
    ]
)

EVENT_SCHEMA = pa.schema(
    [
        pa.field("recording_id", pa.string(), nullable=False),
        pa.field("onset", pa.float64(), nullable=False),  # seconds from recording start
        pa.field("duration", pa.float64(), nullable=False),
        pa.field("label", pa.string(), nullable=False),  # brainbench.ontology label
        pa.field("original_label", pa.string(), nullable=False),
    ]
)

# Provenance shipped with every recording. Internal releases carry further
# keys (see pipeline.clean); distributed releases carry exactly these.
PROVENANCE_KEYS = (
    "recording_id",
    "source",
    "source_version",
    "license",
    "schema_version",
)


def empty_table(schema: pa.Schema) -> pa.Table:
    return schema.empty_table()
