"""Unified event ontology.

Each source maps its native event labels onto these. Labels are hierarchical
strings ("sleep/N2") so tasks can select a whole branch ("sleep/*").
Native labels with no mapping become "unmapped" and keep their original_label.
"""

from __future__ import annotations

LABELS = frozenset(
    {
        # stimulus
        "stimulus/onset",
        "stimulus/offset",
        "stimulus/speech",  # perceived speech (e.g. a film's dialogue block)
        "stimulus/music",
        # seizure
        "seizure/onset",
        "seizure/offset",
        "seizure/preictal",  # lead-in before a marked onset, same clip
        "seizure/ictal",
        "seizure/postictal",
        "seizure/interictal",
        # sleep (AASM)
        "sleep/W",
        "sleep/N1",
        "sleep/N2",
        "sleep/N3",
        "sleep/REM",
        # task
        "task/rest",  # awake, at rest
        "task/watch_media",  # watching film / TV
        "task/sleep_or_rest",  # source does not separate sleep from rest
        "task/speech",  # speaking / conversation
        "task/listen",
        "task/motor",
        "task/memory_encode",
        "task/memory_recall",
        # data quality
        "artifact",
        "unmapped",
    }
)


def map_label(original: str, mapping: dict[str, str]) -> str:
    """Map a native label to the ontology using a source-provided mapping."""
    label = mapping.get(original, "unmapped")
    if label not in LABELS:
        raise ValueError(f"mapping produced {label!r}, which is not in the ontology")
    return label


def matches(label: str, pattern: str) -> bool:
    """True if label matches pattern; "sleep/*" matches every sleep stage."""
    if pattern.endswith("/*"):
        return label.startswith(pattern[:-1])
    return label == pattern
