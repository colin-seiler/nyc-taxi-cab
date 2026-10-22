# nyc-taxi-cab
NYC Taxi Cab Data Science Project for UB 587

# NYC Yellow Taxi Trip Analysis

EAS 587 - Data-Intensive Computing
Phase 2: Data Cleaning, Processing, and Exploratory Data Analysis

## Project Overview

This project analyzes NYC Yellow Taxi trip data, with support for High Volume For-Hire Vehicle (rideshare: Uber/Lyft) trip data as well.

For Phase 2, we processed the full 2025 year across both datasets:
- Profiled the raw files
- Cleaned invalid and extreme records
- Created analysis-ready features
- Performed exploratory data analysis (EDA)
- Produced first analytics results
- Generated visualizations for major findings

The Yellow Taxi dataset originally contained 48,722,602 records across 12 files (January-December 2025). After cleaning, 44,025,133 records remained, removing 4,697,469 records (9.64%).

The rideshare dataset originally contained 243,589,684 records across 12 files (January-December 2025). After cleaning, 243,513,002 records remained, removing 76,682 records (0.03%).

The pipeline can process Yellow Taxi data, rideshare data, or both, through command-line arguments.

## Project Structure

```text
nyc-taxi-cab/
├── data/
│   ├── raw/
│   │   ├── yellow/
│   │   │   └── yellow_tripdata_2025-01.parquet
│   │   └── rideshare/
│   │       └── fhvhv_tripdata_2025-01.parquet
│   ├── reference/
│   │   └── taxi_zone_lookup.csv
│   ├── profiles/
│   │   ├── yellow_cab_profile.parquet
│   │   └── rideshare_profile.parquet
│   ├── processed/
│   │   ├── yellow/
│   │   │   └── yellow_tripdata_2025-01_clean.parquet
│   │   └── rideshare/
│   │       └── fhvhv_tripdata_2025-01_clean.parquet
│   ├── analytics/
│   │   ├── yellow/
│   │   └── rideshare/
│   ├── cleaning_results_yellow.txt
│   ├── cleaning_results_rideshare.txt
│   ├── analytics_results_yellow.txt
│   └── analytics_results_rideshare.txt
├── figures/
├── notebooks/
│   └── phase2_analysis.ipynb
├── src/
│   ├── analytics.py
│   ├── data_access.py
│   ├── data_cleaning.py
│   ├── data_profile.py
│   ├── data_sampling.py
│   └── pipeline.py
├── Phase_1_Report.pdf
├── phase2_report.md
├── requirements.txt
├── .gitignore
└── README.md
```

## Dataset

Dataset: NYC Yellow Taxi Trip Records and High Volume For-Hire Vehicle (rideshare) Trip Records
Period: 2025

The raw dataset is not included in the GitHub repository because of its size.

Raw files can be downloaded automatically by passing `--download_files` to the pipeline (see below), or downloaded manually from the NYC Taxi & Limousine Commission Trip Record Data page.

Place manually downloaded files here:

```text
data/raw/yellow/yellow_tripdata_2025-01.parquet
data/raw/rideshare/fhvhv_tripdata_2025-01.parquet
```

The years that are downloaded and processed are controlled by the `YEARS` list in `src/data_access.py`, currently set to 2025.

## Environment Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it in Git Bash on Windows:

