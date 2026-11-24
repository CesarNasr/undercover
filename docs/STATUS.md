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
  policy references, and requests simulated payment. The CLI can process one
  waiting claim or all waiting claims sequentially and print saved decisions.
- **Dashboard:** Claims queue, full claim and customer/policy details, run controls,
  live activity, decisions, handler sign-off and payment retry. The read-only
  instructions screen describes the records the agent reads and displays its
  instructions followed by the policy wording from the backend.
- **E2E:** Playwright coverage of queue/detail navigation, instructions and policy
  wording, mobile layout, all decision outcomes, and over-limit sign-off/payment
  persistence, using an isolated database and scripted model.

### Main functions

| Location | Function | What it does |
| --- | --- | --- |
| `backend/store.py` | `initialize()` | Creates the SQLite table and inserts missing seed records without overwriting saved work. |
| `backend/store.py` | `database()` | Opens and closes a database transaction; serializes writes. |
| `backend/runs.py` | `start(claim_id, thread_id)` | Reserves a waiting claim and records the start of a run. |
| `backend/runs.py` | `execute(claim_id, thread_id)` | Calls the agent in the background and records completion or failure. |
| `backend/runs.py` | `recover()` | Releases interrupted runs when the backend restarts. |
| `backend/workflow.py` | `decide(claim_id, body)` | Validates the active run and stores its decision, payout and explanation. |
| `backend/workflow.py` | `sign_off(claim_id, body)` | Records an eligible handler's approval of an over-limit payout. |
| `backend/workflow.py` | `pay(claim_id, body)` | Checks the full approved amount and sign-off, then records one simulated payment. |
| `agent/main.py` | `run(claim_id, thread_id)` | Runs the LangChain agent for one claim and returns its final reply; decisions are saved through API tools. |
| `agent/cli.py` | `main(argv)`, `process_claim(client, claim)` | Select waiting claims, submit runs through the API, wait for completion and print decisions and counts. |
| `agent/main.py` | `model()` | Builds the OpenRouter model client using `MODEL_NAME` or the default model. |
| Inside `run()` | `read_context()`, `record_decision(...)`, `request_payment(amount)` | Agent tools that read evidence, save a decision and request payment through the backend. |
| `dashboard/src/api.ts` | `api<T>(path, body?)` | Fetches API data, or posts an action when a body is supplied. |
| `dashboard/src/` | `App()`, `ClaimDetail({ id })`, `Actions({ claim, onChange })`, `AgentInstructions({ instructions, wording })` | Render navigation/queue, claim detail, handler controls and the read-only instructions screen. |
| `e2e/server.py` | `scripted(claim_id, thread_id)` | Runs the real agent tools with scripted model replies for browser tests, without OpenRouter calls. |

## Setup and run

Use Python 3.12, uv and Node 26. At the repository root:

```text
uv sync
npm install
npm run dev
```

Open the dashboard URL printed by Vite, normally http://localhost:5173.
If that port is occupied, Vite may choose 5174 or another port. The backend is at http://localhost:8000 and its API
schema is at http://localhost:8000/docs. Select a claim and choose **Run agent**.
An over-limit approval needs a handler selection and **Sign off payout**, then
**Record simulated payment**. An unpaid approval can retry payment without
rerunning the decision.

Put `OPENROUTER_API_KEY` in the root `.env`. The default model is
`openai/gpt-6-luna` with low reasoning effort. Set `MODEL_NAME` to override it,
for example `openrouter/free`. The agent's `BACKEND_URL` defaults to
`http://localhost:8000`; change it only when running the API elsewhere.

### Run claims from the terminal

Keep `npm run dev` running, then use a second terminal at the repository root:

```text
uv run -m agent
uv run -m agent CLM-1001
```

The first command processes every waiting claim in the order returned by the
queue API, one at a time. The second processes only the named claim. Use an
actual ID from your queue; this seed data starts at `CLM-1001`, not `CLM-001`.
Both commands submit the same backend agent workflow used by the dashboard,
using the real OpenRouter model configured in the backend's `.env` (currently
`MODEL_NAME=openrouter/free`). Automated CLI tests mock HTTP and never call a
real model.

