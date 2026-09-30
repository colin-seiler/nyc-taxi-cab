from pathlib import Path
import polars as pl


RAW_FILE = Path("data/raw/yellow_tripdata_2025-01.parquet")
PROCESSED_FILE = Path(
    "data/processed/yellow_tripdata_2025-01_clean.parquet"
)
OUTPUT_FILE = Path("data/cleaning_results.txt")


def write_line(file, text=""):
    print(text)
    file.write(str(text) + "\n")


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)

    lf = pl.scan_parquet(RAW_FILE)

    original_rows = (
        lf.select(pl.len())
        .collect()
        .item()
    )

    # Add derived trip duration first
    lf = lf.with_columns(
        (
            pl.col("tpep_dropoff_datetime")
            - pl.col("tpep_pickup_datetime")
        )
        .dt.total_seconds()
        .truediv(60)
        .alias("trip_duration_minutes")
    )

    # Cleaning rules
    cleaned = (
        lf
        .filter(
            # Keep only January 2025 records
            (
                pl.col("tpep_pickup_datetime")
                >= pl.datetime(2025, 1, 1)
            )
            &
            (
                pl.col("tpep_pickup_datetime")
                < pl.datetime(2025, 2, 1)
            )

            # Valid time order
            & (
                pl.col("tpep_dropoff_datetime")
                > pl.col("tpep_pickup_datetime")
            )

            # Reasonable distance
            & (pl.col("trip_distance") > 0)
            & (pl.col("trip_distance") <= 100)

            # Positive / plausible trip duration
            & (pl.col("trip_duration_minutes") >= 1)
            & (pl.col("trip_duration_minutes") <= 240)

            # Non-negative monetary values
            & (pl.col("fare_amount") >= 0)
            & (pl.col("total_amount") >= 0)

            # Remove extreme monetary outliers
            & (pl.col("fare_amount") <= 500)
            & (pl.col("total_amount") <= 600)
        )
        .with_columns([
            pl.col("tpep_pickup_datetime")
            .dt.hour()
            .alias("pickup_hour"),

            pl.col("tpep_pickup_datetime")
            .dt.weekday()
            .alias("pickup_weekday"),

            pl.col("tpep_pickup_datetime")
            .dt.date()
            .alias("pickup_date")
        ])
    )

    cleaned_rows = (
        cleaned.select(pl.len())
        .collect()
        .item()
    )

    removed_rows = original_rows - cleaned_rows
    removed_percent = removed_rows / original_rows * 100

    # Save cleaned data
    cleaned.collect(engine="streaming").write_parquet(
        PROCESSED_FILE
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        write_line(out, "=== CLEANING SUMMARY ===")
        write_line(out, f"Original rows: {original_rows:,}")
        write_line(out, f"Cleaned rows:  {cleaned_rows:,}")
        write_line(out, f"Removed rows:  {removed_rows:,}")
        write_line(out, f"Removed %:     {removed_percent:.2f}%")

        write_line(out, "\n=== CLEANING RULES ===")
        write_line(out, "Pickup date: January 2025 only")
        write_line(out, "Trip distance: > 0 and <= 100 miles")
        write_line(out, "Trip duration: 1 to 240 minutes")
        write_line(out, "Fare amount: $0 to $500")
        write_line(out, "Total amount: $0 to $600")
        write_line(out, "Dropoff time must be after pickup time")

        write_line(out, "\n=== MISSING VALUE POLICY ===")
        write_line(
            out,
            "Passenger count null values were retained."
        )
        write_line(
            out,
            "RatecodeID and store_and_fwd_flag null values were retained."
        )
        write_line(
            out,
            "Missing categorical values will be handled within "
            "relevant analyses rather than dropping entire trips."
        )

        write_line(out, "\n=== OUTPUT ===")
        write_line(out, f"Saved to: {PROCESSED_FILE}")


if __name__ == "__main__":
    main()