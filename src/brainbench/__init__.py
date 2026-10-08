"""brain-bench: a standardized, openly licensed iEEG dataset and benchmark."""

from brainbench.schema import CANONICAL_SFREQ, SCHEMA_VERSION

__version__ = "0.0.1"
# Working name for the dataset/benchmark; goes into every release manifest.
DATASET_NAME = "brain-bench"
__all__ = ["CANONICAL_SFREQ", "DATASET_NAME", "SCHEMA_VERSION", "__version__"]
