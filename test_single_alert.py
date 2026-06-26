"""
test_single_alert.py
====================
Sends ONE test SMS via Twilio to verify credentials work.
Uses the first finding from all_findings.json.

Run:
    python test_single_alert.py
"""

import json, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Check env vars
missing = [v for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM", "TWILIO_TO")
           if not os.environ.get(v)]
if missing:
    sys.exit(f"ERROR: set these in .env first: {', '.join(missing)}")

# Load first finding
findings = json.loads(Path("all_findings.json").read_text(encoding="utf-8"))
if not findings:
    sys.exit("ERROR: all_findings.json is empty — run compliance_engine.py first")

finding = findings[0]
message = (
    f"[TEST] {finding['company']}: {finding['product_name'] or finding.get('product','')} "
    f"— {finding['rule_id']} — deadline {finding['deadline']}. "
    f"{finding['recommended_action']} Source: {finding['source_url']}"
)[:300]  # SMS limit

print(f"Sending test SMS to {os.environ['TWILIO_TO']}...")
print(f"Message: {message}")

from twilio.rest import Client
client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
msg = client.messages.create(
    body=message,
    from_=os.environ["TWILIO_FROM"],
    to=os.environ["TWILIO_TO"],
)
print(f"Sent! SID: {msg.sid} | Status: {msg.status}")
