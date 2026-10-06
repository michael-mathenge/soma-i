# SOMA.i Codex Accelerator Capstone Spec

## Outcome

Strengthen the existing SOMA.i proof of concept around one learner journey: Amina Demo completes a Data Analyst checkpoint and can see how her progress leads to relevant learning and a possible next step. Treat the biography and the 2–3 week drop-off problem in `PRODUCT_BRIEF.md` as assumptions, not research findings. Do not build real SMS delivery, accounts, live opportunity aggregation, or deployment.

## Interfaces

- A direct visit or reload of `/next` must render the same result data shape and useful content as arriving there after checkpoint completion: unlocked skill, next checkpoint, low-data reading picks, and matched sample opportunities.
- Keep seeded opportunities visibly labelled as samples. Keep reminder delivery on the existing console sender.
- Add no public user-facing route unless required to supply that `/next` result consistently; if the backend response changes, keep its fallback payload aligned with the checkpoint completion response.

## Acceptance criteria

1. **Fixture-backed pathway relevance:** From the repository root, `python -m pytest backend` passes and includes offline fixture coverage showing relevant RSS-derived learning items for Data Analyst, Web Developer, and Digital Marketing Assistant. Tests make no network requests.
2. **Direct `/next` fallback:** From `frontend`, `npm run test:e2e` passes a Playwright case that opens `/next` without checkpoint response data and verifies matched sample opportunities appear with the fallback result.
3. **Reminder skill and Scheduled task:**
   - **Repo-verifiable:** Confirm `.agents/skills/soma-reminder-ops/SKILL.md` exists. On a fresh local SQLite database, run `python backend\manage.py migrate` and `python backend\manage.py seed_demo` from the repository root. Because reminders are opt-in, enable weekly reminders for Amina Demo in Settings, then run `python backend\manage.py send_reminders`. The console prints Amina's reminder and `Sent 1 reminder(s).`; running the same command again within seven days prints `Sent 0 reminder(s).` and no Amina reminder.
   - **MANUAL — external app state:** In the Codex App, open Automations and verify `SOMA.i Reminder Dispatch` is active. Select **Run now** and verify it completes without approval prompts. The Codex App must stay open for the local Scheduled task to run. Record the task prompt, schedule, date of the **Run now**, output summary, and screenshot path in `docs/SCHEDULED_TASK.md`.
4. **Build and browser checks:** `npm run build` and `npm run test:e2e`, run from `frontend`, both complete successfully.
5. **Amina end-to-end journey:** Starting with a fresh local SQLite database, run `python backend\manage.py migrate` and `python backend\manage.py seed_demo` from the repository root. Then run `npm run test:e2e` from `frontend`. Playwright signs in as the seeded Amina Demo, submits her current Data Analyst checkpoint, and verifies on the same result screen that the next skill is unlocked, low-data reading picks and matched sample opportunities appear, her flow starts in English, and changing to Kiswahili still works.

## Ordered implementation tasks

1. Fix `/next` hydration so direct navigation and reload recover the checkpoint result, including matched sample opportunities for the most recently unlocked skill.
2. Align configured RSS content, keyword-to-skill coverage, and seeded learning items so each of the three pathways has relevant reading. Preserve source traceability and fixture-only network-free tests.
3. Create a reusable Codex skill at `.agents/skills/soma-reminder-ops/SKILL.md`, named **SOMA.i Reminder Ops**. It should explain the weekly due rule, bilingual message checks, pre-run safeguards, and console-only operation; it must not claim to preview or send real SMS unless that behavior is later implemented.
4. Create a local Codex Scheduled task named **SOMA.i Reminder Dispatch** that runs `python backend\manage.py send_reminders` daily at 09:00 Africa/Nairobi. Keep the console sender as the default. Confirm **Run now** completes without approval prompts, document that the Codex App must stay open for scheduled runs, and create `docs/SCHEDULED_TASK.md` to record the task prompt, schedule, **Run now** date, output summary, and screenshot path.
5. Add backend regression coverage for fixture-backed pathway relevance, reminder selection/message limits, and the data needed by `/next` fallback. Keep tests offline.
6. Add a Playwright test using the seeded Amina Demo journey. Verify checkpoint submission, unlocked next skill, low-data picks, matched sample opportunities on the same result screen, and Kiswahili language continuity. Also cover direct `/next` navigation without stored completion data.
7. Add a README section titled **Built with Codex** that accurately describes Codex’s role in implementation, reusable skill creation, scheduled reminder operation, and test-backed iteration. Update the README demo instructions to point to the capstone flow.
8. Create `DEMO_SCRIPT.md` as a separate artifact and update `docs/PLANS.md` with capstone status and validation results.

## Validation commands

Use only these repository commands and their documented working directories:

```powershell
# Repository root: backend tests and fresh demo data
python -m pytest backend
python backend\manage.py migrate
python backend\manage.py seed_demo
python backend\manage.py send_reminders

# Frontend directory: production build and Playwright flow
npm run build
npm run test:e2e
```

The local Scheduled task is additionally checked in the Codex App through the **Automations → SOMA.i Reminder Dispatch → Run now** click path. It must finish without an approval prompt; the Codex App must remain open for the task to run on schedule.
