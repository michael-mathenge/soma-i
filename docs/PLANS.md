# SOMA.i milestones

Update each status and validation result as work progresses. All work is on a milestone feature branch; do not commit directly to `main`.

| Milestone | Status | Validation |
|---|---|---|
| M0 Bootstrap and project guide | done | Fresh `.env` setup, migrations, `seed_demo`, and `manage.py check` pass; `/api/health/` returns `{"status":"ok"}`. |
| M1 Content, RSS ingestion, and sources | done | Fixture ingestion/dedupe/tag/traceability tests pass; live run parsed 50 MIT News, 10 freeCodeCamp, and 71 MDN entries. |
| M2 Pathways, learner progress, and checkpoints | done | Progress and low-data recommendation tests pass; API covers completion, skip, restart, switch, and quiz storage. |
| M3 Opportunities and next steps | done | Skill-overlap and What's Next payload tests pass; demo seeds 10 labelled Kenya examples. |
| M4 Bilingual reminders | done | Tests cover opt-in/due selection, English and Kiswahili copy, and <=160 characters. |
| M5 Frontend, i18n, accessibility, and offline shell | done | ESLint passes; `npm run build` reports 106.0 KB gzipped JS+CSS (<200 KB); Playwright journey passes in English and Kiswahili. |
| M6 Demo, documentation, and acceptance | done | Fresh SQLite setup and demo seed pass; `pytest` (8 passed), Ruff, Black, ESLint, production build, and bilingual Playwright smoke pass. Live feed ingestion parsed 50 MIT News, 10 freeCodeCamp, and 71 MDN entries on 2026-10-02. |
| M7 Direct `/next` hydration | done | `python -m pytest backend` (11 passed); frontend `npm run build` (106.1 KB gzipped JS+CSS); `npm run test:e2e` (3 passed, including direct `/next` and bilingual no-learner empty states; used installed Chrome). |
| M8 Repeatable demo seed and reminders | done | `\.venv\Scripts\python.exe -m pytest backend` (13 passed); `\.venv\Scripts\python.exe backend\manage.py seed_demo` left counts at Amina 1, Data Analyst 1, Web Developer 1, Digital Marketing Assistant 1; with `$env:SOMA_SENDER='console'`, `\.venv\Scripts\python.exe backend\manage.py send_reminders` printed Amina's English reminder and `Sent 1 reminder(s).`; duplicate-row regression confirms pre-existing extras remain untouched. |
| M9 Local `.env` setup and branch consolidation | done | `.env.example` copies with a non-empty local Django secret; `\.venv\Scripts\python.exe -m pytest backend` (13 passed); `npm run build` (106.1 KB gzipped JS+CSS); `npm run test:e2e` (3 passed using installed Chrome). |

## Capstone working rules - 2026-10-11

- Branch: `docs/working-rules`; contributor guide now records one chat per branch, labelled copyable blocks, complete PR and extended merge descriptions, and restrictions on editing, Git operations, reviews, unattended commands, and evidence claims.
- New-computer checks: Python 3.13.7; backend suite 117 passed (four existing database-override warnings); frontend build 106.2 KB gzipped JS+CSS; database guard 16 passed, one Windows symlink-permission skip.
- Commit tested: `e1cc885030a37bfae6dcb930356c9e33ec0f5ef4`, matching main application code; documentation edits were present on `docs/working-rules`.
- T1: 16 Playwright tests passed, but exit code 1 from teardown `EBUSY` while removing temporary SQLite. Overall check blocked by cleanup. The inherited `PYTHON` variable pointed at a missing Python312 directory; the run used `C:\dev\soma-i\.venv\Scripts\python.exe` outside the sandbox.
- T2-T4: backend 117 passed; guard 16 passed and one skipped; build 106.2 KB, below 200 KB.
- T5: Black 68 files unchanged; Ruff all checks passed (outside sandbox, Black with one worker).
- E6/E7: request-count tests passed, with one pathways request observed for each relevant load in server logs. Required UI Network screenshots remain pending; the external tracker was inaccessible and has not been edited.

## Later

- Production SMS provider delivery and durable user accounts.
- Broader curated feed and live opportunity aggregation.
- Cross-device synchronization and deployment hardening.
