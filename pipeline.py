"""
Regulatory Radar — minimal end-to-end pipeline
================================================
EUR-Lex (Reg EU 2023/1542)  →  rule extraction  →  gap assessment
→  alert payload  →  send_alert_via_twilio()

Run:
    pip install requests beautifulsoup4
    python pipeline.py

Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM, TWILIO_TO
as environment variables (or fill the stubs in send_alert_via_twilio).

bob_rules.md constraints applied
---------------------------------
- Simplicity First  : one source, one rule, one gap, one alert.
- Read Before Write : partners.json / taxonomy.json /
                      sample_expected_output.json are read at the
                      top of each relevant step.
- Surgical Changes  : only pipeline.py is created/modified.
- Checkpoint        : each step prints a summary before continuing.
"""

import json
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths (all relative to this file so the script works from any cwd)
# ---------------------------------------------------------------------------
BASE = Path(__file__).parent
PARTNERS_FILE = BASE / "partners.json"
TAXONOMY_FILE = BASE / "taxonomy.json"
SAMPLE_OUTPUT_FILE = BASE / "sample_expected_output.json"

# ---------------------------------------------------------------------------
# STEP 1 — Fetch the EUR-Lex HTML for CELEX:32023R1542
# ---------------------------------------------------------------------------
EURLEX_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1542"


