# Status

The local claims pilot is implemented: 25 claims in a persistent SQLite queue,
full claim/policy/customer records, an API-only LangChain agent, live activity,
read-only instructions, handler sign-off and simulated payments.

The backend independently blocks payouts above $1,000 until an eligible handler
signs off. The payment must match the stored approval exactly and can happen
only once. Decisions, sign-offs, activity and payments survive restart.

## Built

- **Backend:** FastAPI endpoints backed by SQLite, seeded business records,
  claim decisions and run activity, handler sign-off, and simulated payments
  with the $1,000 approval barrier and duplicate-payment protection.
- **Agent:** LangChain agent on OpenRouter with the `MODEL_NAME` override. Reads
  instructions, claims, policies, customer history, plans and policy wording
  through backend tools; records approve, decline or refer with a payout and
  policy references, and requests simulated payment.
- **Dashboard:** Claims queue, full claim and customer/policy details, run controls,
  live activity, decisions, handler sign-off and payment retry. The read-only
  instructions screen describes the records the agent reads and displays its
  instructions followed by the policy wording from the backend.
- **E2E:** Playwright coverage of queue/detail navigation, instructions and policy
  wording, mobile layout, all decision outcomes, and over-limit sign-off/payment
  persistence, using an isolated database and scripted model.

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

Final `npm run check` exited 0 on November 22, 2026.
The suite includes 16 Python tests, 11 component tests and five Chromium
scenarios. Python coverage is 99.66%; dashboard statement coverage is 97.24%.
The browser suite starts an isolated temporary database and a scripted LangChain
model through `e2e/server.py`; it never reuses a development backend. No automated
check calls OpenRouter. Screenshots are written to ignored `e2e/test-results/`.
Desktop and 390px mobile layouts have been inspected.

The policy wording is the agent's only coverage-rule source. The claims manual,
evaluation answer keys, held-out claims and security test data are not loaded.
No accuracy score or live-model quality claim has been established. No real
payments, customer messages, sign-in, cloud resources or later-day features exist.

## Local checks

- SonarJS 4.2.2 and the accessibility lint plugin 0.2.0 are pinned for ESLint
  10 compatibility. Older SonarJS 2.x uses the removed `eslintrc` Linter API;
  accessibility plugin 0.1.x also targets older ESLint versions. Avoid
  `npm audit fix --force`, which can downgrade these plugins incompatibly.
  Use `npm ci` to reproduce the checked-in dependency versions.
- Playwright starts its dashboard on port 5174 and its isolated backend on 8000;
  stop a development backend on 8000 before running browser checks.
- Dependency setup reports six moderate advisories and no high or critical
  advisories. Forced fixes propose incompatible plugin downgrades; these remain
  unresolved.

Lint dependency repair: Python and frontend checks pass with the pinned plugins.
The standard full command was blocked at browser startup by an existing server
on port 8000; all five browser scenarios passed with temporary configurations
on backend port 8001. The existing server was left running.

November 24 instructions-screen update: Python and frontend checks pass. All five
browser scenarios pass on isolated backend port 8001, including the expanded
read-only instructions and policy wording. The development backend on 8000 was
left running.
