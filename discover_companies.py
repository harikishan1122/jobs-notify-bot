"""
discover_companies.py

Reads company names from companies_master.txt, tries common ATS
(Applicant Tracking System) URL patterns for each one, and appends
any that resolve successfully to companies.json (skipping duplicates).

Usage:
    python discover_companies.py

Requires:
    pip install requests

Notes:
- Greenhouse and Lever use predictable URLs, so those are the most
  reliable to auto-detect.
- Workday uses a random subdomain number (wd1, wd5, wd12, etc.) per
  company, so it CANNOT be reliably guessed. Workday companies will
  mostly be skipped unless you find the number manually.
- This does basic existence checking (does the page load without a
  404), not deep content validation. Always spot-check a few new
  entries before trusting them fully.
"""

import json
import re
import time
import requests

MASTER_LIST_FILE = "companies_master.txt"
COMPANIES_JSON_FILE = "companies.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def slugify(name):
    """Turn 'My Company Inc' into 'mycompanyinc' and 'my-company' variants."""
    base = name.strip().lower()
    no_space = re.sub(r"[^a-z0-9]", "", base)
    hyphenated = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return no_space, hyphenated


def try_url(url):
    """Return True if the URL loads successfully (not a 404/error page)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if resp.status_code == 200:
            lowered = resp.text.lower()
            if "page not found" in lowered or "404" in resp.url:
                return False
            return True
        return False
    except requests.RequestException:
        return False


def find_ats_url(company_name):
    """Try Greenhouse and Lever patterns (Workday is not guessable)."""
    slug_plain, slug_hyphen = slugify(company_name)

    candidates = [
        f"https://boards.greenhouse.io/{slug_plain}",
        f"https://boards.greenhouse.io/{slug_hyphen}",
        f"https://jobs.lever.co/{slug_plain}",
        f"https://jobs.lever.co/{slug_hyphen}",
    ]

    for url in candidates:
        if try_url(url):
            return url
    return None


def load_existing_companies():
    try:
        with open(COMPANIES_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_companies(companies):
    with open(COMPANIES_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2)


def main():
    with open(MASTER_LIST_FILE, "r", encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip()]

    existing = load_existing_companies()
    existing_names = {c["name"].strip().lower() for c in existing}

    added = []
    skipped_existing = []
    not_found = []

    for name in names:
        if name.strip().lower() in existing_names:
            skipped_existing.append(name)
            continue

        print(f"Checking: {name} ...")
        url = find_ats_url(name)
        if url:
            entry = {"name": name.title(), "url": url}
            existing.append(entry)
            added.append(name)
            print(f"  FOUND: {url}")
        else:
            not_found.append(name)
            print(f"  not found (skipped)")

        time.sleep(1)

    save_companies(existing)

    print("\n--- Summary ---")
    print(f"Added: {len(added)} -> {added}")
    print(f"Already in companies.json: {len(skipped_existing)}")
    print(f"Not found (likely Workday or unknown ATS): {len(not_found)} -> {not_found}")
    print(f"\nUpdated {COMPANIES_JSON_FILE} with {len(existing)} total companies.")


if __name__ == "__main__":
    main()
