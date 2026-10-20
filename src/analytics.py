import re
from pathlib import Path
import polars as pl


PROCESSED_DIR = Path("data/processed")
OUTPUT_FILE = Path("data/analytics_results.txt")
ANALYTICS_DIR = Path("data/analytics")

YEAR_PATTERN = re.compile(r"yellow_tripdata_(\d{4})-\d{2}_clean\.parquet$")


def write_line(file, text=""):
    print(text)
    file.write(str(text) + "\n")


def write_table(df: pl.DataFrame, name: str) -> None:
    df.write_parquet(ANALYTICS_DIR / f"{name}.parquet")


def with_pct_of_year(lf_agg: pl.LazyFrame) -> pl.LazyFrame:
    return lf_agg.with_columns(
        (pl.col("trip_count") / pl.col("trip_count").sum().over("year") * 100)
        .alias("pct_of_year")
    )


def warm_files(files: list[Path]) -> None:
    for file in files:
        pl.scan_parquet(file).select(pl.len()).collect()


def files_by_year(files: list[Path]) -> dict[int, list[Path]]:
    years: dict[int, list[Path]] = {}
    for file in files:
        match = YEAR_PATTERN.search(file.name)
        if not match:
            continue
        years.setdefault(int(match.group(1)), []).append(file)
    return years


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(PROCESSED_DIR.glob("*.parquet"))
    years = files_by_year(files)

    pl.Config.set_tbl_rows(-1)
    pl.Config.set_tbl_cols(-1)
    pl.Config.set_tbl_width_chars(1000)
    pl.Config.set_fmt_str_lengths(40)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        write_line(out, f"Reading processed data: {PROCESSED_DIR}/*.parquet ({len(years)} years)")
        write_line(out, "\n=== BASIC DATASET SUMMARY BY YEAR ===")

        basic_rows = []
        for year in sorted(years):
            year_files = sorted(years[year])
            write_line(out, f"Processing year {year} ({len(year_files)} files)...")
            warm_files(year_files)

            lf_year = pl.scan_parquet(year_files, extra_columns="ignore").with_columns(
                pl.lit(year).alias("year")
            )

            basic_rows.append(
                lf_year.group_by("year")
                .agg(
                    pl.len().alias("trip_count"),
                    pl.col("trip_distance").mean().alias("avg_distance"),
                    pl.col("trip_distance").median().alias("median_distance"),
                    pl.col("trip_duration_minutes").mean().alias("avg_duration"),
                    pl.col("trip_duration_minutes").median().alias("median_duration"),
                    pl.col("fare_amount").mean().alias("avg_fare"),
                    pl.col("fare_amount").median().alias("median_fare"),
                    pl.col("tip_amount").mean().alias("avg_tip"),
                    pl.col("tip_amount").median().alias("median_tip"),
                    pl.col("total_amount").mean().alias("avg_total"),
                    pl.col("total_amount").median().alias("median_total"),
                )
                .collect()
            )

        basic_by_year = pl.concat(basic_rows).sort("year")
        write_line(out, basic_by_year)
        write_table(basic_by_year, "basic_by_year")

        lf = pl.scan_parquet(PROCESSED_DIR / "*.parquet", extra_columns="ignore")
        lf = lf.with_columns(pl.col("pickup_date").dt.year().alias("year"))

        # --------------------------------------------------
        # TRIPS BY YEAR x PICKUP HOUR
        # --------------------------------------------------
        write_line(out, "\n=== TRIPS BY YEAR x PICKUP HOUR ===")

        by_hour = (
            with_pct_of_year(
                lf.group_by(["year", "pickup_hour"]).agg(pl.len().alias("trip_count"))
            )
            .sort(["year", "pickup_hour"])
            .collect()
        )

        write_line(out, by_hour)
        write_table(by_hour, "by_hour")

        # --------------------------------------------------
        # TRIPS BY YEAR x WEEKDAY
        # --------------------------------------------------
        write_line(out, "\n=== TRIPS BY YEAR x WEEKDAY ===")

        by_weekday = (
            with_pct_of_year(
                lf.group_by(["year", "pickup_weekday"]).agg(pl.len().alias("trip_count"))
            )
            .sort(["year", "pickup_weekday"])
            .collect()
        )

        write_line(out, by_weekday)
        write_table(by_weekday, "by_weekday")

        # --------------------------------------------------
        # TRIPS BY YEAR x PAYMENT TYPE
        # --------------------------------------------------
        write_line(out, "\n=== TRIPS BY YEAR x PAYMENT TYPE ===")

        by_payment = (
            with_pct_of_year(
                lf.group_by(["year", "payment_type"]).agg(pl.len().alias("trip_count"))
            )
            .sort(["year", "payment_type"])
            .collect()
        )

        write_line(out, by_payment)
        write_table(by_payment, "by_payment")

        # --------------------------------------------------
        # TRIP DISTANCE BINS, BY YEAR
        # --------------------------------------------------
        write_line(out, "\n=== TRIP DISTANCE BINS BY YEAR ===")

        distance_bins = (
            with_pct_of_year(
                lf.with_columns(
                    pl.when(pl.col("trip_distance") <= 1).then(pl.lit("0-1 mile"))
                    .when(pl.col("trip_distance") <= 3).then(pl.lit("1-3 miles"))
                    .when(pl.col("trip_distance") <= 5).then(pl.lit("3-5 miles"))
                    .when(pl.col("trip_distance") <= 10).then(pl.lit("5-10 miles"))
                    .otherwise(pl.lit("10+ miles"))
                    .alias("distance_group")
                )
                .group_by(["year", "distance_group"])
                .agg(pl.len().alias("trip_count"))
            )
            .sort(["year", "distance_group"])
            .collect()
        )

        write_line(out, distance_bins)
        write_table(distance_bins, "distance_bins")

        # --------------------------------------------------
        # PICKUP LOCATIONS, BY YEAR (ALL, not just top 20)
        # --------------------------------------------------
        write_line(out, "\n=== PICKUP LOCATIONS BY YEAR (ALL) ===")

        pickup_by_year = (
            with_pct_of_year(
                lf.group_by(["year", "PULocationID"]).agg(pl.len().alias("trip_count"))
            )
            .sort(["year", "trip_count"], descending=[False, True])
            .collect()
        )

        write_line(out, pickup_by_year)
        write_table(pickup_by_year, "pickup_by_year")

        # --------------------------------------------------
        # DROPOFF LOCATIONS, BY YEAR (ALL, not just top 20)
        # --------------------------------------------------
        write_line(out, "\n=== DROPOFF LOCATIONS BY YEAR (ALL) ===")

        dropoff_by_year = (
            with_pct_of_year(
                lf.group_by(["year", "DOLocationID"]).agg(pl.len().alias("trip_count"))
            )
            .sort(["year", "trip_count"], descending=[False, True])
            .collect()
        )

        write_line(out, dropoff_by_year)
        write_table(dropoff_by_year, "dropoff_by_year")

        # --------------------------------------------------
        # PASSENGER COUNT SUMMARY (combined, not split by year)
        # --------------------------------------------------
        write_line(out, "\n=== PASSENGER COUNT SUMMARY ===")

        passenger_summary = (
            lf.group_by("passenger_count")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("trip_distance").mean().alias("avg_distance"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("tip_amount").mean().alias("avg_tip"),
            )
            .sort("trip_count", descending=True)
            .collect()
        )

        write_line(out, passenger_summary)
        write_table(passenger_summary, "passenger_summary")

        # --------------------------------------------------
        # CORRELATIONS (combined, not split by year)
        # --------------------------------------------------
        write_line(out, "\n=== CORRELATIONS ===")

        correlations = (
            lf.select(
                pl.corr("trip_distance", "fare_amount").alias("distance_vs_fare"),
                pl.corr("trip_distance", "trip_duration_minutes").alias("distance_vs_duration"),
                pl.corr("fare_amount", "tip_amount").alias("fare_vs_tip"),
                pl.corr("trip_distance", "tip_amount").alias("distance_vs_tip"),
            )
            .collect()
        )

        write_line(out, correlations)
        write_table(correlations, "correlations")

        # --------------------------------------------------
        # POST-CLEANING RANGE CHECK (combined, sanity check)
        # --------------------------------------------------
        write_line(out, "\n=== POST-CLEANING RANGE CHECK ===")

        range_check = (
            lf.select(
                pl.col("trip_distance").min().alias("min_distance"),
                pl.col("trip_distance").max().alias("max_distance"),
                pl.col("fare_amount").min().alias("min_fare"),
                pl.col("fare_amount").max().alias("max_fare"),
                pl.col("total_amount").min().alias("min_total"),
                pl.col("total_amount").max().alias("max_total"),
                pl.col("trip_duration_minutes").min().alias("min_duration"),
                pl.col("trip_duration_minutes").max().alias("max_duration"),
            )
            .collect()
        )

        write_line(out, range_check)
        write_table(range_check, "range_check")

        # --------------------------------------------------
        # COMPLETE
        # --------------------------------------------------
        write_line(out, "\n=== ANALYTICS COMPLETE ===")
        write_line(out, f"Results saved to: {OUTPUT_FILE}")
        write_line(out, f"Per-table parquet files saved to: {ANALYTICS_DIR}/")


if __name__ == "__main__":
    main()
