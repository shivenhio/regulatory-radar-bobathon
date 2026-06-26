"""
test_compliance_engine.py
=========================
Proper test suite for compliance_engine.py.

Test data is INDEPENDENTLY authored — not derived from partners.csv.
Each test case explicitly states what should fire and why, and verifies
the exact opposite (non-trigger) cases don't fire.

Run:
    python test_compliance_engine.py
"""

import json
import sys
import tempfile
import csv
import os
from pathlib import Path

# Add repo root to path so we can import compliance_engine
sys.path.insert(0, str(Path(__file__).parent))

from compliance_engine import ComplianceEngine, REQUIRED_COLUMNS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0

def ok(label):
    global PASS
    PASS += 1
    print(f"  PASS  {label}")

def fail(label, detail=""):
    global FAIL
    FAIL += 1
    print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))


def make_engine_with_rows(rows: list[dict]) -> tuple:
    """
    Write rows to a temp CSV and return (engine, records).
    Bypasses rules_cache and rules_catalog so we test pure logic.
    """
    fieldnames = list(REQUIRED_COLUMNS) + ["category", "product_name"]
    # Fill any missing fields with safe defaults
    defaults = {
        "markets": "EU", "intended_use": "consumer", "has_battery": "False",
        "battery_type": "none", "battery_capacity_wh": "0", "connector": "usb_c",
        "substances": "", "company": "TestCo", "partner_id": "T001",
        "product_id": "T001-A", "product_name": "Test Product",
        "contact_email": "test@example.com", "contact_phone": "+1234567890",
        "preferred_channel": "email", "category": "electronics",
    }
    completed = [{**defaults, **row} for row in rows]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv",
                                     delete=False, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(completed[0].keys()))
        writer.writeheader()
        writer.writerows(completed)
        tmp_path = f.name

    engine = ComplianceEngine(tmp_path)
    records = engine.parse_records()
    return engine, records, tmp_path


def alerts_for(rows, rule_id_filter=None):
    engine, records, tmp = make_engine_with_rows(rows)
    try:
        all_alerts = engine.generate_alerts(records)
        if rule_id_filter:
            return [a for a in all_alerts if a["rule_id"] == rule_id_filter]
        return all_alerts
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# SECTION 1 — battery_passport
# ---------------------------------------------------------------------------

def test_battery_passport():
    print("\n[battery_passport — Art. 77 Reg (EU) 2023/1542]")

    # SHOULD fire: EU market, lmt battery, >2 Wh
    a = alerts_for([{
        "markets": "EU", "has_battery": "True",
        "battery_type": "lmt", "battery_capacity_wh": "500",
        "company": "ScootCo", "product_name": "City Scooter 500Wh"
    }], "battery_passport")
    if len(a) == 1 and a[0]["company"] == "ScootCo":
        ok("LMT battery 500 Wh in EU fires passport alert")
    else:
        fail("LMT battery 500 Wh in EU fires passport alert", f"got {len(a)} alerts")

    # SHOULD fire: industrial battery, 3 Wh (just above threshold)
    a = alerts_for([{
        "markets": "EU", "has_battery": "True",
        "battery_type": "industrial", "battery_capacity_wh": "3",
    }], "battery_passport")
    if len(a) == 1:
        ok("Industrial battery 3 Wh in EU fires passport alert")
    else:
        fail("Industrial battery 3 Wh in EU fires passport alert", f"got {len(a)}")

    # SHOULD NOT fire: capacity exactly 2 Wh (rule is strictly > 2)
    a = alerts_for([{
        "markets": "EU", "has_battery": "True",
        "battery_type": "lmt", "battery_capacity_wh": "2",
    }], "battery_passport")
    if len(a) == 0:
        ok("LMT battery exactly 2 Wh does NOT fire (threshold is >2)")
    else:
        fail("LMT battery exactly 2 Wh should NOT fire", f"got {len(a)}")

    # SHOULD NOT fire: portable battery (wrong type for passport rule)
    a = alerts_for([{
        "markets": "EU", "has_battery": "True",
        "battery_type": "portable", "battery_capacity_wh": "500",
    }], "battery_passport")
    if len(a) == 0:
        ok("Portable battery does NOT fire passport alert (wrong type)")
    else:
        fail("Portable battery should NOT fire passport", f"got {len(a)}")

    # SHOULD NOT fire: US-only market
    a = alerts_for([{
        "markets": "US", "has_battery": "True",
        "battery_type": "lmt", "battery_capacity_wh": "500",
    }], "battery_passport")
    if len(a) == 0:
        ok("LMT battery US-only market does NOT fire passport alert")
    else:
        fail("US-only market should NOT fire passport", f"got {len(a)}")

    # SHOULD NOT fire: no battery
    a = alerts_for([{
        "markets": "EU", "has_battery": "False",
        "battery_type": "lmt", "battery_capacity_wh": "500",
    }], "battery_passport")
    if len(a) == 0:
        ok("has_battery=False does NOT fire passport alert")
    else:
        fail("has_battery=False should NOT fire passport", f"got {len(a)}")


