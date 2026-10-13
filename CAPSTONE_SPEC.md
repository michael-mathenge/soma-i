# SOMA.i Codex Accelerator Capstone Spec

## Original capstone outcome

Strengthen the existing SOMA.i proof of concept around one learner journey: Amina Demo completes a Data Analyst checkpoint and can see how her progress leads to relevant learning and a possible next step. Treat the biography and the 2–3 week drop-off problem in `PRODUCT_BRIEF.md` as assumptions, not research findings. Do not build real SMS delivery, accounts, live opportunity aggregation, or deployment.

## Interfaces

- A direct visit or reload of `/next` must render the same result data shape and useful content as arriving there after checkpoint completion: unlocked skill, next checkpoint, low-data reading picks, and matched sample opportunities.
- Keep seeded opportunities visibly labelled as samples. Keep reminder delivery on the existing console sender.
- Add no public user-facing route unless required to supply that `/next` result consistently; if the backend response changes, keep its fallback payload aligned with the checkpoint completion response.

## Acceptance criteria

1. **Fixture-backed pathway relevance:** From the repository root, `\.venv\Scripts\python.exe -m pytest backend` passes and includes offline fixture coverage showing relevant RSS-derived learning items for Data Analyst, Web Developer, and Digital Marketing Assistant. Tests make no network requests.
2. **Direct `/next` fallback:** From `frontend`, `npm run test:e2e` passes a Playwright case that opens `/next` without checkpoint response data and verifies matched sample opportunities appear with the fallback result.
3. **Reminder skill and Scheduled task:**
   - **Repo-verifiable:** Confirm `.agents/skills/soma-reminder-ops/SKILL.md` exists. On a fresh local SQLite database, run `\.venv\Scripts\python.exe backend\manage.py migrate` and `\.venv\Scripts\python.exe backend\manage.py seed_demo` from the repository root. Because reminders are opt-in, enable weekly reminders for Amina Demo in Settings, then run `\.venv\Scripts\python.exe backend\manage.py send_reminders`. The console prints Amina's reminder and `Sent 1 reminder(s).`; running the same command again within seven days prints `Sent 0 reminder(s).` and no Amina reminder.
   - **MANUAL — external app state:** In the Codex App, open Automations and verify `SOMA.i Reminder Dispatch` is active. Select **Run now** and verify it completes without approval prompts. The Codex App must stay open for the local Scheduled task to run. Record the task prompt, schedule, date of the **Run now**, output summary, and screenshot path in `docs/SCHEDULED_TASK.md`.
4. **Build and browser checks:** `npm run build` and `npm run test:e2e`, run from `frontend`, both complete successfully.
5. **Amina end-to-end journey:** Starting with a fresh local SQLite database, run `\.venv\Scripts\python.exe backend\manage.py migrate` and `\.venv\Scripts\python.exe backend\manage.py seed_demo` from the repository root. Then run `npm run test:e2e` from `frontend`. Playwright signs in as the seeded Amina Demo, submits her current Data Analyst checkpoint, and verifies on the same result screen that the next skill is unlocked, low-data reading picks and matched sample opportunities appear, her flow starts in English, and changing to Kiswahili still works.

## Ordered implementation tasks

1. Fix `/next` hydration so direct navigation and reload recover the checkpoint result, including matched sample opportunities for the most recently unlocked skill.
2. Align configured RSS content, keyword-to-skill coverage, and seeded learning items so each of the three pathways has relevant reading. Preserve source traceability and fixture-only network-free tests.
3. Create a reusable Codex skill at `.agents/skills/soma-reminder-ops/SKILL.md`, named **SOMA.i Reminder Ops**. It should explain the weekly due rule, bilingual message checks, pre-run safeguards, and console-only operation; it must not claim to preview or send real SMS unless that behavior is later implemented.
4. Create a local Codex Scheduled task named **SOMA.i Reminder Dispatch** that runs `\.venv\Scripts\python.exe backend\manage.py send_reminders` daily at 09:00 Africa/Nairobi. Keep the console sender as the default. Confirm **Run now** completes without approval prompts, document that the Codex App must stay open for scheduled runs, and create `docs/SCHEDULED_TASK.md` to record the task prompt, schedule, **Run now** date, output summary, and screenshot path.
5. Add backend regression coverage for fixture-backed pathway relevance, reminder selection/message limits, and the data needed by `/next` fallback. Keep tests offline.
6. Add a Playwright test using the seeded Amina Demo journey. Verify checkpoint submission, unlocked next skill, low-data picks, matched sample opportunities on the same result screen, and Kiswahili language continuity. Also cover direct `/next` navigation without stored completion data.
7. Add a README section titled **Built with Codex** that accurately describes Codex’s role in implementation, reusable skill creation, scheduled reminder operation, and test-backed iteration. Update the README demo instructions to point to the capstone flow.
8. Create `DEMO_SCRIPT.md` as a separate artifact and update `docs/PLANS.md` with capstone status and validation results.

