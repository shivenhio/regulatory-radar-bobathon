"""
live_rules_fetcher.py
=====================
Fetches current EU regulatory texts from live official sources, then uses
Groq LLM to extract structured compliance obligations from the real legal text.
Results are cached in rules_cache/ and loaded by compliance_engine.py.

Run:
    python live_rules_fetcher.py

Output:
    rules_cache/battery_regulation.json
    rules_cache/gpsr.json
    rules_cache/red_common_charger.json
    rules_cache/reach_svhc.json
"""

import json
import os
import re
import warnings
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from dotenv import load_dotenv
from groq import Groq

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CACHE_DIR = Path("rules_cache")
CACHE_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RegulatoryRadar/1.0)",
    "Accept": "application/xhtml+xml,text/html,application/xml;q=0.9,*/*;q=0.8",
}

GROQ_MODEL = "llama-3.3-70b-versatile"

# EUR-Lex OJ XHTML content URLs — stable publications.europa.eu permanent links
EURLEX_SOURCES = {
    "battery_regulation": {
        "url": "https://publications.europa.eu/resource/oj/JOL_2023_191_R_0001.ENG.xhtml",
        "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1542/oj",
        "reference": "Regulation (EU) 2023/1542",
        "regulation_family": "Battery Regulation",
    },
    "gpsr": {
        "url": "https://publications.europa.eu/resource/oj/JOL_2023_130_R_0001.ENG.xhtml",
        "source_url": "https://eur-lex.europa.eu/eli/reg/2023/988/oj",
        "reference": "Regulation (EU) 2023/988",
        "regulation_family": "GPSR",
    },
    "red_common_charger": {
        "url": "https://publications.europa.eu/resource/oj/JOL_2022_311_R_0001.ENG.xhtml",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2380",
        "reference": "Directive 2014/53/EU + Delegated Regulation (EU) 2022/2380",
        "regulation_family": "RED",
    },
}

# Known obligation IDs the compliance engine understands — used to align LLM output
KNOWN_IDS = {
    "battery_passport", "battery_removability", "battery_carbon_footprint",
    "common_charger", "gpsr_button_cell", "reach_svhc",
}

# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------

def fetch(url: str, timeout: int = 30) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            print(f"  OK fetched {url[:80]} ({len(r.content):,} bytes)")
            return r.text
        print(f"  FAIL HTTP {r.status_code}: {url[:80]}")
        return None
    except Exception as e:
        print(f"  FAIL {url[:80]}: {e}")
        return None