Each completed run prints the saved outcome, payout, queue state, explanation,
calculation and policy references. A final count reports decisions and skipped
claims. Existing decisions and active or sign-off-pending claims are skipped.
Over-limit payouts still require handler sign-off in the dashboard.

The CLI stops on a run without a decision or after waiting ten minutes, rather
than starting more claims after a failure. A timeout or Ctrl+C does not cancel
an already submitted backend run; check activity before retrying. If payment
fails after a decision is saved, inspect the payment state in the dashboard.

### Stop and restart

Keep the terminal running while using the dashboard. Press **Ctrl+C** there to
stop both servers. Run `npm run dev` again to restart them, including after
changing `.env`. Starting a second copy can fail because port 8000 is occupied;
stop the earlier copy in its terminal first.

### Database startup and reseeding

SQLite is a local file, so there is no separate database server to start. The
backend creates `data/pilot.sqlite3` on its first startup and seeds the 25 claims.
Later startups keep existing decisions, activity, sign-offs and payments. Refresh
the dashboard after restarting.

To create the database or insert missing seed records from the CLI without
starting the app, run this from the repository root (macOS or PowerShell):

```text
uv run python -c "from dotenv import load_dotenv; load_dotenv(override=True); from backend.store import initialize; initialize()"
```

This does not reset existing claims or update existing seeded wording/instructions.
A full reset reloads the current seed files and instructions into a new database.

### Clear and recreate the database

First stop the app with **Ctrl+C**. Resetting deletes all local decisions, run
activity, sign-offs and simulated payments; the seed files in `data/` and `.env`
are kept. For a backup, copy the database while the app is stopped before deleting
it. The commands below use the default database path.

macOS (zsh):

```bash
# Optional backup; use a new filename to keep an earlier backup.
cp data/pilot.sqlite3 data/pilot-backup.sqlite3
# Clear the local database.
rm -f data/pilot.sqlite3
# Recreate and seed it on startup.
npm run dev
```

Windows (PowerShell):

```powershell
# Optional backup; use a new filename to keep an earlier backup.
Copy-Item data/pilot.sqlite3 data/pilot-backup.sqlite3
# Clear the local database.
Remove-Item data/pilot.sqlite3 -ErrorAction SilentlyContinue
# Recreate and seed it on startup.
npm run dev
```

Skip the optional backup command if the database does not exist yet. After a
reset, the queue returns to 25 waiting claims, so decided claims can be run again.
To restore a backup, stop the app, copy the backup over `data/pilot.sqlite3`
(`cp` on macOS or `Copy-Item -Force` in PowerShell), and restart the app.

### Use a separate local database

`UNDERCOVER_DB` selects a different SQLite file; choose an existing parent folder.
For example, start a separate demo database without clearing the default one:

macOS:

```bash
export UNDERCOVER_DB=data/demo.sqlite3
npm run dev
# After stopping the app, return to the default database:
unset UNDERCOVER_DB
```

PowerShell:

```powershell
$env:UNDERCOVER_DB = "data/demo.sqlite3"
npm run dev
# After stopping the app, return to the default database:
Remove-Item Env:UNDERCOVER_DB
```

If `UNDERCOVER_DB` is also set in `.env`, remove that entry to return to the
default database: the app loads `.env` with override enabled. When backing up or
resetting an alternate database, substitute its actual file path in the commands.
SQLite files under `data/` are ignored by git. Browser tests use their own temporary file.

## Persistence and recovery

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
The suite includes 26 Python tests, 11 component tests and five Chromium
scenarios. Python coverage is 98.92%; dashboard statement coverage is 97.24%.
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

CLI update: 26 Python tests pass (including a CLI-to-backend-to-stub-model
integration test), with 100% coverage of `agent/cli.py`. Frontend checks pass.
The required full check stops at browser startup because the development backend
occupies port 8000; it was left running. No live model runs were started during
implementation.