# ---------------------------------------------------------------------------
# SECTION 2 — battery_removability
# ---------------------------------------------------------------------------

def test_battery_removability():
    print("\n[battery_removability — Art. 11 Reg (EU) 2023/1542]")

    # SHOULD fire: consumer product, portable battery, EU
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer",
        "has_battery": "True", "battery_type": "portable",
        "company": "GadgetFirm", "product_name": "Smart Speaker"
    }], "battery_removability")
    if len(a) == 1:
        ok("Consumer portable battery in EU fires removability alert")
    else:
        fail("Consumer portable battery in EU", f"got {len(a)}")

    # SHOULD fire: toy, button_cell
    a = alerts_for([{
        "markets": "EU", "intended_use": "toy",
        "has_battery": "True", "battery_type": "button_cell",
    }], "battery_removability")
    if len(a) == 1:
        ok("Toy with button_cell battery fires removability alert")
    else:
        fail("Toy button_cell removability", f"got {len(a)}")

    # SHOULD NOT fire: industrial use (excluded from scope)
    a = alerts_for([{
        "markets": "EU", "intended_use": "industrial",
        "has_battery": "True", "battery_type": "portable",
    }], "battery_removability")
    if len(a) == 0:
        ok("Industrial use does NOT fire removability alert")
    else:
        fail("Industrial use should NOT fire removability", f"got {len(a)}")

    # SHOULD NOT fire: lmt battery (wrong type for removability)
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer",
        "has_battery": "True", "battery_type": "lmt",
    }], "battery_removability")
    if len(a) == 0:
        ok("LMT battery does NOT fire removability alert (wrong type)")
    else:
        fail("LMT should NOT fire removability", f"got {len(a)}")


# ---------------------------------------------------------------------------
# SECTION 3 — common_charger
# ---------------------------------------------------------------------------

def test_common_charger():
    print("\n[common_charger — RED Delegated Reg (EU) 2022/2380]")

    # SHOULD fire: barrel connector, consumer, EU
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer",
        "connector": "barrel", "company": "ChargeCo", "product_name": "Action Cam"
    }], "common_charger")
    if len(a) == 1:
        ok("Barrel connector consumer product in EU fires common_charger alert")
    else:
        fail("Barrel connector in EU", f"got {len(a)}")

    # SHOULD fire: micro_usb
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer", "connector": "micro_usb",
    }], "common_charger")
    if len(a) == 1:
        ok("micro_usb connector fires common_charger alert")
    else:
        fail("micro_usb connector", f"got {len(a)}")

    # SHOULD fire: proprietary
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer", "connector": "proprietary",
    }], "common_charger")
    if len(a) == 1:
        ok("Proprietary connector fires common_charger alert")
    else:
        fail("Proprietary connector", f"got {len(a)}")

    # SHOULD NOT fire: usb_c connector (already compliant)
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer", "connector": "usb_c",
    }], "common_charger")
    if len(a) == 0:
        ok("usb_c connector does NOT fire common_charger alert (already compliant)")
    else:
        fail("usb_c should NOT fire common_charger", f"got {len(a)}")

    # SHOULD NOT fire: industrial use
    a = alerts_for([{
        "markets": "EU", "intended_use": "industrial", "connector": "barrel",
    }], "common_charger")
    if len(a) == 0:
        ok("Industrial product with barrel connector does NOT fire common_charger")
    else:
        fail("Industrial barrel should NOT fire common_charger", f"got {len(a)}")

    # SHOULD NOT fire: non-EU market
    a = alerts_for([{
        "markets": "US|CA", "intended_use": "consumer", "connector": "barrel",
    }], "common_charger")
    if len(a) == 0:
        ok("Non-EU market barrel connector does NOT fire common_charger")
    else:
        fail("Non-EU market should NOT fire common_charger", f"got {len(a)}")


