# GeoForce dashboard

React + Vite + TypeScript UI styled with the Claude design tokens.

## Dev

```bash
# 1. Backend — agent SSE API
.venv/bin/uvicorn agent.api:app --host 0.0.0.0 --port 8765

# 2. Dashboard
cd dashboard
npm install
npm run dev
# open http://localhost:5173
```

Vite proxies `/api/*` → `http://localhost:8765`. Override with `VITE_API_BASE`.

## Build

```bash
npm run build
# output: dashboard/dist
```
