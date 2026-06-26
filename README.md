# 🛰️ Regulatory Radar

> Continuous EU product-compliance monitoring for electronics SMEs.
> The backend finds regulatory gaps across a 22-company portfolio; the frontend
> visualises findings, deadlines, and alert history; Twilio fires real SMS/WhatsApp/email alerts.

**Stack:** Python · FastAPI · React · TanStack Start · IBM Bob · Twilio

---

## Repo layout

```
regulatory-radar/
├── README.md               ← you are here
├── .gitignore              ← root-level ignores (Python + Node + OS)
├── .env.example            ← all required env vars (copy → app-specific .env)
│
├── backend-app/            ← Python pipeline + FastAPI REST server
│   ├── README.md           ← backend-specific setup & run instructions
│   ├── api_server.py       ← FastAPI server (serves all /api/* endpoints)
│   ├── multi_gap.py        ← gap-detection engine
│   ├── alerts.py           ← Twilio alert dispatcher
│   ├── partners.json       ← 22-company SME portfolio (data source)
│   ├── rules_catalog.json  ← current EU rules
│   ├── all_findings.json   ← pre-computed findings (pipeline output)
│   ├── alerts.json         ← enriched alert records
│   ├── audit_log.jsonl     ← append-only audit trail
│   └── ...                 ← other scripts & data files
│
└── frontend-app/           ← React dashboard (TanStack Start + Vite)
    ├── src/
    │   ├── lib/api/        ← typed API client (mock-mode or live)
    │   ├── routes/         ← file-based routes
    │   └── components/     ← dashboard, findings, alerts UI
    ├── package.json
    ├── vite.config.ts
    └── ...
```

---

## Quickstart

### 1 — Backend

```bash
cd backend-app
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn python-dotenv twilio
cp ../.env.example .env          # fill in TWILIO_* values
uvicorn api_server:app --reload  # → http://localhost:8000
```

The API will be live at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the
auto-generated OpenAPI docs.

### 2 — Frontend

```bash
cd frontend-app
bun install                      # or: npm install
cp ../.env.example .env          # set VITE_API_BASE_URL=http://localhost:8000
bun run dev                      # → http://localhost:5173
```

Leave `VITE_API_BASE_URL` unset (or remove the `.env`) to run in **mock mode** — every screen
works offline with bundled demo data.

---

## Environment variables

See [`.env.example`](.env.example) for the full list. Each app reads only its own variables:

| Variable | App | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | frontend-app | Points the API client at the backend (omit for mock mode) |
| `TWILIO_ACCOUNT_SID` | backend-app | Twilio credentials for alert dispatch |
| `TWILIO_AUTH_TOKEN` | backend-app | — |
| `TWILIO_FROM` | backend-app | Your Twilio sender number |
| `TWILIO_TO` | backend-app | Your test number (alerts never go to fabricated partner phones) |

---

## Architecture

```
  ┌──────────────────────────────────────────────────────────────┐
  │                        backend-app/                          │
  │                                                              │
  │  partners.json  ──┐                                          │
  │  rules_catalog  ──┤──▶  multi_gap.py  ──▶  all_findings.json│
  │  (live sources) ──┘         │                    │           │
  │                             ▼                    ▼           │
  │                        alerts.py            api_server.py   │
  │                        (Twilio)              (FastAPI)       │
  └──────────────────────────────────┬───────────────┬──────────┘
                                     │               │
                                  real alerts    REST /api/*
                                  (SMS/WA/email)     │
                                             ┌───────▼────────┐
                                             │  frontend-app/ │
                                             │  React dashboard│
                                             └────────────────┘
```

---

## Running the gap-detection pipeline

```bash
cd backend-app
source .venv/bin/activate
python multi_gap.py          # writes all_findings.json + all_gaps.json
python alerts.py             # sends Twilio alerts for all findings
```

---

## API reference

Full OpenAPI spec at `http://localhost:8000/docs` once the server is running.
Quick reference: `GET /api/companies`, `/api/products`, `/api/regulations`, `/api/findings`,
`/api/alerts`, `/api/audit` — plus `POST /api/alerts/preview` and `/api/alerts/resend`.

See [`frontend-app/BACKEND_INTEGRATION.md`](frontend-app/BACKEND_INTEGRATION.md) for the
exact shapes each endpoint must return.

---

## Dataset

The portfolio is **entirely fabricated** — `@example.com` emails and placeholder phone numbers.
No test alert will reach a real person. Use your own Twilio number for demos.

- 22 companies · 53 products · 3 active EU rules in catalog
- See [`backend-app/DATASET_README.md`](backend-app/DATASET_README.md) for the full data dictionary
- See [`backend-app/SOURCES.md`](backend-app/SOURCES.md) for live regulatory sources

---

*GDGoC TUM Campus Heilbronn · GenAI Builders Day · partner challenge by EcoComply · IBM Bob + Twilio*
