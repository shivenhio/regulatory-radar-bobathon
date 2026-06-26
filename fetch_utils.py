import requests
import json
from datetime import date

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RegulatoryRadar/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_url(url, timeout=20):
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
    path = f"rules_cache/{filename}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rule, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")


def rule_template(update_id):
    return {
        "update_id": update_id,
        "regulation_family": "",
        "reference": "",
        "title": "",
        "summary": "",
        "deadline_date": "",
        "severity": "",
        "action_required": "",
        "source_url": "",
        "fetched_date": str(date.today()),
        "scope": {
            "categories": [],
            "substances": [],
            "conditions": ""
        }
    }