```bash
source .venv/Scripts/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Recommended Entry Point

Run the main Phase 2 processing pipeline with:

```bash
python src/pipeline.py --yellow_taxi
```

`pipeline.py` accepts the following arguments:

| Argument | Description |
| --- | --- |
| `--download_files` | Download raw files before running the pipeline |
| `--yellow_taxi` | Process yellow taxi data |
| `--rideshare` | Process rideshare (FHVHV) data |
| `--delete_raw` | Delete each raw file once its processed/cleaned file has been written |

At least one of `--yellow_taxi` or `--rideshare` must be passed. For example:

```bash
python src/pipeline.py --yellow_taxi --rideshare --download_files
python src/pipeline.py --rideshare --delete_raw
```

The pipeline downloads raw files if requested, then runs profiling, cleaning, and analytics in sequence for each selected dataset.

## Running the Project

### 1. (Optional) Download Raw Files

```bash
python src/data_access.py
```

This scrapes the NYC TLC Trip Record Data page for the years configured in `YEARS` (currently 2025), and downloads the matching Yellow Taxi parquet files along with the taxi zone lookup table into `data/raw/yellow/` and `data/reference/`. This step also runs automatically when `--download_files` is passed to `pipeline.py`.

### 2. Profile the Raw Data

```bash
python src/data_profile.py
```

This checks schema, missing values, unique values, duplicates, numeric distributions (including p25/median/p75/p90/p95/p99), and potential data quality issues, for each raw file found in `data/raw/yellow/` or `data/raw/rideshare/`. Results are saved to:

```text
data/profiles/yellow_cab_profile.parquet
data/profiles/rideshare_profile.parquet
```

### 3. Clean and Process the Data

```bash
python src/data_cleaning.py
```

Each raw file is cleaned and saved to:

```text
data/processed/yellow/yellow_tripdata_2025-01_clean.parquet
data/processed/rideshare/fhvhv_tripdata_2025-01_clean.parquet
```

Main cleaning rules:
- Pickup date restricted to each file's own year-month
- Trip distance > 0 and <= 120 miles
- Trip duration between 1 and 360 minutes
- Fare amount between $0 and $1,000
- Total amount between $0 and $1,000 (yellow taxi only)
- Dropoff time must be later than pickup time
- Rideshare trips are restricted to Uber (HV0003) and Lyft (HV0005)

A per-file cleaning summary, including counts of why rows were removed, is written to `data/cleaning_results_yellow.txt` and `data/cleaning_results_rideshare.txt`.

### 4. Run Analytics

```bash
python src/analytics.py
```

The analytics include year-by-year summaries, hourly demand, weekday demand, payment or company summaries, distance groups, pickup/dropoff activity by location, passenger counts, and correlations. Results are written to `data/analytics_results_yellow.txt` and `data/analytics_results_rideshare.txt`, with each individual table also saved as its own Parquet file under:

```text
data/analytics/yellow/
data/analytics/rideshare/
```

## Scalable Processing

The project uses Polars and Parquet files for scalable processing. Polars lazy scanning is used during profiling, cleaning, and analytics so transformations can be optimized before execution. The pipeline is driven by command-line arguments so it can scale to additional years or datasets (yellow taxi and/or rideshare) without changing the underlying scripts.

## Phase 2 Results

### Yellow Taxi (2025, 12 files)
- Original records: 48,722,602
- Cleaned records: 44,025,133
- Removed records: 4,697,469
- Removed: 9.64%
- Average trip distance: approximately 3.50 miles
- Average trip duration: approximately 17.28 minutes
- Average fare: approximately $19.97

### Rideshare (2025, 12 files)
- Original records: 243,589,684
- Cleaned records: 243,513,002
- Removed records: 76,682
- Removed: 0.03%
- Average trip distance: approximately 5.03 miles
- Average trip duration: approximately 19.87 minutes
- Average base passenger fare: approximately $26.94

Across both datasets:
- Demand is lowest during early morning hours
- Demand is highest during late afternoon and early evening
- Trip distance and fare amount have a strong positive relationship

See the full analysis in:

```text
phase2_report.md
```

## Reproducibility

Random sampling uses a fixed seed of 42.

The Phase 2 notebook has been tested using Run All without errors.

Before final submission, the complete workflow should also be tested in a fresh environment or on another team member's machine.

## Requirements

Major Python packages include:
- Polars
- Pandas
- PyArrow
- Matplotlib
- Jupyter

Install all dependencies using:

```bash
python -m pip install -r requirements.txt
```
