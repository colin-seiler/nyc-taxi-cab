from pathlib import Path
import polars as pl

YELLOW_RAW_DIR = Path("data/raw/yellow")
RIDESHARE_RAW_DIR = Path("data/raw/rideshare")

YELLOW_OUTPUT_FILE = Path("data/profiles/yellow_cab_profile.parquet")
RIDESHARE_OUTPUT_FILE = Path("data/profiles/rideshare_profile.parquet")

NUMERIC_COLS_YELLOW = [
    "passenger_count",
    "trip_distance",
    "fare_amount",
    "tip_amount",
    "tolls_amount",
    "total_amount",
]

CATEGORICAL_COLS_YELLOW = [
    "VendorID",
    "RatecodeID",
    "payment_type",
    "store_and_fwd_flag",
]

NUMERIC_COLS_RIDESHARE = [
    "trip_miles",
    "base_passenger_fare",
    "tolls",
    "bcf",
    "sales_tax",
    "congestion_surcharge",
    "tips",
    "driver_pay",
]

CATEGORICAL_COLS_RIDESHARE = [
    "hvfhs_license_num",
    "shared_request_flag",
    "shared_match_flag",
    "access_a_ride_flag",
    "wav_request_flag",
]

def normalize(lf: pl.LazyFrame) -> pl.LazyFrame:
    lf = lf.rename({"Airport_fee": "airport_fee"}, strict=False)

    columns = lf.collect_schema().names()

    if "VendorID" in columns:
        lf = lf.with_columns(pl.col("VendorID").cast(pl.Int32))
    if "PULocationID" in columns:
        lf = lf.with_columns(pl.col("PULocationID").cast(pl.Int32))
    if "DOLocationID" in columns:
        lf = lf.with_columns(pl.col("DOLocationID").cast(pl.Int32))
    if "RatecodeID" in columns:
        lf = lf.with_columns(pl.col("RatecodeID").cast(pl.Int32))
    if "passenger_count" in columns:
        lf = lf.with_columns(pl.col("passenger_count").cast(pl.Int32))
    if "tpep_pickup_datetime" in columns:
        lf = lf.with_columns(pl.col("tpep_pickup_datetime").cast(pl.Datetime("us")))
    if "tpep_dropoff_datetime" in columns:
        lf = lf.with_columns(pl.col("tpep_dropoff_datetime").cast(pl.Datetime("us")))
    if "pickup_datetime" in columns:
        lf = lf.with_columns(pl.col("pickup_datetime").cast(pl.Datetime("us")))
    if "dropoff_datetime" in columns:
        lf = lf.with_columns(pl.col("dropoff_datetime").cast(pl.Datetime("us")))
    if "request_datetime" in columns:
        lf = lf.with_columns(pl.col("request_datetime").cast(pl.Datetime("us")))
    if "on_scene_datetime" in columns:
        lf = lf.with_columns(pl.col("on_scene_datetime").cast(pl.Datetime("us")))

    if "cbd_congestion_fee" in columns:
        lf = lf.with_columns(pl.col("cbd_congestion_fee").cast(pl.Float64))
    else:
        lf = lf.with_columns(pl.lit(None, dtype=pl.Float64).alias("cbd_congestion_fee"))

    return lf

def profile(file: Path, dataset: str) -> dict:
    lf = normalize(pl.scan_parquet(file))

    if dataset == "rideshare":
        # Uber (HV0003) and Lyft (HV0005)
        lf = lf.filter(pl.col("hvfhs_license_num").is_in(["HV0003", "HV0005"]))

    schema = lf.collect_schema()

    exprs = [pl.len().alias("rows")]

    # Missing + Unique values
    for col in schema.names():
        exprs.append(pl.col(col).null_count().alias(f"{col}_null_count"))
        exprs.append(pl.col(col).n_unique().alias(f"{col}_unique_count"))

    if dataset == "yellow":
        numeric_cols = NUMERIC_COLS_YELLOW
        categorical_cols = CATEGORICAL_COLS_YELLOW
    if dataset == "rideshare":
        numeric_cols = NUMERIC_COLS_RIDESHARE
        categorical_cols = CATEGORICAL_COLS_RIDESHARE

    # Numeric summary
    for col in numeric_cols:
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
    if dataset == "yellow":
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

    if dataset == "rideshare":
        exprs += [
            (pl.col("trip_miles") <= 0).sum().alias("trip_miles_le_0"),
            (pl.col("base_passenger_fare") < 0).sum().alias("base_passenger_fare_negative"),
            (pl.col("trip_miles") > 100).sum().alias("trip_miles_gt_100"),
            (
                pl.col("dropoff_datetime") <= pl.col("pickup_datetime")
            ).sum().alias("invalid_trip_time"),
        ]

        lf = lf.with_columns(
            (pl.col("dropoff_datetime") - pl.col("pickup_datetime"))
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
    categorical_cols_present = [c for c in categorical_cols if c in schema.names()]
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

def main(yellow=False, rideshare=False):
    if yellow:
        files = sorted(YELLOW_RAW_DIR.glob("yellow_tripdata_*.parquet"))

        results = []
        for file in files:
            print(f"Profiling {file.name}")
            results.append(profile(file, dataset="yellow"))

        summary = pl.DataFrame(results)

        YELLOW_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        summary.write_parquet(YELLOW_OUTPUT_FILE)

        print(f"\nProfile saved to: {YELLOW_OUTPUT_FILE}")
        print(f"Rows: {summary.height}, Columns: {summary.width}")

    if rideshare:
        files = sorted(RIDESHARE_RAW_DIR.glob("fhvhv_tripdata_*.parquet"))

        results = []
        for file in files:
            print(f"Profiling {file.name}")
            results.append(profile(file, dataset="rideshare"))

        summary = pl.DataFrame(results)

        RIDESHARE_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        summary.write_parquet(RIDESHARE_OUTPUT_FILE)

        print(f"\nProfile saved to: {RIDESHARE_OUTPUT_FILE}")
        print(f"Rows: {summary.height}, Columns: {summary.width}")

if __name__ == "__main__":
    main(yellow=True)