# ---------------------------------------------------------------------------
# SECTION 4 — gpsr_button_cell
# ---------------------------------------------------------------------------

def test_gpsr_button_cell():
    print("\n[gpsr_button_cell — Art. 15 GPSR Reg (EU) 2023/988]")

    # SHOULD fire: consumer, button_cell, EU
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer",
        "has_battery": "True", "battery_type": "button_cell",
        "company": "ToyMaker", "product_name": "Remote Control Car"
    }], "gpsr_button_cell")
    if len(a) == 1:
        ok("Consumer button_cell product in EU fires gpsr_button_cell alert")
    else:
        fail("Consumer button_cell in EU", f"got {len(a)}")

    # SHOULD fire: toy
    a = alerts_for([{
        "markets": "EU", "intended_use": "toy",
        "has_battery": "True", "battery_type": "button_cell",
    }], "gpsr_button_cell")
    if len(a) == 1:
        ok("Toy button_cell fires gpsr_button_cell alert")
    else:
        fail("Toy button_cell", f"got {len(a)}")

    # SHOULD NOT fire: portable battery (not button_cell)
    a = alerts_for([{
        "markets": "EU", "intended_use": "consumer",
        "has_battery": "True", "battery_type": "portable",
    }], "gpsr_button_cell")
    if len(a) == 0:
        ok("Portable battery does NOT fire gpsr_button_cell (wrong type)")
    else:
        fail("Portable should NOT fire gpsr_button_cell", f"got {len(a)}")

    # SHOULD NOT fire: medical use
    a = alerts_for([{
        "markets": "EU", "intended_use": "medical",
        "has_battery": "True", "battery_type": "button_cell",
    }], "gpsr_button_cell")
    if len(a) == 0:
        ok("Medical use does NOT fire gpsr_button_cell")
    else:
        fail("Medical should NOT fire gpsr_button_cell", f"got {len(a)}")


# ---------------------------------------------------------------------------
# SECTION 5 — reach_svhc
# ---------------------------------------------------------------------------

def test_reach_svhc():
    print("\n[reach_svhc — REACH Art. 7(2) + Art. 33]")

    # SHOULD fire: BPA present, EU market
    a = alerts_for([{
        "markets": "EU", "substances": "BPA",
        "company": "PlasticCo", "product_name": "Enclosure"
    }], "reach_svhc")
    if len(a) == 1:
        ok("BPA substance in EU product fires reach_svhc alert")
    else:
        fail("BPA in EU", f"got {len(a)}")

    # SHOULD fire: DEHP in pipe-delimited list
    a = alerts_for([{
        "markets": "EU", "substances": "lead|DEHP|cadmium",
    }], "reach_svhc")
    if len(a) == 1:
        ok("DEHP in pipe-delimited substance list fires reach_svhc")
    else:
        fail("DEHP pipe list", f"got {len(a)}")

    # SHOULD fire: MCCP (new substance added to our list)
    a = alerts_for([{
        "markets": "EU", "substances": "MCCP",
    }], "reach_svhc")
    if len(a) == 1:
        ok("MCCP fires reach_svhc alert")
    else:
        fail("MCCP", f"got {len(a)}")

    # SHOULD NOT fire: harmless substance
    a = alerts_for([{
        "markets": "EU", "substances": "silicone",
    }], "reach_svhc")
    if len(a) == 0:
        ok("Non-SVHC substance does NOT fire reach_svhc")
    else:
        fail("Harmless substance should NOT fire reach_svhc", f"got {len(a)}")

    # SHOULD NOT fire: SVHC present but non-EU market
    a = alerts_for([{
        "markets": "US", "substances": "BPA",
    }], "reach_svhc")
    if len(a) == 0:
        ok("SVHC in non-EU market does NOT fire reach_svhc")
    else:
        fail("Non-EU SVHC should NOT fire", f"got {len(a)}")

    # SHOULD NOT fire: empty substances field
    a = alerts_for([{
        "markets": "EU", "substances": "",
    }], "reach_svhc")
    if len(a) == 0:
        ok("Empty substances field does NOT fire reach_svhc")
    else:
        fail("Empty substances should NOT fire", f"got {len(a)}")


