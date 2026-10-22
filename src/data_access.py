import re
import requests

from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

YEARS = ['2025']

YELLOW_RAW_DIR = Path('data/raw/yellow')
RIDESHARE_RAW_DIR = Path('data/raw/rideshare')
REFERENCE_DIR = Path('data/reference')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

WEBSITE = 'https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page'
LINK_PATTERN_YELLOW = re.compile(r'yellow_tripdata_\d{4}-\d{2}\.parquet$')
LINK_PATTERN_RIDESHARE = re.compile(r'fhvhv_tripdata_\d{4}-\d{2}\.parquet$')
ZONE_LOOKUP_LINK_TEXT = 'Taxi Zone Lookup Table'

def find_links(pattern, website=WEBSITE):
    response = requests.get(website, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    links = {}
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if pattern.search(href):
            month = re.search(r'(\d{4}-\d{2})', href).group(1)
            links[month] = urljoin(website, href)

    return links

def find_zone_lookup_link(website=WEBSITE):
    response = requests.get(website, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    for a in soup.find_all('a', href=True):
        if a.get_text(strip=True) == ZONE_LOOKUP_LINK_TEXT:
            return urljoin(website, a['href'].strip())

    return None

def download_file(url, dest):
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    dest.write_bytes(response.content)

def download_years(links, years, raw_dir):
    raw_dir.mkdir(parents=True, exist_ok=True)

    for year in years:
        year_links = [url for month, url in links.items() if month.startswith(f'{year}-')]
        for url in year_links:
            name = Path(url).name
            dest = raw_dir / name
            try:
                download_file(url, dest)
            except requests.RequestException as e:
                print(f'FAILED TO DOWNLOAD {name}: {e}')
                continue
            else:
                print(f'DOWNLOAD SUCCESS: {name}')

def download_zone_lookup():
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    url = find_zone_lookup_link()
    dest = REFERENCE_DIR / 'taxi_zone_lookup.csv'
    try:
        download_file(url, dest)
    except requests.RequestException as e:
        print(f'FAILED TO DOWNLOAD {dest.name}: {e}')
    else:
        print(f'DOWNLOAD SUCCESS: {dest.name}')

def main(years=YEARS, yellow=False, rideshare=False):
    if yellow or rideshare:
        download_zone_lookup()

    if yellow:
        links = find_links(LINK_PATTERN_YELLOW)
        if '2019' in years:
            links.pop('2019-01', None)
        download_years(links, years, YELLOW_RAW_DIR)

    if rideshare:
        links = find_links(LINK_PATTERN_RIDESHARE)
        download_years(links, years, RIDESHARE_RAW_DIR)

if __name__ == "__main__":
    main(YEARS, yellow=True)