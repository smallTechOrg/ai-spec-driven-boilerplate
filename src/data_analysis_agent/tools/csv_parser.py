from pathlib import Path

import pandas as pd


def parse_csv(file_path: str) -> tuple[list[str], int, str]:
    """Read a CSV file. Returns (column_names, row_count, data_sample)."""
    df = pd.read_csv(file_path)
    column_names = list(df.columns)
    row_count = len(df)
    sample = df.head(5).to_csv(index=False)
    return column_names, row_count, sample
