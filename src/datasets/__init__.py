"""Local dataset storage + profiling — the local side of the privacy boundary.

Raw CSVs live on local disk under ``data/datasets/{id}.csv`` and never leave the
machine. Only derived metadata/schema is persisted to SQLite, and only a small
derived profile (computed by :mod:`datasets.profiler`) is ever allowed near the
LLM prompt.
"""

from datasets.store import (
    save_dataset,
    dataset_path,
    get_dataset,
    DatasetError,
)
from datasets.profiler import build_profile

__all__ = [
    "save_dataset",
    "dataset_path",
    "get_dataset",
    "DatasetError",
    "build_profile",
]
