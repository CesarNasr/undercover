# Status

Phases 1–3 complete: API-only agent, background runs, progress events and restart
recovery, plus persistent business API, decisions, handler sign-off and
transactional simulated payments. Thirteen Python tests pass with 99% coverage.
Pilot implementation continues.

## Local checks

- The accessibility lint plugin uses version 0.2 or later for ESLint flat config compatibility. Avoid `npm audit fix --force`, which can downgrade it to an incompatible version.
- Playwright starts its own dashboard on port 5174 so it does not reuse an unrelated app on the usual development port 5173.
- The latest dependency audit reports six moderate advisories and no high or critical advisories. Forced fixes propose incompatible plugin downgrades; these advisories remain unresolved.
