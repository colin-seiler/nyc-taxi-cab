import argparse
import sys

from data_access import main as download_files, YEARS
from data_profile import main as run_profile
from data_cleaning import main as run_cleaning
from analytics import main as run_analytics

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download_files', action='store_true', help='Use if need download raw files before running pipeline')
    parser.add_argument('--yellow_taxi', action='store_true', help='Process yellow taxi data')
    parser.add_argument('--rideshare', action='store_true', help='Process rideshare (FHVHV) data')
    parser.add_argument('--delete_raw', action='store_true', help='Delete each raw file once its processed/cleaned file has been written')

    args = parser.parse_args()

    if not args.yellow_taxi and not args.rideshare:
        sys.exit('Must pass at least one of --yellow_taxi or --rideshare')

    if args.download_files:
        print('\n')
        print("=" * 60)
        print('DOWNLOADING RAW FILES')
        print("=" * 60)
        download_files(YEARS, yellow=args.yellow_taxi, rideshare=args.rideshare)

    print('\n')
    print("=" * 60)
    print("PHASE 2 PIPELINE START")
    print("=" * 60)

    print("\nProfiling raw data...")
    run_profile(yellow=args.yellow_taxi, rideshare=args.rideshare)

    print("\nCleaning and processing data...")
    run_cleaning(yellow=args.yellow_taxi, rideshare=args.rideshare, delete_raw=args.delete_raw)

    print("\nRunning analytics...")
    run_analytics(yellow=args.yellow_taxi, rideshare=args.rideshare)

    print("\n" + "=" * 60)
    print("PHASE 2 PIPELINE COMPLETE")
    print("=" * 60)

    print("\nGenerated outputs:")
    if args.yellow_taxi:
        print("- data/profiles/yellow_cab_profile.parquet")
        print("- data/cleaning_results_yellow.txt")
        print("- data/analytics_results_yellow.txt")
        print("- data/processed/yellow/*.parquet")
        print("- data/analytics/yellow/*.parquet")
    if args.rideshare:
        print("- data/profiles/rideshare_profile.parquet")
        print("- data/cleaning_results_rideshare.txt")
        print("- data/analytics_results_rideshare.txt")
        print("- data/processed/rideshare/*.parquet")
        print("- data/analytics/rideshare/*.parquet")


if __name__ == "__main__":
    main()
