# Car Checker — web app

React + TypeScript single-page app for the Car Checker API. Design, screens and
conventions: [`../docs/08-frontend.md`](../docs/08-frontend.md).

Everything runs in Docker from the repository root; no local Node.js is needed.

```bash
make fe-up      # dev server on http://localhost:5173, /api proxied to the API
make fe-check   # type check, lint, format check, unit tests
make fe-e2e     # Playwright end-to-end tests (stack running)
make fe-types   # regenerate src/api/schema.d.ts after an API change
make fe-build   # production image (nginx, port 8080)
```

Inside the container (`make fe-npm c="..."` or `docker compose exec frontend sh`):

| Script              | What it does                        |
| ------------------- | ----------------------------------- |
| `npm run dev`       | Vite dev server                     |
| `npm run typecheck` | TypeScript, strict                  |
| `npm run lint`      | ESLint (React hooks rules included) |
| `npm run format`    | Prettier                            |
| `npm test`          | Vitest unit and component tests     |
| `npm run build`     | Production build into `dist/`       |

Demo account (after `docker compose exec api python -m app.cli seed --demo`):
`demo@example.com` / `Car-checker-2026`.
