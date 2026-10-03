from pathlib import Path
import polars as pl

RAW_FILE = Path("data/raw/yellow_tripdata_2025-01.parquet")


def load_raw_data() -> pl.LazyFrame:
    return pl.scan_parquet(RAW_FILE)