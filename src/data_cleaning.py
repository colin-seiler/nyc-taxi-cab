import re
from pathlib import Path
import polars as pl

from data_profile import normalize


YELLOW_RAW_DIR = Path("data/raw/yellow")
RIDESHARE_RAW_DIR = Path("data/raw/rideshare")

YELLOW_PROCESSED_DIR = Path("data/processed/yellow")
RIDESHARE_PROCESSED_DIR = Path("data/processed/rideshare")

YELLOW_OUTPUT_FILE = Path("data/cleaning_results_yellow.txt")
RIDESHARE_OUTPUT_FILE = Path("data/cleaning_results_rideshare.txt")

YELLOW_FILENAME_PATTERN = re.compile(r"yellow_tripdata_(\d{4})-(\d{2})\.parquet$")
RIDESHARE_FILENAME_PATTERN = re.compile(r"fhvhv_tripdata_(\d{4})-(\d{2})\.parquet$")


def clean(file: Path, dataset: str, delete_raw: bool = False) -> dict:
    if dataset == "yellow":
        match = YELLOW_FILENAME_PATTERN.search(file.name)
    if dataset == "rideshare":
        match = RIDESHARE_FILENAME_PATTERN.search(file.name)

    year, month = int(match.group(1)), int(match.group(2))
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    lf = normalize(pl.scan_parquet(file))

    if dataset == "rideshare":
        # Only Uber (HV0003) and Lyft (HV0005) - Juno/Via aren't in scope
        lf = lf.filter(pl.col("hvfhs_license_num").is_in(["HV0003", "HV0005"]))

    if dataset == "yellow":
        lf = lf.with_columns(
            (pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime"))
            .dt.total_seconds()
            .truediv(60)
            .alias("trip_duration_minutes")
        )
    if dataset == "rideshare":
        lf = lf.with_columns(
            (pl.col("dropoff_datetime") - pl.col("pickup_datetime"))
            .dt.total_seconds()
            .truediv(60)
            .alias("trip_duration_minutes")
        )

    # Failing rules counts for diagnostics
    if dataset == "yellow":
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
                (pl.col("fare_amount") < 0) | (pl.col("fare_amount") > 1000)
            ).sum().alias("removed_fare_bounds"),

            (
                (pl.col("total_amount") < 0) | (pl.col("total_amount") > 1000)
            ).sum().alias("removed_total_bounds"),
        ]).collect().to_dicts()[0]

    if dataset == "rideshare":
        diagnostics = lf.select([
            pl.len().alias("rows"),

            (
                (pl.col("pickup_datetime") < pl.datetime(year, month, 1))
                | (pl.col("pickup_datetime") >= pl.datetime(next_year, next_month, 1))
            ).sum().alias("removed_wrong_month"),

            (pl.col("dropoff_datetime") <= pl.col("pickup_datetime"))
            .sum().alias("removed_invalid_time_order"),

            (
                (pl.col("trip_miles") <= 0) | (pl.col("trip_miles") > 120)
            ).sum().alias("removed_distance_bounds"),

            (
                (pl.col("trip_duration_minutes") < 1) | (pl.col("trip_duration_minutes") > 360)
            ).sum().alias("removed_duration_bounds"),

            (
                (pl.col("base_passenger_fare") < 0) | (pl.col("base_passenger_fare") > 1000)
            ).sum().alias("removed_fare_bounds"),
        ]).collect().to_dicts()[0]

    original_rows = diagnostics.pop("rows")

    if dataset == "yellow":
        cleaned = (
            lf.filter(
                # Keep only this file's own year-month
                (pl.col("tpep_pickup_datetime") >= pl.datetime(year, month, 1))
                & (pl.col("tpep_pickup_datetime") < pl.datetime(next_year, next_month, 1))

                # Valid time order
                & (pl.col("tpep_dropoff_datetime") > pl.col("tpep_pickup_datetime"))

                # Reasonable distance (idea is Manhattan -> Philly or Hamptons)
                & (pl.col("trip_distance") > 0)
                & (pl.col("trip_distance") <= 120)

                # Positive and plausible trip duration
                & (pl.col("trip_duration_minutes") >= 1)
                & (pl.col("trip_duration_minutes") <= 360)

                # Non-negative monetary values
                & (pl.col("fare_amount") >= 0)
                & (pl.col("total_amount") >= 0)

                # Remove extreme monetary outliers
                & (pl.col("fare_amount") <= 1000)
                & (pl.col("total_amount") <= 1000)
            )
            .with_columns([
                pl.col("tpep_pickup_datetime").dt.hour().alias("pickup_hour"),
                pl.col("tpep_pickup_datetime").dt.weekday().alias("pickup_weekday"),
                pl.col("tpep_pickup_datetime").dt.date().alias("pickup_date"),
            ])
        )

    if dataset == "rideshare":
        cleaned = (
            lf.filter(
                # Keep only this file's own year-month
                (pl.col("pickup_datetime") >= pl.datetime(year, month, 1))
                & (pl.col("pickup_datetime") < pl.datetime(next_year, next_month, 1))

                # Valid time order
                & (pl.col("dropoff_datetime") > pl.col("pickup_datetime"))

                # Reasonable distance (same real-world logic as yellow taxi)
                & (pl.col("trip_miles") > 0)
                & (pl.col("trip_miles") <= 120)

                # Positive and plausible trip duration
                & (pl.col("trip_duration_minutes") >= 1)
                & (pl.col("trip_duration_minutes") <= 360)

                # Non-negative fare, with surge-pricing margin above yellow's metered ceiling
                & (pl.col("base_passenger_fare") >= 0)
                & (pl.col("base_passenger_fare") <= 1000)
            )
            .with_columns([
                pl.col("pickup_datetime").dt.hour().alias("pickup_hour"),
                pl.col("pickup_datetime").dt.weekday().alias("pickup_weekday"),
                pl.col("pickup_datetime").dt.date().alias("pickup_date"),
            ])
        )

    cleaned_rows = cleaned.select(pl.len()).collect().item()

    if dataset == "yellow":
        dest = YELLOW_PROCESSED_DIR / file.name.replace(".parquet", "_clean.parquet")
    if dataset == "rideshare":
        dest = RIDESHARE_PROCESSED_DIR / file.name.replace(".parquet", "_clean.parquet")

    dest.parent.mkdir(parents=True, exist_ok=True)
    cleaned.collect(engine="streaming").write_parquet(dest)

    if delete_raw:
        file.unlink()

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


