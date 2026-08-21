"""
discover_companies.py

Searches Adzuna's job listings for software-related roles, extracts
unique company names + job links, and appends any NEW companies
(not already in companies.json) to that file.

Requires environment variables:
  ADZUNA_APP_ID
  ADZUNA_APP_KEY
"""

import os
import json
import time
import requests

APP_ID = os.environ.get("ADZUNA_APP_ID")
APP_KEY = os.environ.get("ADZUNA_APP_KEY")

COMPANIES_FILE = "companies.json"

# Adjust or expand this list of search terms as you like
SEARCH_TERMS = [
    "software engineer",
    "backend developer",
    "full stack developer",
    "frontend developer",
    "qa automation engineer",
    "sdet",
]

COUNTRY = "us"           # Adzuna country code (us, gb, in, etc.)
RESULTS_PER_PAGE = 50    # max allowed by Adzuna is 50
PAGES_PER_TERM = 1       # increase cautiously -- costs more API calls


def load_existing_companies():
    if not os.path.exists(COMPANIES_FILE):
        return []
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_companies(companies):
    with open(COMPANIES_FILE, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)


def fetch_adzuna_results(query, page):
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": query,
        "results_per_page": RESULTS_PER_PAGE,
        "content-type": "application/json",
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("results", [])


def main():
    if not APP_ID or not APP_KEY:
        raise SystemExit("Missing ADZUNA_APP_ID or ADZUNA_APP_KEY environment variables.")

    existing = load_existing_companies()
    existing_names_lower = {c["name"].strip().lower() for c in existing if c.get("name")}

    new_companies = {}  # name -> {"name":..., "url":...}, deduped within this run too

    for term in SEARCH_TERMS:
        for page in range(1, PAGES_PER_TERM + 1):
            try:
                results = fetch_adzuna_results(term, page)
            except requests.RequestException as e:
                print(f"Error fetching '{term}' page {page}: {e}")
                continue

            for job in results:
                company_info = job.get("company", {})
                name = company_info.get("display_name", "").strip()
                url = job.get("redirect_url", "").strip()

                if not name or not url:
                    continue

                name_lower = name.lower()

                # Skip if already tracked, or already queued this run
                if name_lower in existing_names_lower or name_lower in new_companies:
                    continue

                new_companies[name_lower] = {"name": name, "url": url}

            # Be polite to the API / respect rate limits
            time.sleep(1)

    if not new_companies:
        print("No new companies found this run.")
        return

    updated = existing + list(new_companies.values())
    save_companies(updated)

    print(f"Added {len(new_companies)} new companies:")
    for c in new_companies.values():
        print(f"  - {c['name']}")


if __name__ == "__main__":
    main()
