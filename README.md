# nyc-taxi-cab
NYC Taxi Cab Data Science Project for UB 587

# NYC Yellow Taxi Trip Analysis

EAS 587 - Data-Intensive Computing
Phase 2: Data Cleaning, Processing, and Exploratory Data Analysis

## Project Overview

This project analyzes NYC Yellow Taxi trip data.

For Phase 2, we:
- Profiled the raw dataset
- Cleaned invalid and extreme records
- Created analysis-ready features
- Performed exploratory data analysis (EDA)
- Produced first analytics results
- Generated visualizations for major findings

The January 2025 dataset originally contained 3,475,226 records.
After cleaning, 3,242,213 records remained.

## Project Structure

```text
nyc-taxi-cab/
├── data/
│   ├── raw/
│   │   └── yellow_tripdata_2025-01.parquet
│   ├── processed/
│   │   └── yellow_tripdata_2025-01_clean.parquet
│   └── samples/
│       └── yellow_tripdata_sample.parquet
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

Dataset: NYC Yellow Taxi Trip Records
Period: January 2025

The raw dataset is not included in the GitHub repository because of its size.

Download the January 2025 Yellow Taxi Parquet file from the NYC Taxi & Limousine Commission Trip Record Data page.

Place the file here:

```text
data/raw/yellow_tripdata_2025-01.parquet
```

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
python src/pipeline.py
```

## Running the Project

### 1. Profile the Raw Data

```bash
python src/data_profile.py
```

This checks schema, missing values, unique values, duplicates, numeric distributions, and potential data quality issues.

### 2. Create a Sample Dataset

```bash
python src/data_sampling.py
```

This creates:

```text
data/samples/yellow_tripdata_sample.parquet
```

### 3. Clean and Process the Data

```bash
python src/data_cleaning.py
```

The cleaned dataset is saved to:

```text
data/processed/yellow_tripdata_2025-01_clean.parquet
```

Main cleaning rules:
- January 2025 trips only
- Trip distance > 0 and <= 100 miles
- Trip duration between 1 and 240 minutes
- Fare amount between $0 and $500
- Total amount between $0 and $600
- Dropoff time must be later than pickup time

### 4. Run Analytics

```bash
python src/analytics.py
```

The analytics include hourly demand, weekday demand, daily trip counts, payment summaries, passenger counts, pickup/dropoff activity, distance groups, and correlations.

### 5. Run the EDA Notebook

Open:

```text
notebooks/phase2_analysis.ipynb
```

Run all cells in order. The notebook generates figures in:

```text
figures/
```

## Scalable Processing

The project uses Polars and Parquet files for scalable processing. Polars lazy scanning is used during profiling and processing so transformations can be optimized before execution.

## Phase 2 Results

After cleaning:
- Original records: 3,475,226
- Cleaned records: 3,242,213
- Removed records: 233,013
- Removed: 6.70%

Initial findings:
- Average trip distance: approximately 3.18 miles
- Average trip duration: approximately 14.72 minutes
- Average fare: approximately $17.91
- Taxi demand is lowest during early morning hours
- Taxi demand is highest during late afternoon and early evening
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