def write_cleaning_summary(results, output_file, rules_lines):
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

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("=== CLEANING SUMMARY (per file, with totals) ===\n")
        out.write(str(summary_with_total))

        out.write("\n\n=== CLEANING RULES ===\n")
        for line in rules_lines:
            out.write(line + "\n")

        out.write("\n=== MISSING VALUE POLICY ===\n")
        out.write(
            "passenger_count, RatecodeID, and store_and_fwd_flag null values "
            "were retained rather than dropping entire trips.\n"
        )


def main(yellow=False, rideshare=False, delete_raw=False):
    if yellow:
        YELLOW_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        YELLOW_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        files = sorted(YELLOW_RAW_DIR.glob("yellow_tripdata_*.parquet"))

        results = []
        for file in files:
            print(f"Cleaning {file.name}")
            results.append(clean(file, dataset="yellow", delete_raw=delete_raw))

        write_cleaning_summary(results, YELLOW_OUTPUT_FILE, [
            "Pickup date: restricted to each file's own year-month",
            "Trip distance: > 0 and <= 120 miles",
            "Trip duration: 1 to 360 minutes",
            "Fare amount: $0 to $1000",
            "Total amount: $0 to $1000",
            "Dropoff time must be after pickup time",
        ])

        print(f"\nCleaned {len(files)} files -> {YELLOW_PROCESSED_DIR}")
        print(f"Summary written to {YELLOW_OUTPUT_FILE}")

    if rideshare:
        RIDESHARE_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        RIDESHARE_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        files = sorted(RIDESHARE_RAW_DIR.glob("fhvhv_tripdata_*.parquet"))

        results = []
        for file in files:
            print(f"Cleaning {file.name}")
            results.append(clean(file, dataset="rideshare", delete_raw=delete_raw))

        write_cleaning_summary(results, RIDESHARE_OUTPUT_FILE, [
            "Only Uber (HV0003) and Lyft (HV0005) trips retained",
            "Pickup date: restricted to each file's own year-month",
            "Trip distance: > 0 and <= 120 miles",
            "Trip duration: 1 to 360 minutes",
            "Base passenger fare: $0 to $1000",
            "Dropoff time must be after pickup time",
        ])

        print(f"\nCleaned {len(files)} files -> {RIDESHARE_PROCESSED_DIR}")
        print(f"Summary written to {RIDESHARE_OUTPUT_FILE}")


if __name__ == "__main__":
    main(rideshare=True, delete_raw=True)
