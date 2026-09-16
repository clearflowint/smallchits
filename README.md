# Small Chits Workflow Automation — ClearFlow Automations

Production-grade SaaS platform to digitize and automate traditional 20-month community Chit Fund ("Chitti") savings circles.

> Grounded on an isolated `Share_ID` data model, a pure Python math engine, a Vue.js 3 / Tailwind mobile-first PWA, and automated n8n background crons.

## Stack

| Layer | Technology |
|---|---|
| Mobile UI / PWA | Vue.js 3 + Tailwind CSS |
| Backend REST API | FastAPI (Python 3.12) |
| Relational DB | NocoDB (Docker) — **not included here**, connect to your own instance |
| Automation Engine | n8n (Docker) |
| Reverse Proxy / SSL | Caddy |
| DevOps | Docker Compose + GitHub Actions |

## Repository layout

```
clearflow-chits/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── core/             config, security (Google OAuth), NocoDB client
│   │   ├── routers/          API route modules
│   │   ├── services/         math engine, cycle spawning, whatsapp/drive services
│   │   ├── models.py          Pydantic schemas
│   │   └── main.py
│   ├── tests/                 pytest unit tests for the math engine
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 Vue 3 + Tailwind PWA
│   ├── src/
│   │   ├── views/             Page 1 (Home/Cards) & Page 2 (Summary/Hub)
│   │   ├── components/        PaymentDrawer, ShareCard, DrawControl, etc.
│   │   ├── composables/       useAuth, useApi
│   │   └── router/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
├── n8n/
│   └── workflows/             exportable n8n workflow JSON (D-2, D+10, D+20 crons)
├── Caddyfile
├── docker-compose.yml
├── .env.example
└── docs/
    ├── NOCODB_SCHEMA.md       full table/field spec (build this yourself in NocoDB)
    └── API.md                 endpoint reference
```

## Quick start

```bash
cp .env.example .env
# fill in NOCODB_BASE_URL, NOCODB_API_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, etc.
docker compose up -d --build
```

- Frontend PWA → `https://your-domain` (via Caddy)
- Backend API → `https://your-domain/api`
- n8n → `https://your-domain/n8n` (protect this route!)
- NocoDB → configure separately, point `NOCODB_BASE_URL` at it

See `docs/NOCODB_SCHEMA.md` for the exact tables/columns this code expects.
