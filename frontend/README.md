# Rooftop Energy Estimator — Frontend

React 18 + TypeScript (strict) + Vite SPA. Auth + dashboard are implemented; the
analysis wizard, processing and results screens are scaffolded as placeholders.

## Stack

React 18 · TypeScript strict · Vite · MUI v5 · TanStack Query v5 · React Hook
Form + Zod · React Router v6 · MapLibre GL · Recharts · Vitest + RTL · ESLint +
Prettier. HTTP via a typed `fetch` wrapper.

## Scripts

```bash
npm run dev        # start dev server (Vite)
npm run build      # tsc --noEmit + vite build
npm run preview    # preview production build
npm run test       # vitest (watch)
npm run test:run   # vitest run (CI)
npm run lint       # eslint (max-warnings 0)
npm run format     # prettier --write
npm run typecheck  # tsc --noEmit
```

Set `VITE_API_URL` (see `.env.example`); defaults to `http://localhost:8000/api/v1`.

## Layout (`src/`)

```
api/        typed fetch client (auth injection, 401 refresh+retry, error envelope),
            QueryClient, typed query/mutation wrappers, query keys
schemas/    Zod schemas = single source of truth for RHF validation + TS types;
            STAGE_LABELS for the 20 pipeline stages
types/      DTO types re-exported (inferred from schemas)
components/ presentational MUI components (LoadingState, ErrorState, EmptyState,
            PageContainer, StatusChip, StageProgress, DisclaimerBanner, FormTextField,
            PlaceholderPage) — no data fetching
features/   auth/, projects/ — each: api.ts, hooks.ts, components/
hooks/      useAuth (AuthProvider), usePolling
maps/       bbox/zoom helpers for the bounded /features/ endpoint
theme/      MUI theme + light/dark/system mode context + toggle
layout/     AppShell, AuthLayout, UserMenu
pages/      route-level pages
routes/     paths, ProtectedRoute, featureRoutes (seam), AppRouter
```

## Seam for the wizard / processing / results engineer

- Route constants + path builders: `src/routes/paths.ts` (`ROUTES`, `buildPath`).
- Registry: `src/routes/featureRoutes.tsx` — add screens here; do NOT edit
  `AppRouter.tsx` or `ProtectedRoute.tsx`.
- Replace the BODY of these placeholder pages (keep export names + route params):
  `pages/ProjectDetailPage.tsx`, `pages/NewAnalysisPage.tsx`,
  `pages/ProcessingPage.tsx`, `pages/ResultsPage.tsx`.
- Reuse: `usePolling` (job polling), `StageProgress` + `STAGE_LABELS` (progress),
  `DisclaimerBanner` (DEC-02, mandatory on results), the schemas in `@/schemas`,
  and the `http`/`parseResponse`/`useApiQuery`/`useApiMutation` API layer.