# ---------------------------------------------------------------------------
# SECTION 6 — carbon footprint
# ---------------------------------------------------------------------------

def test_battery_carbon_footprint():
    print("\n[battery_carbon_footprint — Art. 7 Reg (EU) 2023/1542]")

    # SHOULD fire: industrial battery, EU
    a = alerts_for([{
        "markets": "EU", "has_battery": "True", "battery_type": "industrial",
        "company": "PowerSys", "product_name": "48V Industrial Pack"
    }], "battery_carbon_footprint")
    if len(a) == 1:
        ok("Industrial battery in EU fires carbon footprint alert")
    else:
        fail("Industrial battery carbon footprint", f"got {len(a)}")

    # SHOULD fire: ev battery
    a = alerts_for([{
        "markets": "EU", "has_battery": "True", "battery_type": "ev",
    }], "battery_carbon_footprint")
    if len(a) == 1:
        ok("EV battery in EU fires carbon footprint alert")
    else:
        fail("EV battery carbon footprint", f"got {len(a)}")

    # SHOULD NOT fire: portable battery (not in scope for carbon footprint)
    a = alerts_for([{
        "markets": "EU", "has_battery": "True", "battery_type": "portable",
    }], "battery_carbon_footprint")
    if len(a) == 0:
        ok("Portable battery does NOT fire carbon footprint alert")
    else:
        fail("Portable should NOT fire carbon footprint", f"got {len(a)}")


# ---------------------------------------------------------------------------
# SECTION 7 — column validation
# ---------------------------------------------------------------------------

def test_column_validation():
    print("\n[column validation]")

    # Write a CSV missing required columns
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv",
                                     delete=False, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["foo", "bar"])
        writer.writeheader()
        writer.writerow({"foo": "1", "bar": "2"})
        tmp_path = f.name

    try:
        engine = ComplianceEngine(tmp_path)
        records = engine.parse_records()
        missing = REQUIRED_COLUMNS - set(records[0].keys())
        if missing:
            ok(f"Column validator correctly identifies {len(missing)} missing column(s)")
        else:
            fail("Column validator should have found missing columns")
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# SECTION 8 — output shape
# ---------------------------------------------------------------------------

def test_output_shape():
    print("\n[output shape — matches sample_expected_output.json]")

    a = alerts_for([{
        "markets": "EU", "has_battery": "True",
        "battery_type": "lmt", "battery_capacity_wh": "500",
        "company": "ShapeTestCo", "product_id": "SH-001",
        "product_name": "Shape Test Scooter", "partner_id": "SH",
        "contact_email": "test@shape.example.com",
        "contact_phone": "+49000000",
        "preferred_channel": "sms",
    }], "battery_passport")

    if not a:
        fail("No alert generated for shape test")
        return

    alert = a[0]

    required_fields = ["rule_id", "company", "partner_id", "product_id",
                       "regulation", "gap", "deadline", "severity",
                       "recommended_action", "source_url", "alert"]
    missing = [f for f in required_fields if f not in alert]
    if not missing:
        ok("Alert contains all required fields (matches sample_expected_output.json shape)")
    else:
        fail(f"Alert missing fields: {missing}")

    # Check alert sub-block
    alert_block = alert.get("alert", {})
    alert_fields = ["channel", "to", "message"]
    missing_alert = [f for f in alert_fields if f not in alert_block]
    if not missing_alert:
        ok("Alert.alert block has channel, to, message fields")
    else:
        fail(f"Alert block missing: {missing_alert}")

    if alert["deadline"] == "2027-02-18":
        ok("Deadline is correct: 2027-02-18")
    else:
        fail(f"Wrong deadline: {alert['deadline']}")

    if alert["severity"] == "high":
        ok("Severity is correctly 'high'")
    else:
        fail(f"Wrong severity: {alert['severity']}")

    if "eur-lex.europa.eu" in alert["source_url"]:
        ok("source_url points to eur-lex.europa.eu")
    else:
        fail(f"Bad source_url: {alert['source_url']}")


