"""
Web Scraping - Website Data Extraction and Dataset Creation
===========================================================
Target Website: https://books.toscrape.com/
Purpose:
    Automatically extract book catalog records across multiple pages using
    Requests and BeautifulSoup, clean the data with Pandas, and save a
    structured CSV dataset to data/scraped_data.csv.

Note on Ethics:
    https://books.toscrape.com/ is a public sandbox built specifically for
    practicing web scraping. This script still checks robots.txt, identifies
    itself with a User-Agent header, and pauses politely between requests.
"""

import os
import re
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# 1. Configuration Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
MAX_PAGES = 5                 # Number of pages to scrape (20 books per page)
REQUEST_TIMEOUT = 10          # Seconds to wait before timing out an HTTP request
RATE_LIMIT_SECONDS = 1.0      # Polite delay between page requests
GBP_TO_INR_RATE = 105.0       # Conversion rate from scraped GBP price to Indian Rupees (INR)
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "scraped_data.csv")

HEADERS = {
    "User-Agent": (
        "StudentDataAnalyticsScraper/1.0 "
        "(Educational Python Project; +https://books.toscrape.com/)"
    )
}

# Maps CSS star-rating class names to numeric integer ratings
RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


# ---------------------------------------------------------------------------
# 2. Ethics & robots.txt Verification
# ---------------------------------------------------------------------------
def is_scraping_allowed(base_url: str, target_url: str, user_agent: str) -> bool:
    """
    Fetch and parse robots.txt to verify automated access is permitted.
    If robots.txt returns HTTP 404 (not present), standard crawling rules allow access.
    """
    robots_url = urljoin(base_url, "robots.txt")
    parser = RobotFileParser()

    try:
        response = requests.get(robots_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            allowed = parser.can_fetch(user_agent, target_url)
            print(f"[robots.txt] Checked {robots_url} -> Allowed: {allowed}")
            return allowed
        if response.status_code in (401, 403):
            print(f"[robots.txt] Access restricted (HTTP {response.status_code}).")
            return False

        print(
            f"[robots.txt] No robots.txt found (HTTP {response.status_code}). "
            "Proceeding politely with rate limiting."
        )
        return True
    except requests.exceptions.RequestException as exc:
        print(f"[robots.txt] Could not reach robots.txt ({exc}). Stopping safely.")
        return False


# ---------------------------------------------------------------------------
# 3. Safe HTML Extraction Helpers
# ---------------------------------------------------------------------------
def fetch_page(url: str) -> BeautifulSoup | None:
    """Download a webpage and return a BeautifulSoup object, or None on failure."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        # Ensure UTF-8 decoding so currency symbols (like £) stay intact
        response.encoding = "utf-8"
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.HTTPError as exc:
        print(f"[HTTP Error] Failed to load {url}: {exc}")
    except requests.exceptions.ConnectionError:
        print(f"[Connection Error] Could not connect to {url}. Check your internet.")
    except requests.exceptions.Timeout:
        print(f"[Timeout] Request to {url} exceeded {REQUEST_TIMEOUT}s.")
    except requests.exceptions.RequestException as exc:
        print(f"[Request Error] Unexpected error for {url}: {exc}")
    return None


def safe_extract_rating(article_tag) -> int | None:
    """Extract star rating (1 to 5) from the <p class='star-rating ...'> element."""
    rating_tag = article_tag.select_one("p.star-rating")
    if not rating_tag:
        return None
    for class_name in rating_tag.get("class", []):
        if class_name in RATING_MAP:
            return RATING_MAP[class_name]
    return None


def parse_books_from_page(soup: BeautifulSoup, page_url: str, page_number: int) -> list[dict]:
    """
    Parse all book cards (<article class='product_pod'>) from a catalog page.
    Handles missing or unavailable HTML elements gracefully.
    """
    records = []
    book_cards = soup.select("article.product_pod")

    if not book_cards:
        print(f"[Warning] No book elements found on page {page_number}.")
        return records

    for card in book_cards:
        # 1. Book Title and Product URL
        title_link = card.select_one("h3 a")
        if title_link:
            title = title_link.get("title") or title_link.get_text(strip=True)
            relative_href = title_link.get("href", "")
            product_url = urljoin(page_url, relative_href) if relative_href else None
        else:
            title = None
            product_url = None

        # 2. Price (raw text e.g. '£51.77')
        price_tag = card.select_one("p.price_color")
        raw_price = price_tag.get_text(strip=True) if price_tag else None

        # 3. Stock Availability
        stock_tag = card.select_one("p.instock.availability")
        availability = stock_tag.get_text(" ", strip=True) if stock_tag else None

        # 4. Star Rating (1-5)
        rating = safe_extract_rating(card)

        records.append(
            {
                "title": title,
                "price_raw": raw_price,
                "rating": rating,
                "availability": availability,
                "source_page": page_number,
                "product_url": product_url,
            }
        )

    return records


def find_next_page_url(soup: BeautifulSoup, current_url: str) -> str | None:
    """Find the pagination 'next' link (<li class='next'><a href='...'>) if present."""
    next_link = soup.select_one("ul.pager li.next a")
    if next_link and next_link.get("href"):
        return urljoin(current_url, next_link["href"])
    return None


# ---------------------------------------------------------------------------
# 4. Web Navigation & Multi-Page Scraping
# ---------------------------------------------------------------------------
def scrape_books(start_url: str, max_pages: int) -> list[dict]:
    """Navigate through paginated catalog pages and collect raw book records."""
    all_records: list[dict] = []
    current_url: str | None = start_url
    page_number = 1

    while current_url and page_number <= max_pages:
        print(f"[Scraping] Page {page_number}/{max_pages}: {current_url}")
        soup = fetch_page(current_url)
        if soup is None:
            print(f"[Stopped] Halting pagination due to fetch failure on page {page_number}.")
            break

        page_records = parse_books_from_page(soup, current_url, page_number)
        all_records.extend(page_records)
        print(f"           Extracted {len(page_records)} records (Total so far: {len(all_records)})")

        # Locate next page URL via HTML pagination element
        next_url = find_next_page_url(soup, current_url)
        if not next_url:
            print("[Pagination] Reached last available page.")
            break

        current_url = next_url
        page_number += 1

        # Polite delay before requesting the next page
        if page_number <= max_pages:
            time.sleep(RATE_LIMIT_SECONDS)

    return all_records


# ---------------------------------------------------------------------------
# 5. Data Cleaning & Dataset Creation with Pandas
# ---------------------------------------------------------------------------
def clean_and_build_dataset(raw_records: list[dict]) -> pd.DataFrame:
    """
    Convert raw scraped dictionaries into a clean, analysis-ready DataFrame:
      - Trim whitespace and standardize text fields
      - Parse numeric prices (float) from currency strings
      - Create a boolean 'in_stock' column
      - Handle missing values appropriately
      - Remove duplicate records
      - Enforce clean column types
    """
    df = pd.DataFrame(raw_records)

    if df.empty:
        return df

    # Strip extra whitespace from text columns
    df["title"] = df["title"].fillna("Unknown Title").astype(str).str.strip()
    df["availability"] = (
        df["availability"].fillna("Unknown").astype(str).str.strip()
    )
    df["product_url"] = df["product_url"].fillna("").astype(str).str.strip()

    # Extract numeric source price and convert to Indian Rupees (INR)
    def parse_price_inr(value) -> float | None:
        if pd.isna(value):
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", str(value))
        if not match:
            return None
        return round(float(match.group(1)) * GBP_TO_INR_RATE, 2)

    df["price_inr"] = df["price_raw"].apply(parse_price_inr)

    # Fill any missing numeric prices with the median INR price (if available)
    if df["price_inr"].isna().any():
        median_price = df["price_inr"].median()
        df["price_inr"] = df["price_inr"].fillna(
            round(float(median_price), 2) if pd.notna(median_price) else 0.0
        )

    # Fill missing ratings with 0 (unrated) and cast to integer
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0).astype(int)

    # Derive clean boolean stock column
    df["in_stock"] = df["availability"].str.contains("in stock", case=False, na=False)

    # Ensure source_page is an integer
    df["source_page"] = pd.to_numeric(df["source_page"], errors="coerce").fillna(0).astype(int)

    # Remove duplicate books (by title and product_url)
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["title", "product_url"]).reset_index(drop=True)
    duplicates_removed = before_dedup - len(df)
    if duplicates_removed > 0:
        print(f"[Cleaning] Removed {duplicates_removed} duplicate record(s).")

    # Select and order final dataset columns
    final_columns = [
        "title",
        "price_inr",
        "rating",
        "in_stock",
        "availability",
        "source_page",
        "product_url",
    ]
    df = df[final_columns]

    return df


def save_dataset(df: pd.DataFrame, output_path: str) -> None:
    """Save the cleaned DataFrame to a CSV file, creating the output folder if needed."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # utf-8-sig ensures Excel on Windows displays symbols cleanly
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[Saved] Dataset written successfully to: {output_path}")


def format_indian_rupees(amount: float) -> str:
    """Format a number in Indian Rupee (₹) style with 2,2,3 lakh/crore grouping."""
    negative = amount < 0
    integer_part, decimal_part = f"{abs(amount):.2f}".split(".")
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_int = ",".join(groups) + "," + last_three
    else:
        formatted_int = integer_part
    prefix = "-₹" if negative else "₹"
    return f"{prefix}{formatted_int}.{decimal_part}"


def print_dataset_summary(df: pd.DataFrame) -> None:
    """Display record counts, sample rows, and basic analytics summary in INR."""
    print("\n" + "=" * 65)
    print("SCRAPING & DATASET SUMMARY")
    print("=" * 65)
    print(f"Total Records Collected : {len(df)}")
    print(f"Total Columns           : {len(df.columns)}")
    print(f"Columns                 : {', '.join(df.columns)}")
    print(f"Missing Values (Total)  : {int(df.isna().sum().sum())}")
    print(f"Duplicate Rows          : {int(df.duplicated().sum())}")

    if not df.empty:
        print(f"Total Catalog Value     : {format_indian_rupees(df['price_inr'].sum())}")
        print(f"Average Price (INR)     : {format_indian_rupees(df['price_inr'].mean())}")
        print(
            f"Min / Max Price (INR)   : {format_indian_rupees(df['price_inr'].min())} / "
            f"{format_indian_rupees(df['price_inr'].max())}"
        )
        print(f"Books In Stock          : {int(df['in_stock'].sum())} / {len(df)}")
        print(f"Average Star Rating     : {df['rating'].mean():.2f} / 5")

        print("\n--- Rating Distribution ---")
        rating_counts = df["rating"].value_counts().sort_index()
        for stars, count in rating_counts.items():
            print(f"  {stars} Star(s): {count} book(s)")

        print("\n--- Sample Scraped Records (First 5 Rows) ---")
        sample_df = df[["title", "price_inr", "rating", "in_stock", "source_page"]].head(5).copy()
        sample_df["price_inr"] = sample_df["price_inr"].apply(format_indian_rupees)
        print(sample_df.to_string(index=False))

    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# 6. Main Entry Point
# ---------------------------------------------------------------------------
def main() -> None:
    print("Starting Web Scraping Pipeline...")
    print(f"Target Site: {BASE_URL}\n")

    # Step 1: Respect robots.txt
    if not is_scraping_allowed(BASE_URL, START_URL, HEADERS["User-Agent"]):
        print("Scraping halted because access is disallowed or site is unreachable.")
        return

    # Step 2: Scrape multiple pages
    raw_records = scrape_books(START_URL, MAX_PAGES)
    if not raw_records:
        print("No records were scraped. Exiting without overwriting dataset.")
        return

    # Step 3: Clean data and create DataFrame
    cleaned_df = clean_and_build_dataset(raw_records)

    # Step 4: Save to CSV
    save_dataset(cleaned_df, OUTPUT_FILE)

    # Step 5: Print summary output
    print_dataset_summary(cleaned_df)


if __name__ == "__main__":
    main()
