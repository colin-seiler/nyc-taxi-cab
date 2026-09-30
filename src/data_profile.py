from pathlib import Path
import polars as pl


RAW_FILE = Path("data/raw/yellow_tripdata_2025-01.parquet")
OUTPUT_FILE = Path("data/profile_results.txt")


def write_line(file, text=""):
    print(text)
    file.write(str(text) + "\n")


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        write_line(out, f"Reading: {RAW_FILE}")

        # Lazy scan: does not immediately load the entire dataset into memory
        lf = pl.scan_parquet(RAW_FILE)

        # --------------------------------------------------
        # SCHEMA
        # --------------------------------------------------
        write_line(out, "\n=== SCHEMA ===")

        schema = lf.collect_schema()

        for column, dtype in schema.items():
            write_line(out, f"{column}: {dtype}")

        # --------------------------------------------------
        # BASIC SIZE
        # --------------------------------------------------
        write_line(out, "\n=== BASIC SIZE ===")

        row_count = (
            lf.select(pl.len().alias("rows"))
            .collect()
            .item()
        )

        write_line(out, f"Rows: {row_count:,}")
        write_line(out, f"Columns: {len(schema)}")

        # --------------------------------------------------
        # SAMPLE
        # --------------------------------------------------
        write_line(out, "\n=== SAMPLE ===")

        sample = lf.head(5).collect()
        write_line(out, sample)

        # --------------------------------------------------
        # MISSING VALUES
        # --------------------------------------------------
        write_line(out, "\n=== MISSING VALUES ===")

        missing = (
            lf.select(
                [
                    pl.col(col).null_count().alias(col)
                    for col in schema.names()
                ]
            )
            .collect()
        )

        missing_table = missing.transpose(
            include_header=True,
            header_name="column",
            column_names=["null_count"]
        )

        write_line(out, missing_table)

        # --------------------------------------------------
        # UNIQUE VALUES
        # --------------------------------------------------
        write_line(out, "\n=== UNIQUE VALUES ===")

        unique_counts = (
            lf.select(
                [
                    pl.col(col).n_unique().alias(col)
                    for col in schema.names()
                ]
            )
            .collect()
        )

        unique_table = unique_counts.transpose(
            include_header=True,
            header_name="column",
            column_names=["unique_count"]
        )

        write_line(out, unique_table)

        # --------------------------------------------------
        # DUPLICATES
        # --------------------------------------------------
        write_line(out, "\n=== DUPLICATES ===")

        duplicate_count = (
            lf.group_by(schema.names())
            .len()
            .filter(pl.col("len") > 1)
            .select((pl.col("len") - 1).sum())
            .collect()
            .item()
        )

        if duplicate_count is None:
            duplicate_count = 0

        write_line(out, f"Duplicate rows: {duplicate_count:,}")

        # --------------------------------------------------
        # NUMERIC SUMMARY
        # --------------------------------------------------
        write_line(out, "\n=== NUMERIC SUMMARY ===")

        numeric_cols = [
            "passenger_count",
            "trip_distance",
            "fare_amount",
            "tip_amount",
            "tolls_amount",
            "total_amount"
        ]

        numeric_summary = (
            lf.select(numeric_cols)
            .collect()
            .describe()
        )

        write_line(out, numeric_summary)

        # --------------------------------------------------
        # CATEGORY COUNTS
        # --------------------------------------------------
        write_line(out, "\n=== CATEGORY COUNTS ===")

        categorical_cols = [
            "VendorID",
            "RatecodeID",
            "payment_type",
            "store_and_fwd_flag"
        ]

        for col in categorical_cols:

            write_line(out, f"\n--- {col} ---")

            category_counts = (
                lf.group_by(col)
                .len()
                .sort("len", descending=True)
                .collect()
            )

            write_line(out, category_counts)

        # --------------------------------------------------
        # POTENTIAL DATA QUALITY ISSUES
        # --------------------------------------------------
        write_line(out, "\n=== POTENTIAL DATA QUALITY ISSUES ===")

        quality_checks = (
            lf.select([
                (pl.col("trip_distance") <= 0)
                .sum()
                .alias("trip_distance_le_0"),

                (pl.col("fare_amount") < 0)
                .sum()
                .alias("fare_amount_negative"),

                (pl.col("total_amount") < 0)
                .sum()
                .alias("total_amount_negative"),

                (pl.col("passenger_count") == 0)
                .sum()
                .alias("passenger_count_0"),

                (pl.col("trip_distance") > 100)
                .sum()
                .alias("trip_distance_gt_100"),

                (
                    pl.col("tpep_dropoff_datetime")
                    <= pl.col("tpep_pickup_datetime")
                )
                .sum()
                .alias("invalid_trip_time")
            ])
            .collect()
        )

        quality_table = quality_checks.transpose(
            include_header=True,
            header_name="issue",
            column_names=["count"]
        )

        write_line(out, quality_table)

        # --------------------------------------------------
        # TRIP DURATION
        # --------------------------------------------------
        write_line(out, "\n=== TRIP DURATION CHECK ===")

        duration_stats = (
            lf.with_columns(
                (
                    pl.col("tpep_dropoff_datetime")
                    - pl.col("tpep_pickup_datetime")
                )
                .dt.total_minutes()
                .alias("trip_duration_minutes")
            )
            .select(
                pl.col("trip_duration_minutes")
                .min()
                .alias("min_minutes"),

                pl.col("trip_duration_minutes")
                .median()
                .alias("median_minutes"),

                pl.col("trip_duration_minutes")
                .mean()
                .alias("mean_minutes"),

                pl.col("trip_duration_minutes")
                .max()
                .alias("max_minutes")
            )
            .collect()
        )

        write_line(out, duration_stats)

        # --------------------------------------------------
        # FINAL MESSAGE
        # --------------------------------------------------
        write_line(out, "\n=== PROFILE COMPLETE ===")
        write_line(out, f"Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()