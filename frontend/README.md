# Frontend

React + Vite + TypeScript frontend for the EAI Fruit Keeper demo.

The app currently includes four routed pages:

- Today home dashboard
- Inventory
- Shopping advice and Ask AI
- Profile

## Commands

```powershell
npm install
npm run dev
npm run typecheck
npm run build
npx vitest run
```

## Local API

During development, frontend requests use `/api/*`. Vite proxies those requests to the local backend:

```text
http://127.0.0.1:8000
```

For a deployed frontend, set `VITE_API_BASE_URL` to the backend origin, for example:

```powershell
$env:VITE_API_BASE_URL="http://eai.744477.xyz"
npm run build
```

The API client appends `/api/*` automatically, so both `http://127.0.0.1:8000` and
`http://127.0.0.1:8000/api` are accepted.

Current deployed API:

```text
Base URL: http://eai.744477.xyz/api
Docs: http://eai.744477.xyz/api/docs
Health: GET http://eai.744477.xyz/api/health
```

The MVP has four pages: home, inventory, advice, and profile. Shopping reminders stay
inside the advice page instead of a separate shopping page.
