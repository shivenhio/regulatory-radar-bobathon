#!/usr/bin/env python3
"""
starter.py - a runnable scaffold for the Regulatory Radar challenge.

The loop you build:
    1. FIND   current EU requirements from live sources   (see SOURCES.md)   -> fetch_requirements()
    2. UNDERSTAND each requirement (use IBM Bob)                              -> (your extraction)
    3. ASSESS  the portfolio for gaps                                         -> find_gaps()
    4. ALERT   each company about its gaps (Twilio)                           -> make_alert()

This scaffold runs OFFLINE: fetch_requirements() falls back to the local sample feed so you have
something to develop against immediately. Your real job is to make step 1 pull LIVE data and step 3
genuinely assess compliance. Search for "TODO".

Run:  python3 starter.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- the portfolio: your fixed dataset --------------------------------------
partners = json.loads((HERE / "partners.json").read_text())["partners"]
products = [{**pr, "partner_id": pt["partner_id"], "company": pt["company"],
            "contact": pt["contact"], "compliance_status": pt.get("compliance_status")}
           for pt in partners for pr in pt["products"]]
print(f"Loaded {len(partners)} companies, {len(products)} products.\n")

EU_MEMBERS = {"AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE",
              "IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"}

def expand(markets):
    s = set()
    for m in markets:
        s.update(EU_MEMBERS if m == "EU" else {m})
    return s

def market_overlap(a, b):
    return bool(expand(a) & expand(b))

# ---- Step 1: FIND current requirements --------------------------------------
def fetch_requirements():
    """Return a list of current requirements: {regulation, requirement, categories,
    substances, markets, deadline, source_url}.

    TODO: replace this with LIVE retrieval from the sources in SOURCES.md
          (EUR-Lex / ECHA / EPREL / national registers). Prefer official APIs/RSS,
          respect rate limits, and keep the source_url for every requirement.
    For now it FALLS BACK to the offline sample feed so the scaffold runs.
    """
    feed = json.loads((HERE / "regulatory_updates.json").read_text())["updates"]
    reqs = []
    for u in feed:
        sc = u.get("scope", {})
        reqs.append({
            "regulation": u.get("regulation_family"),
            "title": u.get("title"),
            "requirement": u.get("summary"),
            "categories": sc.get("categories", "all"),
            "substances": sc.get("substances", []),
            "markets": sc.get("markets", ["EU"]),
            "deadline": u.get("deadline_date"),
            "severity": u.get("severity"),
            "source_url": "(offline sample feed - replace with the live source URL)",
            "corrects": u.get("corrects"),
        })
    print(f"[fetch_requirements] OFFLINE FALLBACK: loaded {len(reqs)} sample requirements.")
    print("  -> Make this pull LIVE rules from SOURCES.md for the real challenge.\n")
    return reqs

# ---- Step 3: ASSESS the portfolio for gaps ----------------------------------
def find_gaps(product, requirements):
    """Naive baseline: flag a requirement as a POSSIBLE gap when it plausibly applies to the product.

    It only checks market + category + substance, and cannot tell whether the company has ALREADY
    complied. Improve it:
      TODO(1): check attribute conditions (battery type/capacity, has_radio, connector, intended use,
               packaging) so you stop over-firing on look-alikes.
      TODO(2): skip irrelevant-domain requirements and de-duplicate (see the `corrects` field).
      TODO(3): actually decide compliance - use `compliance_status` where present, and reason about
               the rest instead of assuming every applicable rule is an open gap.
    """
    gaps = []
    for r in requirements:
        cats = r["categories"]
        if isinstance(cats, list) and product["category"] not in cats:
            continue
        if r["substances"] and not (set(product["substances"]) & set(r["substances"])):
            continue
        if not market_overlap(product["markets"], r["markets"]):
            continue
        gaps.append(r)
    return gaps

# ---- Step 4: ALERT ----------------------------------------------------------
def make_alert(product, finding):
    ch = product["contact"]["preferred_channel"].upper()
    return (f"[{ch} -> {product['contact']['email']}] {product['company']}: "
            f"'{finding['title']}' may apply to your '{product['product_id']}'. "
            f"Deadline {finding['deadline']}. Source: {finding['source_url']}")
    # TODO: replace with a real Twilio send to YOUR OWN test number/email.

if __name__ == "__main__":
    reqs = fetch_requirements()

    # The seeded companies have concrete, verifiable current gaps - guaranteed demo wins.
    print("Companies with explicit known gaps (verify these against live sources):")
    for pt in partners:
        cs = pt.get("compliance_status")
        if cs and cs.get("known_gaps"):
            for g in cs["known_gaps"]:
                print(f"  - {pt['company']}: {g}")
    print()

    # Naive baseline assessment across the portfolio.
    total = sum(len(find_gaps(p, reqs)) for p in products)
    print(f"Naive baseline flagged {total} possible (product, requirement) pairs.")
    print("(Too many - it assumes every applicable rule is an open gap. Make it real: TODO 1-3.)\n")

    # One example alert.
    for p in products:
        g = find_gaps(p, reqs)
        if g:
            print("Example alert (wire this to Twilio with YOUR test contact):")
            print("  " + make_alert(p, g[0]))
            break
