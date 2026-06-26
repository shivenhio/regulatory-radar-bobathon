## Regulatory Radar — Frontend Scaffold

Build a Stretch-tier compliance dashboard in the chosen **Command Console** direction (dark navy, Libre Baskerville + IBM Plex Sans, fixed left sidebar, KPI strip, dense findings table, 12-month timeline). Auth-gated via Lovable Cloud (email/password). Mock data + typed API client stub so you can later swap to your real REST backend with one env var.

### Design system (locked from chosen direction)

- Palette tokens in `src/styles.css`:
  - `--navy-950 #0f1b3d`, `--navy-800 #1e3a5f`, `--navy-600 #3b6fa0`, `--navy-100 #e8edf3`
  - `--status-red #ef4444`, `--status-amber #f59e0b`, `--status-green #10b981`
  - Map to semantic shadcn tokens (background = navy-950, card = navy-800, border = navy-600/20, primary = navy-600).
- Fonts loaded via `<link>` in `src/routes/__root.tsx`: Libre Baskerville (serif headings) + IBM Plex Sans (sans body). Registered in `@theme` as `--font-serif` / `--font-sans`.
- Status pills, KPI cards, sidebar nav item, sticky top bar — reuse the prototype's structure verbatim.

### Pages / routes

```
src/routes/
  __root.tsx                      head + fonts + QueryClient
  index.tsx                       redirect → /dashboard
  auth.tsx                        email/password sign in + sign up
  _authenticated/
    route.tsx                     (managed by Cloud integration) gate → /auth
    route.tsx wraps AppShell      sidebar + top bar + <Outlet/>
    dashboard.tsx                 KPI strip, findings table, 12m timeline
    companies.index.tsx           CompanyList table
    companies.$companyId.tsx      profile + products + Gaps/Upcoming/History tabs
    products.index.tsx            ProductList
    products.$productId.tsx       attributes + regulations grouped by family
    regulations.index.tsx         RegulationExplorer with family/status filters
    regulations.$regulationId.tsx articles, deadlines, affected counts
    alerts.tsx                    AlertsTable + re-send + preview form (EN/DE)
    audit.tsx                     activity log list
```

Each route gets distinct `head()` metadata.

### Component layout

```
src/components/
  layout/
    AppShell.tsx                  sidebar + top bar wrapper
    Sidebar.tsx                   nav items, active state from useRouterState
    TopBar.tsx                    page title + filter chips + export btn
  dashboard/
    KpiStrip.tsx                  6 cards
    FindingsTable.tsx             sortable, filterable (company/family/status/market)
    DeadlineTimeline.tsx          12m vertical timeline
  findings/
    StatusPill.tsx                red/amber/green semantic
    FindingRow.tsx
  companies/  CompanyList, CompanyDetail, CompanyTabs
  products/   ProductList, ProductDetail, RegulationsByFamily
  regulations/ RegulationList, RegulationDetail, ArticleList
  alerts/     AlertsTable, AlertPreviewForm (language toggle EN/DE), ResendButton
  audit/      ActivityList
  ui/...      existing shadcn (Table, Tabs, Select, Input, Badge, Card, Dialog)
```

### Data layer (mock + API client stub)

```
src/lib/api/
  client.ts        fetch wrapper; reads import.meta.env.VITE_API_BASE_URL; if unset → mock mode
  types.ts         Company, Product, Regulation, Finding, Alert, AuditEvent
  companies.ts     getCompanies(), getCompany(id)
  products.ts     getProducts(), getProduct(id)
  regulations.ts  getRegulations(), getRegulation(id)
  findings.ts     getFindings(filters?), dedupeFindings(), prioritizeByRisk()
  alerts.ts       getAlerts(), resendAlert(id, language), previewAlert(id, language)
  audit.ts        getAuditEvents()
src/lib/mock/
  companies.json, products.json, regulations.json, findings.json (sampleexpectedoutput shape), alerts.json, audit.json
```

Every API function is a TanStack Query `queryOptions` factory; routes prime cache via `ensureQueryData` and components read with `useSuspenseQuery`.

### Stretch behaviors (built in from day 1)

- **Dedupe**: `dedupeFindings()` merges findings sharing `(company, product, regulation.id)`; keeps an array of `sourceUrls`.
- **Risk priority**: `prioritizeByRisk()` sorts by `(deadline passed desc, high-risk-substance flag, days-to-deadline asc)`.
- **Multi-language alerts**: `AlertPreviewForm` has EN/DE toggle; `resendAlert(id, lang)` and `previewAlert(id, lang)` pass language code to backend.

### Auth

- Lovable Cloud enabled; email/password only, no profile table.
- `/auth` page with sign-in + sign-up tabs, redirects to `/dashboard` on success.
- All app routes live under `_authenticated/` so Cloud's managed gate handles redirect to `/auth`.

### Step-by-step backend hookup guide (delivered as `BACKEND_INTEGRATION.md` at the end)

Each `src/lib/api/*.ts` function will have a `// TODO: replace mock with` comment showing the exact `client.get('/findings', ...)` call to enable. Set `VITE_API_BASE_URL` → flip from mock to live, one file at a time.

### Build order

1. Enable Lovable Cloud + email/password auth.
2. Design tokens + fonts in `styles.css` + `__root.tsx`.
3. `AppShell` + Sidebar + TopBar + `_authenticated` layout.
4. Mock data files + types + API client stub + query options.
5. `/dashboard` (KpiStrip + FindingsTable + DeadlineTimeline) — the hero page.
6. Companies list + detail with tabs.
7. Products list + detail grouped by family.
8. Regulations explorer + detail.
9. Alerts center with re-send + EN/DE preview form.
10. Audit log.
11. `/auth` page + redirect wiring.
12. `BACKEND_INTEGRATION.md` walkthrough.

### Out of scope

- Calling Twilio directly (always goes through your backend).
- Live scraping logic.
- Profile/roles table (auth only).
