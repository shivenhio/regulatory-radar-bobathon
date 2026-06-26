"""
fetch_utils.py — Shared HTTP helpers for regulatory source fetching.

Used by live_rules_fetcher.py.  The canonical cache schema is defined
in live_rules_fetcher.py (rules_cache/*.json with an 'obligations' array).
"""

import json

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RegulatoryRadar/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_url(url, timeout=20):
    """GET a URL and return the response text, or None on failure."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            print(f"  Fetched: {url}")
            return r.text
        else:
            print(f"  HTTP {r.status_code}: {url}")
            return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def save_rule(rule, filename):
    """Write a rule dict as JSON to rules_cache/<filename>."""
    path = f"rules_cache/{filename}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rule, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")