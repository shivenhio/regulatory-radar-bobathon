# Backend integration guide

The frontend ships with mock data so every screen demos out of the box. Wiring
your real REST backend is one env var + light edits per resource.

## 1. Point the client at your backend

In project root, set:

```
VITE_API_BASE_URL=https://your-backend.example.com
```

Once set, `src/lib/api/client.ts` flips out of mock mode. Any `client.get(...)`
calls will hit your backend.

## 2. Expected endpoints

| Method | Path | Returns |
| --- | --- | --- |
| GET  | `/api/companies`              | `Company[]` |
| GET  | `/api/companies/:id`          | `Company`   |
| GET  | `/api/products?companyId=X`   | `Product[]` |
| GET  | `/api/products/:id`           | `Product`   |
| GET  | `/api/regulations`            | `Regulation[]` |
| GET  | `/api/regulations/:id`        | `Regulation`   |
| GET  | `/api/findings?...`           | `Finding[]` (matches `sampleexpectedoutput.json`) |
| GET  | `/api/alerts`                 | `AlertRecord[]` |
| POST | `/api/alerts/preview`         | `{ message }` — body `{ findingId, language }` |
| POST | `/api/alerts/resend`          | `{ ok, alertId }` — body `{ findingId, language }` |
| GET  | `/api/audit`                  | `AuditEvent[]` |

Types are defined in `src/lib/api/types.ts` — match those shapes exactly.

## 3. Per-file wiring

Each `src/lib/api/*.ts` already has a working `client.get(...)` fallback path
that runs once `VITE_API_BASE_URL` is set. The mock branch (`if (isMockMode)`)
can stay for offline demos.

To go fully live, you can also delete the mock import + the `isMockMode`
branch from each file once your backend is stable.

## 4. Alerts → Twilio

`previewAlert(findingId, language)` and `resendAlert(findingId, language)`
should be **your backend endpoints** that internally call Twilio. The
frontend just passes the language code (`"en"` or `"de"`); your backend can
ask Bob for a translated template.

## 5. Auth

Sign in is handled by Lovable Cloud (email/password). Your backend doesn't
need to verify the Supabase JWT for the demo, but if you want to, the bearer
token is on `supabase.auth.getSession()` client-side.
