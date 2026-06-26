# backend-app — Regulatory Radar

Python pipeline and FastAPI REST server for the Regulatory Radar project.
For the full project overview see the [root README](../README.md).

---

## What's in here

| File / Dir | Purpose |
|---|---|
| `api_server.py` | FastAPI server — serves all `/api/*` endpoints consumed by the frontend |
| `multi_gap.py` | Gap-detection engine: matches rules to partner products |
| `alerts.py` | Twilio alert dispatcher (SMS / WhatsApp / email) |
| `compliance_engine.py` | Lower-level compliance logic |
| `live_rules_fetcher.py` | Scrapes live EUR-Lex / ECHA sources |
| `pipeline.py` | End-to-end pipeline orchestrator |
| `partners.json` | 22-company SME portfolio (fixed dataset) |
| `rules_catalog.json` | Active EU rules used by the gap engine |
| `all_findings.json` | Pre-computed findings (output of `multi_gap.py`) |
| `alerts.json` | Enriched alert records (output of `alerts.py`) |
| `audit_log.jsonl` | Append-only audit trail of gap detections and alert attempts |
| `taxonomy.json` | Controlled vocabulary (product categories, substances, regulation families) |
| `DATASET_README.md` | Full data-dictionary for `partners.json` |
| `SOURCES.md` | Curated list of live regulatory sources |

---

## Setup

```bash
cd backend-app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install fastapi uvicorn python-dotenv twilio
```

Copy env vars:

```bash
cp ../.env.example .env
# Edit .env and fill in TWILIO_* values
```

---

## Run the API server

```bash
source .venv/bin/activate
uvicorn api_server:app --reload
```

- API root: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

---

## Run the gap-detection pipeline

```bash
python multi_gap.py     # → writes all_findings.json + all_gaps.json
```

## Send alerts

```bash
python alerts.py        # reads all_findings.json, sends one Twilio message per finding
```

Requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `TWILIO_TO` in `.env`.
Alerts are always sent to `TWILIO_TO` (your own test number) — never to fabricated partner phones.

---

## Dataset

22 companies · 53 products · all contacts fabricated (`@example.com` / placeholder phones).
See [`DATASET_README.md`](DATASET_README.md) for the full field-by-field data dictionary.
See [`SOURCES.md`](SOURCES.md) for live regulatory sources.

---

## Environment variables

| Variable | Required by | Description |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | `alerts.py`, `api_server.py` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | `alerts.py`, `api_server.py` | Twilio Auth Token |
| `TWILIO_FROM` | `alerts.py`, `api_server.py` | Sender number |
| `TWILIO_TO` | `alerts.py`, `api_server.py` | Test recipient number |