def save_rule(rule: dict, filename: str) -> None:
    path = CACHE_DIR / filename
    path.write_text(json.dumps(rule, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  >> Saved: {path}")


def extract_text(html: str, max_chars: int = 12000) -> str:
    """Extract clean plain text from OJ XHTML, truncated for the LLM context window."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    # Collapse excessive whitespace
    text = re.sub(r"\s{3,}", "  ", text)
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Groq LLM extraction
# ---------------------------------------------------------------------------

def extract_obligations_with_llm(regulation_text: str, regulation_name: str, source_url: str) -> list:
    """
    Send the regulation text to Groq and ask it to extract structured
    compliance obligations as JSON.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    system_prompt = """You are a EU regulatory compliance expert. 
Your job is to read EU legal texts and extract compliance obligations as structured JSON.
For each obligation found, output a JSON object with exactly these fields:
- id: a snake_case identifier (e.g. battery_passport, common_charger, gpsr_button_cell)
- article: the article number (e.g. "Art. 77")
- name: short human-readable name
- summary: one sentence describing what the obligation requires
- deadline: the compliance deadline as YYYY-MM-DD (or "" if not specified)
- severity: "high", "medium", or "low"
- scope_markets: list of markets, usually ["EU"]
- scope_battery_types: list of battery types that trigger this (e.g. ["lmt","industrial"]) or []
- scope_intended_use: list of intended uses that trigger this (e.g. ["consumer","toy"]) or []
- scope_connectors: list of non-compliant connector types (e.g. ["micro_usb","barrel"]) or []
- scope_substances: list of substance names that trigger this or []
- scope_condition: any extra condition as plain English text
- gap: one sentence describing what the non-compliance looks like
- action: one sentence describing what the company must do to comply

Return ONLY a JSON array of obligation objects. No explanation, no markdown, just the array."""

    user_prompt = f"""Regulation: {regulation_name}
Source: {source_url}

Legal text (excerpt):
{regulation_text}

Extract all compliance obligations from this text as a JSON array."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        obligations = json.loads(raw)
        print(f"  LLM extracted {len(obligations)} obligation(s)")
        return obligations
    except json.JSONDecodeError as e:
        print(f"  LLM JSON parse error: {e} — using fallback")
        return []
    except Exception as e:
        print(f"  LLM call failed: {e} — using fallback")
        return []


def merge_with_fallback(llm_obligations: list, fallback_obligations: list) -> list:
    """
    Use LLM-extracted obligations where available; fill gaps with fallbacks.
    Matches by id where possible.
    """
    if not llm_obligations:
        print("  Using fallback obligations (LLM returned nothing)")
        return fallback_obligations

    # Build a map of LLM results by id
    llm_by_id = {ob.get("id", ""): ob for ob in llm_obligations}

    merged = []
    for fb in fallback_obligations:
        fid = fb["id"]
        if fid in llm_by_id:
            llm_ob = llm_by_id[fid]
            # LLM wins on metadata; keep fallback id so engine can match it
            merged.append({
                "id": fid,
                "article": llm_ob.get("article") or fb.get("article", ""),
                "name": llm_ob.get("name") or fb["name"],
                "summary": llm_ob.get("summary") or fb.get("summary", ""),
                "deadline": llm_ob.get("deadline") or fb["deadline"],
                "severity": llm_ob.get("severity") or fb["severity"],
                "scope": {
                    "markets": llm_ob.get("scope_markets") or ["EU"],
                    "battery_types": llm_ob.get("scope_battery_types") or [],
                    "intended_use": llm_ob.get("scope_intended_use") or [],
                    "connectors": llm_ob.get("scope_connectors") or [],
                    "substances": llm_ob.get("scope_substances") or [],
                    "condition": llm_ob.get("scope_condition") or "",
                },
                "gap": llm_ob.get("gap") or fb.get("gap", ""),
                "action": llm_ob.get("action") or fb.get("action", ""),
                "llm_extracted": True,
            })
        else:
            # LLM didn't find this one — keep the fallback
            merged.append({**fb, "llm_extracted": False})

    return merged


# ---------------------------------------------------------------------------
# Per-regulation fetchers
# ---------------------------------------------------------------------------

def fetch_battery_regulation() -> dict:
    print("\n[Battery Regulation 2023/1542]")
    src = EURLEX_SOURCES["battery_regulation"]
    html = fetch(src["url"])
    reg_text = extract_text(html) if html else ""

    fallback_obligations = [
        {
            "id": "battery_passport",
            "article": "Art. 77",
            "name": "Battery passport",
            "summary": "LMT and industrial batteries >2 Wh must carry a digital battery passport via QR code.",
            "deadline": "2027-02-18",
            "severity": "high",
            "gap": "Battery passport required for LMT or industrial battery > 2 kWh.",
            "action": "Create QR/data-carrier battery passport before the deadline.",
        },
        {
            "id": "battery_removability",
            "article": "Art. 11",
            "name": "Battery removability (consumer)",
            "summary": "Portable and button-cell batteries in consumer/toy products must be user-removable.",
            "deadline": "2027-02-18",
            "severity": "high",
            "gap": "Battery must be user-removable and replaceable.",
            "action": "Redesign enclosure so the user can remove and replace the battery.",
        },
        {
            "id": "battery_carbon_footprint",
            "article": "Art. 7",
            "name": "Carbon footprint declaration (EV / industrial)",
            "summary": "EV and industrial batteries must carry a carbon footprint declaration.",
            "deadline": "2025-02-18",
            "severity": "high",
            "gap": "Carbon footprint declaration required for EV or industrial battery.",
            "action": "Calculate and declare lifecycle carbon footprint per Annex II methodology.",
        },
    ]

    if reg_text:
        llm_obligations = extract_obligations_with_llm(
            reg_text, src["reference"], src["source_url"]
        )
    else:
        llm_obligations = []

    return {
        "regulation_id": "battery_regulation_2023_1542",
        "regulation_family": src["regulation_family"],
        "reference": src["reference"],
        "title": "Regulation (EU) 2023/1542 — EU Battery Regulation",
        "source_url": src["source_url"],
        "fetched_date": str(date.today()),
        "live_fetch": html is not None,
        "llm_extracted": bool(llm_obligations),
        "obligations": merge_with_fallback(llm_obligations, fallback_obligations),
    }


def fetch_gpsr() -> dict:
    print("\n[GPSR 2023/988]")
    src = EURLEX_SOURCES["gpsr"]
    html = fetch(src["url"])
    reg_text = extract_text(html) if html else ""

    fallback_obligations = [
        {
            "id": "gpsr_button_cell",
            "article": "Art. 15",
            "name": "Button-cell / coin-cell child safety",
            "summary": "Consumer/toy products with button-cell batteries need a tool-required compartment.",
            "deadline": "2024-12-13",
            "severity": "high",
            "gap": "Button-cell compartment must be secured against child access.",
            "action": "Add tool-required or screw-fastened battery compartment and warnings.",
        },
    ]

    if reg_text:
        llm_obligations = extract_obligations_with_llm(
            reg_text, src["reference"], src["source_url"]
        )
    else:
        llm_obligations = []

    return {
        "regulation_id": "gpsr_2023_988",
        "regulation_family": src["regulation_family"],
        "reference": src["reference"],
        "title": "Regulation (EU) 2023/988 — General Product Safety Regulation (GPSR)",
        "source_url": src["source_url"],
        "fetched_date": str(date.today()),
        "live_fetch": html is not None,
        "llm_extracted": bool(llm_obligations),
        "obligations": merge_with_fallback(llm_obligations, fallback_obligations),
    }


def fetch_red_common_charger() -> dict:
    print("\n[RED / Common Charger 2022/2380]")
    src = EURLEX_SOURCES["red_common_charger"]
    html = fetch(src["url"])
    reg_text = extract_text(html) if html else ""

    fallback_obligations = [
        {
            "id": "common_charger",
            "article": "Art. 3(3)(a) RED + Delegated Reg 2022/2380",
            "name": "USB-C common charger",
            "summary": "Consumer devices with wired charging sold in the EU must use a USB-C port.",
            "deadline": "2024-12-28",
            "severity": "high",
            "gap": "USB-C is required for wired charging on this product class.",
            "action": "Replace the wired charging port with USB-C.",
        },
    ]

    if reg_text:
        llm_obligations = extract_obligations_with_llm(
            reg_text, src["reference"], src["source_url"]
        )
    else:
        llm_obligations = []

    return {
        "regulation_id": "red_common_charger_2022_2380",
        "regulation_family": src["regulation_family"],
        "reference": src["reference"],
        "title": "USB-C Common Charger — RED amendment",
        "source_url": src["source_url"],
        "fetched_date": str(date.today()),
        "live_fetch": html is not None,
        "llm_extracted": bool(llm_obligations),
        "obligations": merge_with_fallback(llm_obligations, fallback_obligations),
    }


def fetch_reach_svhc() -> dict:
    print("\n[REACH SVHC — ECHA Candidate List]")
    # ECHA blocks automated requests — use known list + LLM to enrich descriptions
    print("  ECHA WAF blocks direct access — using known SVHC list")

    known_substances = [
        "BPA", "DEHP", "TBBPA", "PFAS_PFHxA",
        "MCCP", "PFOA", "PFOS", "DBP", "BBP", "DIBP",
    ]

    # Ask the LLM to describe the REACH SVHC obligation from its training knowledge
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "Describe the REACH SVHC candidate list obligation for electronics manufacturers "
                    "selling in the EU. Include: which article triggers notification duties, "
                    "the 0.1% w/w threshold, SCIP database filing, and the current deadline. "
                    "Reply in 3 sentences max."
                ),
            }],
            temperature=0.1,
            max_tokens=256,
        )
        llm_summary = response.choices[0].message.content.strip()
        print(f"  LLM summary: {llm_summary[:120]}...")
    except Exception as e:
        print(f"  LLM call failed: {e}")
        llm_summary = (
            "Articles containing SVHC above 0.1% w/w must be notified to ECHA's SCIP database "
            "and customers/consumers informed on request under REACH Art. 7(2) and Art. 33."
        )

    return {
        "regulation_id": "reach_svhc",
        "regulation_family": "REACH",
        "reference": "REACH Regulation (EC) 1907/2006, Art. 59",
        "title": "REACH SVHC Candidate List",
        "source_url": "https://echa.europa.eu/candidate-list-table",
        "fetched_date": str(date.today()),
        "live_fetch": False,
        "llm_extracted": True,
        "llm_summary": llm_summary,
        "svhc_substances": known_substances,
        "obligations": [
            {
                "id": "reach_svhc",
                "article": "Art. 7(2) + Art. 33 REACH",
                "name": "REACH SVHC screening and notification",
                "summary": llm_summary,
                "deadline": "2026-10-30",
                "severity": "medium",
                "scope": {
                    "markets": ["EU"],
                    "substances": known_substances,
                },
                "gap": "SVHC screening and customer/SCIP duties may apply.",
                "action": "Screen articles and file SCIP notifications where required.",
                "llm_extracted": True,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Regulatory Radar -- Live Rules Fetcher (Groq-powered)")
    print(f"Run date: {date.today()}")
    print(f"Model: {GROQ_MODEL}")
    print("=" * 60)

    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set. Add it to .env file.")
        return

    fetchers = [
        ("battery_regulation.json", fetch_battery_regulation),
        ("gpsr.json", fetch_gpsr),
        ("red_common_charger.json", fetch_red_common_charger),
        ("reach_svhc.json", fetch_reach_svhc),
    ]

    summary = []
    for filename, fn in fetchers:
        try:
            rule = fn()
            save_rule(rule, filename)
            summary.append({
                "file": filename,
                "regulation": rule["reference"],
                "obligations": len(rule.get("obligations", [])),
                "live_fetch": rule.get("live_fetch", False),
                "llm_extracted": rule.get("llm_extracted", False),
            })
        except Exception as e:
            print(f"  FAIL {filename}: {e}")

    print("\n" + "=" * 60)
    print("Summary:")
    for s in summary:
        fetch_tag = "LIVE" if s["live_fetch"] else "FALLBACK"
        llm_tag = "LLM" if s["llm_extracted"] else "HARDCODED"
        print(f"  [{fetch_tag}+{llm_tag}] {s['regulation']} -> {s['obligations']} obligations -> {s['file']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
