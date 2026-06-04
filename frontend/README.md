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
