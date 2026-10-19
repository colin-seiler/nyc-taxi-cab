import re
from pathlib import Path
import polars as pl

from data_profile import normalize


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
OUTPUT_FILE = Path("data/cleaning_results.txt")

FILENAME_PATTERN = re.compile(r"yellow_tripdata_(\d{4})-(\d{2})\.parquet$")


def clean(file: Path) -> dict:
    match = FILENAME_PATTERN.search(file.name)
    year, month = int(match.group(1)), int(match.group(2))
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    lf = normalize(pl.scan_parquet(file))

    lf = lf.with_columns(
        (pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime"))
        .dt.total_seconds()
        .truediv(60)
        .alias("trip_duration_minutes")
    )

    # Failing rules counts for diagnostics
    diagnostics = lf.select([
        pl.len().alias("rows"),

        (
            (pl.col("tpep_pickup_datetime") < pl.datetime(year, month, 1))
            | (pl.col("tpep_pickup_datetime") >= pl.datetime(next_year, next_month, 1))
        ).sum().alias("removed_wrong_month"),

        (pl.col("tpep_dropoff_datetime") <= pl.col("tpep_pickup_datetime"))
        .sum().alias("removed_invalid_time_order"),

        (
            (pl.col("trip_distance") <= 0) | (pl.col("trip_distance") > 120)
        ).sum().alias("removed_distance_bounds"),

        (
            (pl.col("trip_duration_minutes") < 1) | (pl.col("trip_duration_minutes") > 360)
        ).sum().alias("removed_duration_bounds"),

        (
            (pl.col("fare_amount") < 0) | (pl.col("fare_amount") > 500)
        ).sum().alias("removed_fare_bounds"),

        (
            (pl.col("total_amount") < 0) | (pl.col("total_amount") > 600)
        ).sum().alias("removed_total_bounds"),
    ]).collect().to_dicts()[0]

    original_rows = diagnostics.pop("rows")

    cleaned = (
        lf.filter(
            # Keep only this file's own year-month
            (pl.col("tpep_pickup_datetime") >= pl.datetime(year, month, 1))
            & (pl.col("tpep_pickup_datetime") < pl.datetime(next_year, next_month, 1))

            # Valid time order
            & (pl.col("tpep_dropoff_datetime") > pl.col("tpep_pickup_datetime"))

            # Reasonable distance (idea is Manhattan -> Philly or Hmpatons)
            & (pl.col("trip_distance") > 0)
            & (pl.col("trip_distance") <= 120)

            # Positive and plausible trip duration
            & (pl.col("trip_duration_minutes") >= 1)
            & (pl.col("trip_duration_minutes") <= 360)

            # Non-negative monetary values
            & (pl.col("fare_amount") >= 0)
            & (pl.col("total_amount") >= 0)

            # Remove extreme monetary outliers
            & (pl.col("fare_amount") <= 500)
            & (pl.col("total_amount") <= 600)
        )
        .with_columns([
            pl.col("tpep_pickup_datetime").dt.hour().alias("pickup_hour"),
            pl.col("tpep_pickup_datetime").dt.weekday().alias("pickup_weekday"),
            pl.col("tpep_pickup_datetime").dt.date().alias("pickup_date"),
        ])
    )

    cleaned_rows = cleaned.select(pl.len()).collect().item()

    dest = PROCESSED_DIR / file.name.replace(".parquet", "_clean.parquet")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cleaned.collect(engine="streaming").write_parquet(dest)

    removed_rows = original_rows - cleaned_rows

    result = {
        "file": file.name,
        "original_rows": original_rows,
        "cleaned_rows": cleaned_rows,
        "removed_rows": removed_rows,
        "removed_percent": (removed_rows / original_rows * 100) if original_rows else 0.0,
    }
    result.update(diagnostics)
    return result


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(RAW_DIR.glob("yellow_tripdata_*.parquet"))

    results = []
    for file in files:
        print(f"Cleaning {file.name}")
        results.append(clean(file))

    summary = pl.DataFrame(results)

    total_original = summary["original_rows"].sum()
    total_cleaned = summary["cleaned_rows"].sum()
    total_removed = summary["removed_rows"].sum()

    totals_row = {
        "file": "TOTAL",
        "original_rows": total_original,
        "cleaned_rows": total_cleaned,
        "removed_rows": total_removed,
        "removed_percent": (total_removed / total_original * 100) if total_original else 0.0,
    }

    reason_cols = [c for c in summary.columns if c.startswith("removed_") and c not in totals_row]
    for col in reason_cols:
        totals_row[col] = summary[col].sum()

    summary_with_total = pl.concat([summary, pl.DataFrame([totals_row])])

    pl.Config.set_tbl_rows(-1)
    pl.Config.set_fmt_str_lengths(40)
    pl.Config.set_tbl_cols(-1)
    pl.Config.set_tbl_width_chars(1000)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("=== CLEANING SUMMARY (per file, with totals) ===\n")
        out.write(str(summary_with_total))

        out.write("\n\n=== CLEANING RULES ===\n")
        out.write("Pickup date: restricted to each file's own year-month\n")
        out.write("Trip distance: > 0 and <= 120 miles\n")
        out.write("Trip duration: 1 to 360 minutes\n")
        out.write("Fare amount: $0 to $500\n")
        out.write("Total amount: $0 to $600\n")
        out.write("Dropoff time must be after pickup time\n")

        out.write("\n=== MISSING VALUE POLICY ===\n")
        out.write(
            "passenger_count, RatecodeID, and store_and_fwd_flag null values "
            "were retained rather than dropping entire trips.\n"
        )

    print(f"\nCleaned {len(files)} files -> {PROCESSED_DIR}")
    print(f"Summary written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