## Validation commands

Use only these repository commands and their documented working directories:

```powershell
# Repository root: backend tests and fresh demo data
.\.venv\Scripts\python.exe -m pytest backend
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py send_reminders

# Frontend directory: production build and Playwright flow
npm run build
npm run test:e2e
```

The local Scheduled task is additionally checked in the Codex App through the **Automations → SOMA.i Reminder Dispatch → Run now** click path. It must finish without an approval prompt; the Codex App must remain open for the task to run on schedule.

## Approved public-beta release contract - 2026-10-13

The owner-approved public-beta scope in PRODUCT_BRIEF.md supersedes the original capstone's account/deployment/route restrictions for the listed production tasks. The original capstone acceptance history remains above; it is not proof of current production readiness. Canonical pathway code currently defines Data Analyst, Frontend Developer and Backend/Python Developer (backend/pathways/constants.py:1-25), rather than the older pathway names in the historical criteria.

### Required release behavior

- English-first real RSS content with verified source rights, attribution, free access and dates. No scraping or full-article storage. Automatic topic-based pathway publication uses the coverage/curriculum thresholds in PRODUCT_BRIEF.md; original pathways are not exempt and new pathways are not limited to three.
- Mobile-first catalogue, onboarding, dashboard, reading/checkpoint/result and account/settings journeys. Guest access and skip/restart/switch remain available. Runtime JS/CSS gzip must be strictly below 204800 bytes; the existing budget command is frontend/scripts/report-gzip.js:15-19. UI incremental allowances total 35 KiB and are estimates, not measured results.
- Optional verified email/password accounts, CSRF-protected guest and account mutations, owner isolation, rate limits, secure cookies, production secrets/headers and a disabled shared demo endpoint. Free account recovery must be verified before release.
- Offline support caches only the public app shell/catalogue metadata; no personalized dashboard/profile responses or offline completion queue. Cross-user cache isolation and honest offline errors are release gates.
- Durable PostgreSQL, daily encrypted backups with seven-copy retention, a demonstrated isolated restore and proposed 24-hour RPO/RTO. Six-hour ingestion needs overlap prevention, bounded retries and operational failure reporting, independent of the owner's desktop.
- A verified zero-new-charge deployment on the existing domain, with explicitly disclosed quota/sleep/cold-start limits. The proposed Render/Neon/GitHub Actions/Brevo/Cloudflare R2 stack is a candidate, not verified eligibility or current pricing. Stop deployment if required free services cannot meet privacy and cost constraints.

### Additional quality gates

Existing pytest, Playwright, database-guard/robustness, lint, build, owner-only Black check and Ruff gates remain required; add a non-writing Prettier check. Tests use fixtures and no live network. Separate manual source verification must cover at least three independent publishers. Proposed axe checks must report zero known WCAG 2.2 AA violations and resolve applicable incomplete findings. Manual checks cover keyboard journeys, focus, announcements, 200% text zoom, 320 px reflow and NVDA. Warm mobile Lighthouse median of three runs must meet performance 90, accessibility 100, best practices 95 and public-page SEO 90; LCP at most 2.5 s, CLS at most 0.1, TBT at most 200 ms. These proposed gates are not tested.

The approved branch/file execution order and gate status live in docs/PLANS.md. No new product behavior or service is claimed implemented by this documentation amendment.
