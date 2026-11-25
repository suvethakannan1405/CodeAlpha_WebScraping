# Web Scraping – Website Data Extraction and Dataset Creation

A beginner-friendly, production-structured Python web scraping and data analytics project. It automatically extracts book catalog data from a publicly accessible practice site ([Books to Scrape](https://books.toscrape.com/)), parses HTML elements with **BeautifulSoup**, handles multi-page pagination politely, cleans and structures the records with **Pandas**, and exports an analysis-ready CSV dataset (scraped_data.csv)

---

## Project Objective

Demonstrate the complete end-to-end data collection workflow used in Data Analytics:
1. Checking `robots.txt` and enforcing polite request delays.
2. Fetching live web pages with `requests` and handling HTTP/network errors.
3. Parsing HTML tags, classes, and attributes with `BeautifulSoup`.
4. Navigating across paginated catalog pages automatically.
5. Cleaning, validating, deduplicating, and exporting structured data with `pandas`.

---

## Project Structure

```text
Web_Scraping/
│
├── scraper.py            # Main scraping, cleaning, and CSV export pipeline
├── scraped_data.csv                        # Generated clean dataset (created automatically)
├── requirements.txt      # Required Python packages
├── README.md             # Project documentation and setup guide
└── .gitignore            # Git ignore rules for virtual environments and caches
```

---

## Target Website & HTML Structure

This project uses **[https://books.toscrape.com/](https://books.toscrape.com/)**, an open sandbox built specifically for learning and testing web scrapers without violating terms of service.

| Field Extracted | HTML Element / Selector | Extraction Logic |
| :--- | :--- | :--- |
| `title` | `article.product_pod h3 a` | Reads `title` attribute (fallback to link text) |
| `price_inr` | `article.product_pod p.price_color` | Extracts numeric price, converts to Indian Rupees (`₹`), and formats as `float` |
| `rating` | `article.product_pod p.star-rating` | Maps class (`One`–`Five`) to integer `1`–`5` |
| `availability` | `article.product_pod p.instock.availability` | Strips whitespace into `"In stock"` |
| `in_stock` | Derived from `availability` | Boolean `True` / `False` |
| `source_page` | Pagination loop counter | Page number (`1` to `5`) |
| `product_url` | `article.product_pod h3 a[href]` | Resolved to full URL using `urljoin` |
| Next Page URL | `ul.pager li.next a[href]` | Used for multi-page navigation |

---

## Prerequisites

- **Python 3.10 or higher** ([python.org/downloads](https://www.python.org/downloads/))
- **VS Code** with the official **Python** extension

---

## Installation & Setup (Windows + VS Code)

1. Open the `Web_Scraping` folder in **VS Code** (`File -> Open Folder...`).
2. Open the integrated terminal (`Ctrl + ~`).
3. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
   *(If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt with `venv\Scripts\activate.bat`.)*
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Running the Scraper

Execute the main script from inside `Web_Scraping/`:

```powershell
python scraper.py
```

### Expected Output

```text
Starting Web Scraping Pipeline...
Target Site: https://books.toscrape.com/

[robots.txt] No robots.txt found (HTTP 404). Proceeding politely with rate limiting.
[Scraping] Page 1/5: https://books.toscrape.com/catalogue/page-1.html
           Extracted 20 records (Total so far: 20)
[Scraping] Page 2/5: https://books.toscrape.com/catalogue/page-2.html
           Extracted 20 records (Total so far: 40)
...
[Saved] Dataset written successfully to: data/scraped_data.csv

=================================================================
SCRAPING & DATASET SUMMARY
=================================================================
Total Records Collected : 100
Total Columns           : 7
...
```

---

## Verifying the Generated CSV Dataset

Verify the output in PowerShell or Python:

```powershell
python -c "import pandas as pd; df = pd.read_csv('data/scraped_data.csv'); print(df.info()); print(df.head())"
```

You can also open `data/scraped_data.csv` directly in **VS Code** (or Microsoft Excel) to inspect all 100 rows and 7 clean columns.