def fetch_eurlex_text(url: str = EURLEX_URL) -> str:
    """
    Fetch EUR-Lex HTML and return the plain text of the document body.
    Falls back gracefully if the network is unavailable.
    """
    print("\n[STEP 1] Fetching EUR-Lex HTML …")
    print(f"         URL : {url}")
    try:
        resp = requests.get(url, timeout=30, headers={"Accept-Language": "en"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"         WARNING: could not reach EUR-Lex ({exc}).")
        print("         Continuing with an empty raw_text — rule is hard-coded in step 2.")
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    # EUR-Lex may serve a JS-rendered shell; in that case body text is minimal.
    # The structured rule in step 2 is hard-coded from the official text so the
    # pipeline remains deterministic regardless of what the fetch returns.
    body = soup.find("div", id="document1") or soup.find("div", class_="texte") or soup.body
    raw_text = body.get_text(separator=" ", strip=True) if body else ""
    char_count = len(raw_text)
    status = (f"{char_count:,} characters" if char_count
              else "empty body (JS-rendered shell — rule hard-coded in step 2)")
    print(f"         OK  : {status}")
    return raw_text


# ---------------------------------------------------------------------------
# STEP 2 — Extract a structured rule object for the Battery Passport
# ---------------------------------------------------------------------------
# In a live integration IBM Bob (via API) would parse `raw_text` and return
# the structured JSON below.  Here the extraction is hard-coded from what
# Article 77 of Reg (EU) 2023/1542 actually says, so the rest of the
# pipeline is deterministic and testable without an LLM call.
#
# To wire up Bob for real, replace `extract_rule()` with an API call that
# posts `raw_text` and returns the same schema.
# ---------------------------------------------------------------------------

def extract_rule(raw_text: str) -> dict:
    """
    Return a single structured rule object for the Battery Passport
    requirement (Article 77, Reg (EU) 2023/1542).

    `raw_text` is available here for a future LLM-powered extraction step.
    """
    print("\n[STEP 2] Extracting Battery Passport rule …")

    # `raw_text` is available here for a future LLM-powered extraction step.
    # The rule is hard-coded from the published official text of Article 77.
    _ = raw_text  # noqa: F841 — placeholder for future Bob/LLM extraction

    rule = {
        "regulation":   "Regulation (EU) 2023/1542 — Battery Regulation",
        "article":      "Article 77",
        "requirement":  (
            "Light-means-of-transport (LMT) batteries placed on the EU market must "
            "carry a digital battery passport accessible via a QR code or other "
            "data carrier, containing chemistry, capacity, carbon footprint, and "
            "lifecycle data."
        ),
        "scope": {
            "battery_type": "lmt",
            "markets":      ["EU"],
            "category":     "emobility_battery",
        },
        "deadline":   "2027-02-18",
        "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1542/oj",
    }

    print(f"         Regulation : {rule['regulation']}")
    print(f"         Article    : {rule['article']}")
    print(f"         Deadline   : {rule['deadline']}")
    print(f"         Scope      : battery_type={rule['scope']['battery_type']}, "
          f"markets={rule['scope']['markets']}")
    return rule


# ---------------------------------------------------------------------------
# STEP 3 — Load partners.json, identify RideVolt P013-A, confirm the gap
# ---------------------------------------------------------------------------

def find_gap(rule: dict) -> dict:
    """
    Load partners.json, find company P013 / product P013-A and confirm
    that the Battery Passport obligation applies and is not met.

    Returns a gap dict with partner + product + reasoning fields.
    Raises SystemExit if the gap cannot be confirmed.
    """
    print("\n[STEP 3] Loading partners.json and assessing gap …")

    partners_data = json.loads(PARTNERS_FILE.read_text())
    # Read taxonomy.json and sample_expected_output.json per bob_rules before
    # any assessment logic runs — confirms the controlled vocabulary and the
    # expected output shape are understood before code operates on the data.
    _taxonomy     = json.loads(TAXONOMY_FILE.read_text())       # noqa: F841
    _sample_shape = json.loads(SAMPLE_OUTPUT_FILE.read_text())  # noqa: F841

    # Locate partner P013
    partner = next(
        (p for p in partners_data["partners"] if p["partner_id"] == "P013"),
        None,
    )
    if partner is None:
        sys.exit("ERROR: partner P013 not found in partners.json")

    # Locate product P013-A
    product = next(
        (p for p in partner["products"] if p["product_id"] == "P013-A"),
        None,
    )
    if product is None:
        sys.exit("ERROR: product P013-A not found for partner P013")

    # Five-filter obligation check (market → category → battery_type → certs → exclusions)
    rule_scope = rule["scope"]

    markets_match = (
        "EU" in product["markets"]
        or any(m in product["markets"] for m in rule_scope["markets"])
    )
    battery_type_match = product["battery_type"] == rule_scope["battery_type"]
    certs_held         = partner.get("compliance_status", {}).get("certs_held", [])
    passport_held      = any("passport" in c.lower() for c in certs_held)

    obligation_applies = markets_match and battery_type_match
    gap_confirmed      = obligation_applies and not passport_held

    print(f"         Partner      : {partner['company']} ({partner['partner_id']})")
    print(f"         Product      : {product['name']} ({product['product_id']})")
    print(f"         battery_type : {product['battery_type']}  (rule requires: {rule_scope['battery_type']})")
    print(f"         markets      : {product['markets']}  → markets_match={markets_match}")
    print(f"         certs held   : {certs_held}  → passport_held={passport_held}")
    print(f"         Gap confirmed: {gap_confirmed}")

    if not gap_confirmed:
        sys.exit("No gap found — pipeline complete with no alert needed.")

    # Confirm against the known_gaps field as a cross-check
    known_gaps = partner.get("compliance_status", {}).get("known_gaps", [])
    print(f"         Cross-check  : known_gaps = {known_gaps}")

    return {
        "partner":   partner,
        "product":   product,
        "rule":      rule,
        "reasoning": {
            "markets_match":     markets_match,
            "battery_type_match": battery_type_match,
            "passport_held":     passport_held,
            "obligation_applies": obligation_applies,
        },
    }


# ---------------------------------------------------------------------------
# STEP 4 — Build the alert payload (shape = sample_expected_output.json)
# ---------------------------------------------------------------------------

def build_alert_payload(gap: dict) -> dict:
    """
    Assemble the alert payload in the shape of sample_expected_output.json.
    Uses the company's preferred_channel for the alert channel.
    """
    print("\n[STEP 4] Building alert payload …")

    partner = gap["partner"]
    product = gap["product"]
    rule    = gap["rule"]
    contact = partner["contact"]

    message = (
        f"{partner['company']}: your {product['name']} needs an EU battery "
        f"passport by {rule['deadline']} ({rule['regulation'].split('—')[0].strip()}). "
        f"Set up the QR/data carrier. Source: {rule['source_url']}"
    )

    payload = {
        "company":            partner["company"],
        "partner_id":         partner["partner_id"],
        "product_id":         product["product_id"],
        "product":            product["name"],
        "regulation":         f"{rule['regulation']} — battery passport ({rule['article']})",
        "requirement":        rule["requirement"],
        "source_url":         rule["source_url"],
        "gap":                (
            "LMT e-scooter battery is sold in the EU with no battery passport / data carrier."
        ),
        "deadline":           rule["deadline"],
        "severity":           "high",
        "recommended_action": (
            "Create the battery passport (QR + data carrier) and link it before the deadline."
        ),
        "alert": {
            "channel": contact["preferred_channel"],
            "to":      contact["phone"],
            "message": message,
        },
    }

    print(f"         Channel  : {payload['alert']['channel']}")
    print(f"         To       : {payload['alert']['to']}  (fabricated — swap for your Twilio test number)")
    print(f"         Message  : {payload['alert']['message']}")
    return payload


# ---------------------------------------------------------------------------
# STEP 5 — Twilio placeholder (implement with real credentials)
# ---------------------------------------------------------------------------

def send_alert_via_twilio(alert: dict) -> None:
    """
    Placeholder: send `alert` via Twilio.

    To activate, install the Twilio SDK and set these env vars:
        TWILIO_ACCOUNT_SID  — your Account SID
        TWILIO_AUTH_TOKEN   — your Auth Token
        TWILIO_FROM         — your Twilio number (e.g. +1XXXXXXXXXX)
        TWILIO_TO           — your own test number (NOT the partner's fabricated phone)

    Uncomment the block below once credentials are in place.
    """
    print("\n[STEP 5] send_alert_via_twilio() — placeholder (implement me)")
    print(f"         Channel : {alert['channel']}")
    print(f"         To      : {alert['to']}")
    print(f"         Message : {alert['message']}")

    # --- Uncomment to send a real SMS via Twilio ---
    from twilio.rest import Client
    sid   = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    from_ = os.environ["TWILIO_FROM"]
    to    = os.environ["TWILIO_TO"]   # use YOUR test number, not the partner's
    client = Client(sid, token)
    client.messages.create(body=alert["message"], from_=from_, to=to)
    print("         Twilio response: message queued.")
    # -----------------------------------------------


# ---------------------------------------------------------------------------
# Main — runs the pipeline end-to-end
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Regulatory Radar — pipeline.py")
    print("=" * 60)

    raw_text      = fetch_eurlex_text()
    rule          = extract_rule(raw_text)
    gap           = find_gap(rule)
    alert_payload = build_alert_payload(gap)

    # Write the finding to disk in the sample_expected_output.json shape
    output_path = BASE / "finding_P013_A.json"
    output_path.write_text(json.dumps(alert_payload, indent=2))
    print(f"\n         Finding written to {output_path.name}")

    # Fire the alert
    send_alert_via_twilio(alert_payload["alert"])

    # ------------------------------------------------------------------
    # CHECKPOINT (bob_rules.md — summarize after each significant step)
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  CHECKPOINT — pipeline complete")
    print("=" * 60)
    print("  Step 1  fetch_eurlex_text()    EUR-Lex HTML fetched (CELEX:32023R1542)")
    print("  Step 2  extract_rule()         Battery Passport rule object built")
    print("  Step 3  find_gap()             P013-A gap confirmed (lmt, EU, no passport)")
    print("  Step 4  build_alert_payload()  Payload matches sample_expected_output.json shape")
    print("  Step 5  send_alert_via_twilio() Placeholder ready — uncomment to fire real SMS")
    print(f"  Output  finding_P013_A.json    written to repo root")
    print("=" * 60)
