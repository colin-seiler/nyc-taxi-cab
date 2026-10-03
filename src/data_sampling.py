from pathlib import Path
import polars as pl

RAW_FILE = Path("data/raw/yellow_tripdata_2025-01.parquet")
SAMPLE_FILE = Path("data/samples/yellow_tripdata_sample.parquet")


def create_sample(n=1000, seed=42):
    SAMPLE_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = pl.read_parquet(RAW_FILE)

    sample = df.sample(
        n=min(n, df.height),
        seed=seed
    )

    sample.write_parquet(SAMPLE_FILE)

    print(f"Sample saved to: {SAMPLE_FILE}")
    print(f"Rows: {sample.height}")


if __name__ == "__main__":
    create_sample()