"""
alerts.py — Send SMS alerts for every finding in all_findings.json
===================================================================
Loads findings produced by multi_gap.find_gaps_for_all_rules(), builds
an SMS message for each one, and sends it via Twilio to the test number
in TWILIO_TO (never to the partner's fabricated phone).

Required environment variables:
    TWILIO_ACCOUNT_SID  — Twilio Account SID
    TWILIO_AUTH_TOKEN   — Twilio Auth Token
    TWILIO_FROM         — your Twilio sender number (e.g. +1XXXXXXXXXX)
    TWILIO_TO           — your own test number to receive all alerts

Run:
    pip install twilio python-dotenv
    python alerts.py

bob_rules.md constraints applied
---------------------------------
- Simplicity First  : one function, one loop, one Twilio call per finding.
- Read Before Write : all_findings.json is read and validated before any
                      Twilio call is attempted.
- Surgical Changes  : pipeline.py is untouched.
- Checkpoint        : summary printed after all alerts are sent.
- Fail Loud         : missing env vars or missing findings file raise
                      immediately with a clear message.
"""

import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).parent
DEFAULT_FINDINGS_FILE = "all_findings.json"


def send_alerts_for_findings(findings_file: str = DEFAULT_FINDINGS_FILE) -> int:
    """
    Load findings from `findings_file`, build one SMS per finding, and
    send each via Twilio to the TWILIO_TO test number.

    Returns the number of alerts successfully sent.

    Raises:
        SystemExit — if the findings file is missing, the JSON is invalid,
                     or any required Twilio env var is absent.
    """
    findings_path = BASE / findings_file

    # ------------------------------------------------------------------
    # Read Before You Write (bob_rules.md)
    # ------------------------------------------------------------------
    print("\n[alerts] Reading findings file …")

    if not findings_path.exists():
        sys.exit(f"ERROR: findings file not found: {findings_path}")

    try:
        findings = json.loads(findings_path.read_text())
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: could not parse {findings_path.name}: {exc}")

    if not isinstance(findings, list):
        sys.exit(f"ERROR: {findings_path.name} must contain a JSON array.")

    print(f"         Findings loaded : {len(findings)}")

    if not findings:
        print("         Nothing to send — no findings.")
        return 0

    # ------------------------------------------------------------------
    # Load Twilio credentials — fail loud if any are missing.
    # ------------------------------------------------------------------
    missing = [v for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                           "TWILIO_FROM", "TWILIO_TO")
               if not os.environ.get(v)]
    if missing:
        sys.exit(
            f"ERROR: missing required environment variable(s): "
            f"{', '.join(missing)}\n"
            f"Set them (or add to .env and run: python-dotenv run -- python alerts.py)."
        )

    from twilio.rest import Client  # imported here so the file is importable without twilio installed

    sid    = os.environ["TWILIO_ACCOUNT_SID"]
    token  = os.environ["TWILIO_AUTH_TOKEN"]
    from_  = os.environ["TWILIO_FROM"]
    to     = os.environ["TWILIO_TO"]   # always our test number — never the partner's phone

    client = Client(sid, token)

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------
    print(f"         Sending to      : {to}  (test number — not the partner's phone)")
    print()

    sent = 0
    for finding in findings:
        message_body = (
            f"[{finding['rule_id']}] {finding['company']} / {finding['product']}: "
            f"{finding['gap']} "
            f"Deadline: {finding['deadline']}. "
            f"Action: {finding['recommended_action']} "
            f"Source: {finding['source_url']}"
        )

        print(f"  → Sending alert for {finding['partner_id']} / {finding['product_id']}")
        print(f"    {message_body[:120]}{'…' if len(message_body) > 120 else ''}")

        client.messages.create(body=message_body, from_=from_, to=to)
        sent += 1

    # ------------------------------------------------------------------
    # CHECKPOINT (bob_rules.md)
    # ------------------------------------------------------------------
    print(f"\n[alerts] CHECKPOINT — done")
    print(f"         Findings loaded : {len(findings)}")
    print(f"         Alerts sent     : {sent}")
    print(f"         Sent to         : {to}")

    return sent


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Load .env if python-dotenv is available (optional convenience).
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[alerts] .env loaded via python-dotenv.")
    except ImportError:
        pass  # fine — env vars may be set in the shell directly

    send_alerts_for_findings()
