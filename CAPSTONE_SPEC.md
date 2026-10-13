# SOMA.i Codex Accelerator Capstone Spec

## Original capstone outcome

Strengthen the existing SOMA.i proof of concept around one learner journey: Amina Demo completes a Data Analyst checkpoint and can see how her progress leads to relevant learning and a possible next step. Treat the biography and the 2–3 week drop-off problem in `PRODUCT_BRIEF.md` as assumptions, not research findings. Do not build real SMS delivery, accounts, live opportunity aggregation, or deployment.

## Interfaces

- A direct visit or reload of `/next` must render the same result data shape and useful content as arriving there after checkpoint completion: unlocked skill, next checkpoint, low-data reading picks, and matched sample opportunities.
- Keep seeded opportunities visibly labelled as samples. Keep reminder delivery on the existing console sender.
- Add no public user-facing route unless required to supply that `/next` result consistently; if the backend response changes, keep its fallback payload aligned with the checkpoint completion response.

## Acceptance criteria

1. **Fixture-backed pathway relevance:** From the repository root, `\.venv\Scripts\python.exe -m pytest backend` passes and includes offline fixture coverage showing relevant RSS-derived learning items for Data Analyst, Frontend Developer, and Backend/Python Developer. Tests make no network requests.
2. **Direct `/next` fallback:** From `frontend`, `npm run test:e2e` passes a Playwright case that opens `/next` without checkpoint response data and verifies matched sample opportunities appear with the fallback result.
3. **Reminder skill and Scheduled task:**
   - **Repo-verifiable:** Confirm `.agents/skills/soma-reminder-ops/SKILL.md` exists. On a fresh OS-temp SQLite database, run `\.venv\Scripts\python.exe backend\manage.py migrate` and `\.venv\Scripts\python.exe backend\manage.py seed_demo` from the repository root. The current seed opts Amina Demo into English weekly reminders; verify that preference in Settings, then run `\.venv\Scripts\python.exe backend\manage.py send_reminders`. The console prints Amina's reminder and `Sent 1 reminder(s).`; running the same command again within seven days prints `Sent 0 reminder(s).` and no Amina reminder.
   - **MANUAL — external app state:** The implemented schedule reports reminder alerts through `reminder_ops`; docs/SCHEDULED_TASK.md records a successful run followed by an intentional pause of its hourly schedule. Present that historical result and paused state accurately. Do not claim an active daily dispatch, production delivery, or live Gmail verification. Any new run must use an explicitly configured OS-temp database and printed DATABASE_URL; the Codex App must stay open for local scheduled runs.
4. **Build and browser checks:** `npm run build` and `npm run test:e2e`, run from `frontend`, both complete successfully.
5. **Amina end-to-end journey:** Starting with a fresh OS-temp SQLite database, run `\.venv\Scripts\python.exe backend\manage.py migrate` and `\.venv\Scripts\python.exe backend\manage.py seed_demo` from the repository root. Rehearse the seeded Amina Demo journey in the browser: submit her current Data Analyst checkpoint and inspect the unlocked skill, low-data reading picks and labelled sample opportunities on the result screen, starting in English and switching to Kiswahili. Separately run `npm run test:e2e` from `frontend`: the existing bilingual checkpoint test creates new learners, while the direct `/next` test uses the demo session. Do not describe that automated coverage as a complete seeded-Amina checkpoint test.

## Ordered implementation tasks

1. Fix `/next` hydration so direct navigation and reload recover the checkpoint result, including matched sample opportunities for the most recently unlocked skill.
2. Align configured RSS content, keyword-to-skill coverage, and seeded learning items so each of the three pathways has relevant reading. Preserve source traceability and fixture-only network-free tests.
3. Create a reusable Codex skill at `.agents/skills/soma-reminder-ops/SKILL.md`, named **SOMA.i Reminder Ops**. It should explain the weekly due rule, bilingual message checks, pre-run safeguards, and console-only operation; it must not claim to preview or send real SMS unless that behavior is later implemented.
4. Document the implemented hourly reminder-alert schedule and its successful historical run in `docs/SCHEDULED_TASK.md`. Keep its paused state explicit, console delivery as the default, and live Gmail as not tested. The original daily dispatch proposal was superseded by the documented alert workflow; do not activate it solely for a submission recording.
5. Add backend regression coverage for fixture-backed pathway relevance, reminder selection/message limits, and the data needed by `/next` fallback. Keep tests offline.
6. Preserve the existing bilingual onboarding and direct-demo `/next` tests. Complete the seeded Amina Demo journey as a separate rehearsal; a dedicated automated seeded-Amina checkpoint test is not currently present. Verify checkpoint submission, unlocked next skill, low-data picks, matched sample opportunities on the same result screen, and Kiswahili language continuity. Also cover direct `/next` navigation without stored completion data.
7. Add a README section titled **Built with Codex** that accurately describes Codex’s role in implementation, reusable skill creation, scheduled reminder operation, and test-backed iteration. Update the README demo instructions to point to the capstone flow.
8. Create `DEMO_SCRIPT.md` as a separate artifact and update `docs/PLANS.md` with capstone status and validation results.

## Validation commands

Run from C:/dev/soma-i in PowerShell. Stop if temporary-directory creation fails; never fall back to a repository database. These commands are a rehearsal checklist; their next execution is not tested yet.

**PowerShell — isolated backend validation and reminders**

```powershell
$ErrorActionPreference = 'Stop'
Set-Location C:/dev/soma-i
$rehearsalDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('somai-rehearsal-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $rehearsalDirectory -ErrorAction Stop | Out-Null
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $rehearsalDirectory 'demo.sqlite3').Replace('\', '/')
$env:SOMA_SENDER = 'console'
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Migrations failed' }
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw 'Seed failed' }
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe -m pytest backend
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py send_reminders
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py send_reminders
```

**PowerShell — frontend checks, with ports 8127/4177 free**

```powershell
Set-Location C:/dev/soma-i/frontend
npm run test:e2e:guard
npm run test:e2e:robustness
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:e2e
```

Record actual rehearsal outputs and screenshot locations in docs/PLANS.md. Preserve historical scheduled-task evidence; its paused state is the current documented state. Tracker updates and E6/E7 Network screenshots are optional supporting material under the supplied challenge guidelines.
