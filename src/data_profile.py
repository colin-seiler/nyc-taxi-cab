from pathlib import Path
import polars as pl

RAW_DIR = Path("data/raw")
OUTPUT_FILE = Path("data/profiles/yellow_cab_profile.parquet")

NUMERIC_COLS = [
    "passenger_count",
    "trip_distance",
    "fare_amount",
    "tip_amount",
    "tolls_amount",
    "total_amount",
]

CATEGORICAL_COLS = [
    "VendorID",
    "RatecodeID",
    "payment_type",
    "store_and_fwd_flag",
]

def normalize(lf: pl.LazyFrame) -> pl.LazyFrame:
    lf = lf.rename({"Airport_fee": "airport_fee"}, strict=False)

    lf = lf.with_columns([
        pl.col("VendorID").cast(pl.Int32),
        pl.col("PULocationID").cast(pl.Int32),
        pl.col("DOLocationID").cast(pl.Int32),
        pl.col("RatecodeID").cast(pl.Int32),
        pl.col("passenger_count").cast(pl.Int32),
        pl.col("tpep_pickup_datetime").cast(pl.Datetime("us")),
        pl.col("tpep_dropoff_datetime").cast(pl.Datetime("us")),
    ])

    return lf

def profile(file: Path) -> dict:
    lf = normalize(pl.scan_parquet(file))

    schema = lf.collect_schema()

    exprs = [pl.len().alias("rows")]

    # Missing + Unique values
    for col in schema.names():
        exprs.append(pl.col(col).null_count().alias(f"{col}_null_count"))
        exprs.append(pl.col(col).n_unique().alias(f"{col}_unique_count"))

    # Numeric summary
    for col in NUMERIC_COLS:
        exprs.append(pl.col(col).mean().alias(f"{col}_mean"))
        exprs.append(pl.col(col).std().alias(f"{col}_std"))
        exprs.append(pl.col(col).min().alias(f"{col}_min"))
        exprs.append(pl.col(col).quantile(0.25).alias(f"{col}_p25"))
        exprs.append(pl.col(col).median().alias(f"{col}_median"))
        exprs.append(pl.col(col).quantile(0.75).alias(f"{col}_p75"))
        exprs.append(pl.col(col).quantile(0.90).alias(f"{col}_p90"))
        exprs.append(pl.col(col).quantile(0.95).alias(f"{col}_p95"))
        exprs.append(pl.col(col).quantile(0.99).alias(f"{col}_p99"))
        exprs.append(pl.col(col).max().alias(f"{col}_max"))

    # Potential data quality issues
    exprs += [
        (pl.col("trip_distance") <= 0).sum().alias("trip_distance_le_0"),
        (pl.col("fare_amount") < 0).sum().alias("fare_amount_negative"),
        (pl.col("total_amount") < 0).sum().alias("total_amount_negative"),
        (pl.col("passenger_count") == 0).sum().alias("passenger_count_0"),
        (pl.col("trip_distance") > 100).sum().alias("trip_distance_gt_100"),
        (
            pl.col("tpep_dropoff_datetime") <= pl.col("tpep_pickup_datetime")
        ).sum().alias("invalid_trip_time"),
    ]

    lf = lf.with_columns(
        (pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime"))
        .dt.total_minutes()
        .alias("trip_duration_minutes")
    )

    exprs += [
        pl.col("trip_duration_minutes").min().alias("duration_min_minutes"),
        pl.col("trip_duration_minutes").median().alias("duration_median_minutes"),
        pl.col("trip_duration_minutes").mean().alias("duration_mean_minutes"),
        pl.col("trip_duration_minutes").max().alias("duration_max_minutes"),
    ]

    row = {"file": file.name}
    row.update(lf.select(exprs).collect().to_dicts()[0])

    # Category counts
    categorical_cols_present = [c for c in CATEGORICAL_COLS if c in schema.names()]
    if categorical_cols_present:
        category_dummies = (
            lf.select(categorical_cols_present)
            .collect()
            .to_dummies(columns=categorical_cols_present)
            .sum()
        )
        row.update(category_dummies.to_dicts()[0])

    # Full-row duplicates
    duplicate_count = (
        lf.group_by(schema.names())
        .len()
        .filter(pl.col("len") > 1)
        .select((pl.col("len") - 1).sum())
        .collect()
        .item()
    )

    row["duplicate_rows"] = duplicate_count or 0

    return row

def main():
    # Gather Files
    files = sorted(RAW_DIR.glob("yellow_tripdata_*.parquet"))

    # Loop files, build profile per file
    results = []
    for file in files:
        print(f"Profiling {file.name}")
        results.append(profile(file))

    summary = pl.DataFrame(results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    summary.write_parquet(OUTPUT_FILE)

    print(f"\nProfile saved to: {OUTPUT_FILE}")
    print(f"Rows: {summary.height}, Columns: {summary.width}")

if __name__ == "__main__":
    main()