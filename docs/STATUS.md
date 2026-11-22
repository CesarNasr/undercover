# Status

The local claims pilot is implemented: 25 claims in a persistent SQLite queue,
full claim/policy/customer records, an API-only LangChain agent, live activity,
read-only instructions, handler sign-off and simulated payments.

The backend independently blocks payouts above $1,000 until an eligible handler
signs off. The payment must match the stored approval exactly and can happen
only once. Decisions, sign-offs, activity and payments survive restart.

## Setup and run

Use Python 3.12, uv and Node 26. At the repository root:

```text
uv sync
npm install
npm run dev
```

Open http://localhost:5173. The backend is at http://localhost:8000 and its API
schema is at http://localhost:8000/docs. Select a claim and choose **Run agent**.
An over-limit approval needs a handler selection and **Sign off payout**, then
**Record simulated payment**. An unpaid approval can retry payment without
rerunning the decision.

Put `OPENROUTER_API_KEY` in the root `.env`. The default model is
`openai/gpt-6-luna` with low reasoning effort. Set `MODEL_NAME` to override it,
for example `openrouter/free`. The agent's `BACKEND_URL` defaults to
`http://localhost:8000`; change it only when running the API elsewhere.

## Persistence and reset

The ignored local database is `data/pilot.sqlite3`. `UNDERCOVER_DB` can select an
alternate database file. Startup inserts missing seed records without replacing
saved work. To deliberately reset all local decisions, stop the backend and
remove `data/pilot.sqlite3` with your file explorer, then restart. This loses all
local run activity, decisions, sign-offs and simulated payments.

Runs execute in the backend process and are not durable. Restarting releases an
interrupted undecided claim for an explicit retry. A saved approval survives a
failure and permits payment retry. A referral is a completed agent decision
requiring human review; this pilot does not implement subsequent adjudication.
Handler selection attributes sign-off; there is no authentication in this pilot.

## Checks

```text
npm run check
```

The suite includes 16 Python tests, 11 component tests and five Chromium
scenarios. Python coverage is 99.66%; dashboard statement coverage is 97.16%.
The browser suite starts an isolated temporary database and a scripted LangChain
model through `e2e/server.py`; it never reuses a development backend. No automated
check calls OpenRouter. Screenshots are written to ignored `e2e/test-results/`.
Desktop and 390px mobile layouts have been inspected.

The policy wording is the agent's only coverage-rule source. The claims manual,
evaluation answer keys, held-out claims and security test data are not loaded.
No accuracy score or live-model quality claim has been established. No real
payments, customer messages, sign-in, cloud resources or later-day features exist.

## Local checks

- The accessibility lint plugin uses version 0.2 or later for ESLint flat config
  compatibility. Avoid `npm audit fix --force`, which can downgrade it to an
  incompatible version.
- Playwright starts its dashboard on port 5174 and its isolated backend on 8000;
  stop a development backend on 8000 before running browser checks.
- Dependency setup reports six moderate advisories and no high or critical
  advisories. Forced fixes propose incompatible plugin downgrades; these remain
  unresolved.
