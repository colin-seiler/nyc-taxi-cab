from pathlib import Path
import polars as pl


PROCESSED_FILE = Path(
    "data/processed/yellow_tripdata_2025-01_clean.parquet"
)

OUTPUT_FILE = Path(
    "data/analytics_results.txt"
)


def write_line(file, text=""):
    print(text)
    file.write(str(text) + "\n")


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    lf = pl.scan_parquet(PROCESSED_FILE)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        write_line(out, f"Reading processed data: {PROCESSED_FILE}")

        # --------------------------------------------------
        # BASIC DATASET SUMMARY
        # --------------------------------------------------
        write_line(out, "\n=== BASIC DATASET SUMMARY ===")

        basic_summary = (
            lf.select(
                pl.len().alias("rows"),
                pl.col("trip_distance").mean().alias("avg_trip_distance"),
                pl.col("trip_duration_minutes").mean().alias("avg_trip_duration"),
                pl.col("fare_amount").mean().alias("avg_fare_amount"),
                pl.col("tip_amount").mean().alias("avg_tip_amount"),
                pl.col("total_amount").mean().alias("avg_total_amount")
            )
            .collect()
        )

        write_line(out, basic_summary)

        # --------------------------------------------------
        # TRIPS BY PICKUP HOUR
        # --------------------------------------------------
        write_line(out, "\n=== TRIPS BY PICKUP HOUR ===")

        trips_by_hour = (
            lf.group_by("pickup_hour")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("trip_distance").mean().alias("avg_distance"),
                pl.col("trip_duration_minutes").mean().alias("avg_duration")
            )
            .sort("pickup_hour")
            .collect()
        )

        write_line(out, trips_by_hour)

        # --------------------------------------------------
        # TRIPS BY WEEKDAY
        # --------------------------------------------------
        write_line(out, "\n=== TRIPS BY WEEKDAY ===")

        trips_by_weekday = (
            lf.group_by("pickup_weekday")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("trip_distance").mean().alias("avg_distance"),
                pl.col("trip_duration_minutes").mean().alias("avg_duration")
            )
            .sort("pickup_weekday")
            .collect()
        )

        write_line(out, trips_by_weekday)

        # --------------------------------------------------
        # PAYMENT TYPE
        # --------------------------------------------------
        write_line(out, "\n=== PAYMENT TYPE SUMMARY ===")

        payment_summary = (
            lf.group_by("payment_type")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("tip_amount").mean().alias("avg_tip"),
                pl.col("total_amount").mean().alias("avg_total")
            )
            .sort("trip_count", descending=True)
            .collect()
        )

        write_line(out, payment_summary)

        # --------------------------------------------------
        # PASSENGER COUNT
        # --------------------------------------------------
        write_line(out, "\n=== PASSENGER COUNT SUMMARY ===")

        passenger_summary = (
            lf.group_by("passenger_count")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("trip_distance").mean().alias("avg_distance"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("tip_amount").mean().alias("avg_tip")
            )
            .sort("trip_count", descending=True)
            .collect()
        )

        write_line(out, passenger_summary)

        # --------------------------------------------------
        # TOP PICKUP LOCATIONS
        # --------------------------------------------------
        write_line(out, "\n=== TOP 20 PICKUP LOCATIONS ===")

        top_pickup_locations = (
            lf.group_by("PULocationID")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("trip_distance").mean().alias("avg_distance")
            )
            .sort("trip_count", descending=True)
            .head(20)
            .collect()
        )

        write_line(out, top_pickup_locations)

        # --------------------------------------------------
        # TOP DROPOFF LOCATIONS
        # --------------------------------------------------
        write_line(out, "\n=== TOP 20 DROPOFF LOCATIONS ===")

        top_dropoff_locations = (
            lf.group_by("DOLocationID")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("trip_distance").mean().alias("avg_distance")
            )
            .sort("trip_count", descending=True)
            .head(20)
            .collect()
        )

        write_line(out, top_dropoff_locations)

        # --------------------------------------------------
        # DAILY TRIP COUNTS
        # --------------------------------------------------
        write_line(out, "\n=== DAILY TRIP COUNTS ===")

        daily_trips = (
            lf.group_by("pickup_date")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("trip_distance").mean().alias("avg_distance"),
                pl.col("trip_duration_minutes").mean().alias("avg_duration")
            )
            .sort("pickup_date")
            .collect()
        )

        write_line(out, daily_trips)

        # --------------------------------------------------
        # TRIP DISTANCE BINS
        # --------------------------------------------------
        write_line(out, "\n=== TRIP DISTANCE BINS ===")

        distance_bins = (
            lf.with_columns(
                pl.when(pl.col("trip_distance") <= 1)
                .then(pl.lit("0-1 mile"))
                .when(pl.col("trip_distance") <= 3)
                .then(pl.lit("1-3 miles"))
                .when(pl.col("trip_distance") <= 5)
                .then(pl.lit("3-5 miles"))
                .when(pl.col("trip_distance") <= 10)
                .then(pl.lit("5-10 miles"))
                .otherwise(pl.lit("10+ miles"))
                .alias("distance_group")
            )
            .group_by("distance_group")
            .agg(
                pl.len().alias("trip_count"),
                pl.col("fare_amount").mean().alias("avg_fare"),
                pl.col("tip_amount").mean().alias("avg_tip"),
                pl.col("trip_duration_minutes").mean().alias("avg_duration")
            )
            .sort("trip_count", descending=True)
            .collect()
        )

        write_line(out, distance_bins)

        # --------------------------------------------------
        # CORRELATION ANALYSIS
        # --------------------------------------------------
        write_line(out, "\n=== CORRELATIONS ===")

        correlations = (
            lf.select(
                pl.corr("trip_distance", "fare_amount")
                .alias("distance_vs_fare"),

                pl.corr("trip_distance", "trip_duration_minutes")
                .alias("distance_vs_duration"),

                pl.corr("fare_amount", "tip_amount")
                .alias("fare_vs_tip"),

                pl.corr("trip_distance", "tip_amount")
                .alias("distance_vs_tip")
            )
            .collect()
        )

        write_line(out, correlations)

        # --------------------------------------------------
        # EXTREME VALUES AFTER CLEANING
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
                pl.col("trip_duration_minutes").max().alias("max_duration")
            )
            .collect()
        )

        write_line(out, range_check)

        # --------------------------------------------------
        # COMPLETE
        # --------------------------------------------------
        write_line(out, "\n=== ANALYTICS COMPLETE ===")
        write_line(out, f"Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()