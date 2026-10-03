from data_profile import main as run_profile
from data_cleaning import main as run_cleaning
from analytics import main as run_analytics


def main():
    print("=" * 60)
    print("PHASE 2 PIPELINE START")
    print("=" * 60)

    print("\n[1/3] Profiling raw data...")
    run_profile()

    print("\n[2/3] Cleaning and processing data...")
    run_cleaning()

    print("\n[3/3] Running analytics...")
    run_analytics()

    print("\n" + "=" * 60)
    print("PHASE 2 PIPELINE COMPLETE")
    print("=" * 60)

    print("\nGenerated outputs:")
    print("- data/profile_results.txt")
    print("- data/cleaning_results.txt")
    print("- data/analytics_results.txt")
    print("- data/processed/yellow_tripdata_2025-01_clean.parquet")


if __name__ == "__main__":
    main()