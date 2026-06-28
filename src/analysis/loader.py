"""Dataset dataframe loader with a simple path-keyed cache.

`execute_local` needs the dataset's dataframe but must never put raw rows into
state that the LLM nodes can read. The dataframe is loaded here, cached by file
path, and handed only to the executor.
"""
from __future__ import annotations

import pandas as pd

from analysis.profile import load_dataframe
from db.models import Dataset
from db.session import create_db_session

# Cache by file path -> DataFrame. Datasets are read-only once uploaded, so a
# loaded frame can be reused across questions.
_CACHE: dict[str, pd.DataFrame] = {}


def get_dataset(dataset_id: str) -> Dataset | None:
    with create_db_session() as session:
        ds = session.get(Dataset, dataset_id)
        if ds is None:
            return None
        # detach a lightweight copy of the fields we need
        session.expunge(ds)
        return ds


def load_dataframe_for_dataset(dataset_id: str) -> pd.DataFrame:
    """Load (and cache) the dataframe for a dataset. Raises if dataset missing."""
    ds = get_dataset(dataset_id)
    if ds is None:
        raise ValueError(f"Dataset {dataset_id} not found")
    cached = _CACHE.get(ds.file_path)
    if cached is None:
        cached = load_dataframe(ds.file_path, kind=ds.kind)
        _CACHE[ds.file_path] = cached
    return cached


def clear_cache() -> None:
    _CACHE.clear()
