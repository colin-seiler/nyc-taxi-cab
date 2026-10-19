import re
import requests

from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

YEARS = ['2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']

RAW_DIR = Path('data/raw')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

WEBSITE = 'https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page'
LINK_PATTERN = re.compile(r'yellow_tripdata_\d{4}-\d{2}\.parquet$')

def find_yellow_taxi_links(website=WEBSITE):
    response = requests.get(website, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    links = {}
    for a in soup.find_all('a', href=True):
        href = a['href']
        if LINK_PATTERN.search(href):
            month = re.search(r'(\d{4}-\d{2})', href).group(1)
            links[month] = urljoin(website, href)

    return links

def download_file(url, dest):
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    dest.write_bytes(response.content)

def main(years=['2025']):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    links = find_yellow_taxi_links()

    for year in years:
        year_links = [url for month, url in links.items() if month.startswith(f'{year}-')]
        for url in year_links:
            name = Path(url).name
            dest = RAW_DIR / name
            try:
                download_file(url, dest)
            except requests.RequestException as e:
                print(f'FAILED TO DOWNLOAD {name}: {e}')
                continue
            else:
                print(f'DOWNLOAD SUCCESS: {name}')

if __name__ == "__main__":
    main(YEARS)