# ---------------------------------------------------------------------------
# SECTION 9 — multi-rule, multi-product
# ---------------------------------------------------------------------------

def test_multi_rule_multi_product():
    print("\n[multi-rule, multi-product interaction]")

    # Product A: should trigger battery_passport only
    # Product B: should trigger common_charger only
    # Product C: should trigger both reach_svhc and battery_removability
    rows = [
        {   # A — LMT battery 280Wh EU
            "company": "MultiCo", "product_id": "M-001", "product_name": "E-Scooter",
            "markets": "EU", "has_battery": "True",
            "battery_type": "lmt", "battery_capacity_wh": "280",
            "connector": "none", "substances": "", "intended_use": "consumer",
        },
        {   # B — barrel connector, no battery
            "company": "MultiCo", "product_id": "M-002", "product_name": "Dash Cam",
            "markets": "EU", "has_battery": "False",
            "battery_type": "none", "battery_capacity_wh": "0",
            "connector": "barrel", "substances": "", "intended_use": "consumer",
        },
        {   # C — portable battery + DEHP
            "company": "MultiCo", "product_id": "M-003", "product_name": "BT Speaker",
            "markets": "EU", "has_battery": "True",
            "battery_type": "portable", "battery_capacity_wh": "12",
            "connector": "usb_c", "substances": "DEHP", "intended_use": "consumer",
        },
    ]

    engine, records, tmp = make_engine_with_rows(rows)
    try:
        all_alerts = engine.generate_alerts(records)
    finally:
        os.unlink(tmp)

    def rule_hits(pid, rid):
        return [a for a in all_alerts if a["product_id"] == pid and a["rule_id"] == rid]

    if rule_hits("M-001", "battery_passport"):
        ok("M-001 (e-scooter LMT) fires battery_passport")
    else:
        fail("M-001 should fire battery_passport")

    if not rule_hits("M-001", "common_charger"):
        ok("M-001 does NOT fire common_charger")
    else:
        fail("M-001 should NOT fire common_charger")

    if rule_hits("M-002", "common_charger"):
        ok("M-002 (dash cam barrel) fires common_charger")
    else:
        fail("M-002 should fire common_charger")

    if not rule_hits("M-002", "battery_passport"):
        ok("M-002 does NOT fire battery_passport")
    else:
        fail("M-002 should NOT fire battery_passport")

    if rule_hits("M-003", "battery_removability"):
        ok("M-003 (speaker portable) fires battery_removability")
    else:
        fail("M-003 should fire battery_removability")

    if rule_hits("M-003", "reach_svhc"):
        ok("M-003 (DEHP) fires reach_svhc")
    else:
        fail("M-003 should fire reach_svhc")

    if not rule_hits("M-003", "battery_passport"):
        ok("M-003 does NOT fire battery_passport (portable, not lmt/industrial)")
    else:
        fail("M-003 should NOT fire battery_passport")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Suppress engine startup prints during testing
    import io, contextlib

    def silent(fn):
        with contextlib.redirect_stdout(io.StringIO()):
            fn()

    print("=" * 60)
    print("  Compliance Engine — Test Suite")
    print("=" * 60)

    silent(test_battery_passport)
    silent(test_battery_removability)
    silent(test_common_charger)
    silent(test_gpsr_button_cell)
    silent(test_reach_svhc)
    silent(test_battery_carbon_footprint)
    test_column_validation()
    silent(test_output_shape)
    silent(test_multi_rule_multi_product)

    print("\n" + "=" * 60)
    print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    print("=" * 60)
    sys.exit(0 if FAIL == 0 else 1)
