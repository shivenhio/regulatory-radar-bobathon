"""
api_server.py — Regulatory Radar FastAPI server
================================================
Reads the pre-computed JSON/JSONL data files and serves the REST endpoints
expected by the frontend (see frontend-app/BACKEND_INTEGRATION.md).

Run:
    uvicorn api_server:app --reload          # dev
    uvicorn api_server:app --port 8000       # prod-like

All responses are shaped to match frontend-app/src/lib/api/types.ts exactly.
No database is needed — the JSON files are the source of truth.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Helpers — file loading
# ---------------------------------------------------------------------------

BASE = Path(__file__).parent

app = FastAPI(title="Regulatory Radar API", version="1.0.0")

# Allow the Vite dev server (and any origin in dev) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_json(filename: str) -> Any:
    path = BASE / filename
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"{filename} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(filename: str) -> List[Dict[str, Any]]:
    path = BASE / filename
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    result = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return result


# ---------------------------------------------------------------------------
# Stable synthetic IDs — deterministic so references stay consistent across
# requests without any database.
# ---------------------------------------------------------------------------

def _sid(*parts: str) -> str:  # noqa: E302
    """Return an 8-char stable hex ID derived from the input parts."""
    return hashlib.md5(":".join(parts).encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

_HIGH_RISK_SUBSTANCES = {
    "lead", "mercury", "cadmium", "hexavalent chromium",
    "PBB", "PBDE", "DEHP", "DBP", "BBP", "DIBP",
}

_COUNTRY_TO_LANGUAGE: Dict[str, str] = {
    "DE": "de", "AT": "de", "CH": "de",
    "FR": "fr", "BE": "fr",
    "PL": "en", "NL": "en", "SE": "en", "FI": "en",
    "LT": "en", "LV": "en", "EE": "en",
}

_RULE_FAMILY: Dict[str, str] = {
    "BATT": "battery",
    "REACH": "reach",
    "ROHS": "rohs",
    "WEEE": "weee",
    "ELEKTROG": "weee",
    "PPWR": "other",
}


def _infer_family(rule_id: str) -> str:
    prefix = rule_id.split("-")[0].upper()
    return _RULE_FAMILY.get(prefix, "other")


def _infer_reg_status(deadline: Optional[str]) -> str:
    if not deadline:
        return "upcoming"
    try:
        d = date.fromisoformat(deadline)
        today = date.today()
        if d < today:
            return "past"
        # "due" = within 12 months
        delta = (d - today).days
        return "due" if delta <= 365 else "upcoming"
    except ValueError:
        return "upcoming"


def _severity_to_status(severity: str, deadline: Optional[str]) -> str:
    """Map backend severity + deadline → frontend FindingStatus (red/amber/green)."""
    if deadline:
        try:
            if date.fromisoformat(deadline) < date.today():
                return "red"   # overdue always red
        except ValueError:
            pass
    mapping = {"high": "red", "medium": "amber", "low": "amber"}
    return mapping.get(severity.lower(), "amber")


def _is_high_risk(substances: list[str]) -> bool:
    lowered = {s.lower() for s in substances}
    return bool(lowered & {s.lower() for s in _HIGH_RISK_SUBSTANCES})


# ---------------------------------------------------------------------------
# /api/companies
# ---------------------------------------------------------------------------

def _partner_to_company(p: dict) -> dict:
    contact = p["contact"]
    lang = _COUNTRY_TO_LANGUAGE.get(p.get("hq_country", ""), "en")
    return {
        "id": p["partner_id"],
        "name": p["company"],
        "markets": p.get("sells_in", []),
        "contacts": [
            {
                "name": contact["name"],
                "email": contact["email"],
                "phone": contact.get("phone"),
            }
        ],
        "preferredChannel": contact.get("preferred_channel", "email"),
        "preferredLanguage": lang,
    }


@app.get("/api/companies")
def get_companies() -> list:
    data = _load_json("partners.json")
    return [_partner_to_company(p) for p in data["partners"]]


@app.get("/api/companies/{company_id}")
def get_company(company_id: str) -> dict:
    data = _load_json("partners.json")
    for p in data["partners"]:
        if p["partner_id"] == company_id:
            return _partner_to_company(p)
    raise HTTPException(status_code=404, detail="Company not found")


# ---------------------------------------------------------------------------
# /api/products
# ---------------------------------------------------------------------------

def _product_to_api(product: dict, partner_id: str) -> dict:
    bt = product.get("battery_type")
    return {
        "id": product["product_id"],
        "companyId": partner_id,
        "name": product["name"],
        "category": product["category"],
        "batteryType": bt if bt and bt != "none" else None,
        "substances": product.get("substances", []),
        "markets": product.get("markets", []),
    }


@app.get("/api/products")
def get_products(companyId: Optional[str] = Query(default=None)) -> list:
    data = _load_json("partners.json")
    results = []
    for p in data["partners"]:
        if companyId and p["partner_id"] != companyId:
            continue
        for prod in p.get("products", []):
            results.append(_product_to_api(prod, p["partner_id"]))
    return results


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    data = _load_json("partners.json")
    for p in data["partners"]:
        for prod in p.get("products", []):
            if prod["product_id"] == product_id:
                return _product_to_api(prod, p["partner_id"])
    raise HTTPException(status_code=404, detail="Product not found")


# ---------------------------------------------------------------------------
# /api/regulations
# ---------------------------------------------------------------------------

def _rule_to_regulation(rule: dict) -> dict:
    article = rule.get("article", "")
    deadline = rule.get("deadline")
    return {
        "id": rule["rule_id"],
        "reference": rule.get("regulation_id", rule["rule_id"]),
        "title": f"{rule.get('regulation_id', rule['rule_id'])} — {article}",
        "family": _infer_family(rule["rule_id"]),
        "status": _infer_reg_status(deadline),
        "deadline": deadline,
        "sourceUrls": [rule["source_url"]],
        "articles": [
            {
                "ref": article,
                "title": article,
                "deadline": deadline,
                "description": rule.get("requirement_text", ""),
            }
        ],
        "summary": rule.get("requirement_text", ""),
    }


@app.get("/api/regulations")
def get_regulations() -> list:
    catalog = _load_json("rules_catalog.json")
    return [_rule_to_regulation(r) for r in catalog.get("rules", [])]


@app.get("/api/regulations/{regulation_id}")
def get_regulation(regulation_id: str) -> dict:
    catalog = _load_json("rules_catalog.json")
    for r in catalog.get("rules", []):
        if r["rule_id"] == regulation_id:
            return _rule_to_regulation(r)
    raise HTTPException(status_code=404, detail="Regulation not found")


# ---------------------------------------------------------------------------
# /api/findings
# ---------------------------------------------------------------------------

def _finding_to_api(f: dict, idx: int) -> dict:
    partner_id = f.get("partner_id", "")
    product_id = f.get("product_id", "")
    rule_id    = f.get("rule_id", "")
    severity   = f.get("severity", "high")
    deadline   = f.get("deadline")
    alert      = f.get("alert", {})

    # Build a stable synthetic ID from the three natural keys + index
    finding_id = _sid(partner_id, product_id, rule_id, str(idx))

    # Infer highRiskSubstance from the gap text (substances aren't in findings;
    # fall back to keyword scan on the requirement text)
    req_text = (f.get("requirement", "") + " " + f.get("gap", "")).lower()
    high_risk = any(s.lower() in req_text for s in _HIGH_RISK_SUBSTANCES)

    return {
        "id": finding_id,
        "companyId": partner_id,
        "productId": product_id,
        "regulationId": rule_id,
        "articleRef": None,          # not present in all_findings.json
        "status": _severity_to_status(severity, deadline),
        "deadline": deadline,
        "gapDescription": f.get("gap", ""),
        "recommendedFix": f.get("recommended_action", ""),
        "sourceUrls": [f["source_url"]] if f.get("source_url") else [],
        "alertChannel": alert.get("channel", "email"),
        "alertSent": True,           # findings in this file have been alerted
        "alertSentAt": None,         # timestamp is in audit_log, not findings
        "highRiskSubstance": high_risk,
    }


@app.get("/api/findings")
def get_findings(
    companyId:    Optional[str] = Query(default=None),
    productId:    Optional[str] = Query(default=None),
    regulationId: Optional[str] = Query(default=None),
    status:       Optional[str] = Query(default=None),
    market:       Optional[str] = Query(default=None),
) -> list:
    findings = _load_json("all_findings.json")
    result = []
    for idx, f in enumerate(findings):
        mapped = _finding_to_api(f, idx)
        if companyId    and mapped["companyId"]    != companyId:    continue
        if productId    and mapped["productId"]    != productId:    continue
        if regulationId and mapped["regulationId"] != regulationId: continue
        if status       and mapped["status"]       != status:       continue
        result.append(mapped)
    return result


# ---------------------------------------------------------------------------
# /api/alerts
# ---------------------------------------------------------------------------

# Map from audit_log alert_status string → frontend deliveryStatus
_DELIVERY_STATUS = {
    "sent":      "sent",
    "delivered": "delivered",
    "failed":    "failed",
}


def _alert_to_api(a: dict, idx: int, sent_at_map: Dict[str, str]) -> dict:
    partner_id = a.get("partner_id", "")
    product_id = a.get("product_id", "")
    rule_id    = a.get("rule_id", "")
    alert      = a.get("alert", {})
    channel    = alert.get("channel") or a.get("preferred_channel", "email")

    alert_id  = _sid(partner_id, product_id, rule_id, str(idx))
    finding_id = _sid(partner_id, product_id, rule_id, str(idx))

    # Look up sentAt from audit_log keyed on (partner_id, product_id, rule_id)
    audit_key  = f"{partner_id}::{product_id}::{rule_id}"
    sent_at    = sent_at_map.get(audit_key, datetime.utcnow().isoformat() + "Z")

    # Infer language from contact_email or hq_country; default "en"
    lang = "en"

    return {
        "id": alert_id,
        "findingId": finding_id,
        "companyId": partner_id,
        "productId": product_id,
        "regulationId": rule_id,
        "channel": channel,
        "language": lang,
        "sentAt": sent_at,
        "deliveryStatus": "sent",
        "messagePreview": alert.get("message", "")[:160],
    }


@app.get("/api/alerts")
def get_alerts() -> list:
    alerts_data = _load_json("alerts.json")
    audit_rows  = _load_jsonl("audit_log.jsonl")

    # Build a lookup of the most recent sentAt per (partner, product, rule)
    sent_at_map: Dict[str, str] = {}
    for row in audit_rows:
        if row.get("event") == "alert_attempt":
            key = f"{row.get('partner_id')}::{row.get('product_id')}::{row.get('rule_id')}"
            # Later rows in the JSONL override earlier ones (most-recent wins)
            sent_at_map[key] = row.get("timestamp", "")

    return [_alert_to_api(a, idx, sent_at_map) for idx, a in enumerate(alerts_data)]


# ---------------------------------------------------------------------------
# POST /api/alerts/preview
# ---------------------------------------------------------------------------

@app.post("/api/alerts/preview")
def preview_alert(body: dict) -> dict:
    finding_id: str = body.get("findingId", "")
    language:   str = body.get("language", "en")

    findings = _load_json("all_findings.json")

    # Find the finding whose synthetic ID matches
    for idx, f in enumerate(findings):
        fid = _sid(
            f.get("partner_id", ""),
            f.get("product_id", ""),
            f.get("rule_id", ""),
            str(idx),
        )
        if fid == finding_id:
            msg = f.get("alert", {}).get("message", "")
            if not msg:
                msg = (
                    f"{f['company']}: {f['product']} must comply with "
                    f"{f['rule_id']} by {f.get('deadline', 'TBD')}. "
                    f"Action: {f.get('recommended_action', '')} "
                    f"Source: {f.get('source_url', '')}"
                )
            if language == "de":
                msg = msg.replace("must comply with", "muss einhalten")
                msg = msg.replace("Action:", "Maßnahme:")
                msg = msg.replace("Source:", "Quelle:")
            return {"message": msg}

    raise HTTPException(status_code=404, detail="Finding not found")


# ---------------------------------------------------------------------------
# POST /api/alerts/resend
# ---------------------------------------------------------------------------

@app.post("/api/alerts/resend")
def resend_alert(body: dict) -> dict:
    """
    In a production system this would call Twilio directly.
    For now it returns a synthetic alertId — wire it to alerts.py when ready.
    """
    finding_id: str = body.get("findingId", "")
    if not finding_id:
        raise HTTPException(status_code=400, detail="findingId required")

    alert_id = _sid(finding_id, datetime.utcnow().isoformat())
    return {"ok": True, "alertId": alert_id}


# ---------------------------------------------------------------------------
# /api/audit
# ---------------------------------------------------------------------------

_AUDIT_KIND_MAP = {
    "alert_attempt": "alert_sent",
    "gap_found":     "gap_found",
    "rule_updated":  "rule_updated",
    "rule_added":    "rule_added",
}


def _audit_row_to_event(row: dict, idx: int) -> dict:
    raw_event = row.get("event", "gap_found")
    kind      = _AUDIT_KIND_MAP.get(raw_event, "gap_found")

    partner_id = row.get("partner_id")
    product_id = row.get("product_id")
    rule_id    = row.get("rule_id")
    company    = row.get("company", "")
    product    = row.get("product", "")
    priority   = row.get("priority", "")
    deadline   = row.get("deadline", "")

    if kind == "alert_sent":
        status = row.get("alert_status", "sent")
        summary = (
            f"Alert {status} to {company} for {product} "
            f"({rule_id}) — deadline {deadline}"
        )
    else:
        summary = (
            f"Gap found: {company} / {product} — {rule_id} "
            f"[{priority}] deadline {deadline}"
        )

    return {
        "id": _sid(str(idx), row.get("timestamp", ""), rule_id or ""),
        "timestamp": row.get("timestamp", ""),
        "kind": kind,
        "summary": summary,
        "refs": {
            "companyId":    partner_id,
            "productId":    product_id,
            "regulationId": rule_id,
            "findingId":    None,
        },
    }


@app.get("/api/audit")
def get_audit() -> list:
    rows = _load_jsonl("audit_log.jsonl")
    return [_audit_row_to_event(row, idx) for idx, row in enumerate(rows)]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
