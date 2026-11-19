# Status

A hello-world skeleton with every check in place:

- `backend/`: one route, `GET /api/health`
- `agent/`: the entry point `run(claim_id, thread_id)`, with one tool that calls the health route
- `dashboard/`: one page that shows whether the backend is up
- `e2e/`: one test of that page

Nothing of UnderCover is built yet. Update this file as you build.

## Local checks

- The accessibility lint plugin uses version 0.2 or later for ESLint flat config compatibility. Avoid `npm audit fix --force`, which can downgrade it to an incompatible version.
- Playwright starts its own dashboard on port 5174 so it does not reuse an unrelated app on the usual development port 5173.
- The latest dependency audit reports six moderate advisories and no high or critical advisories. Forced fixes propose incompatible plugin downgrades; these advisories remain unresolved.
