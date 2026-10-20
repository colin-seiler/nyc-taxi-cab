import argparse

from data_access import main as download_files
from data_profile import main as run_profile
from data_cleaning import main as run_cleaning
from analytics import main as run_analytics

YEARS = ['2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download_files', action='store_true', help='Use if need download raw taxi files before running pipeline')

    args = parser.parse_args()

    if args.download_files:
        print('\n')
        print("=" * 60)
        print('DOWNLOADING RAW FILES')
        print("=" * 60)
        download_files(YEARS)

    print('\n')
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
    print("- data/profiles/yellow_cab_profile.parquet")
    print("- data/cleaning_results.txt")
    print("- data/analytics_results.txt")
    print("- data/processed/*.parquet (108 files, 2017-2025)")


if __name__ == "__main__":
    main()