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

## README submission documentation validation - 2026-10-12

- Branch: `codex/readme-submission`; starting HEAD `391881e` confirmed by `git branch --show-current` and `git log --oneline -3`. Only `README.md` and this validation log were edited; historical results above are retained.
- Command audit: `frontend/package.json` defines `lint`, `build`, `test:e2e`, `test:e2e:guard`, and `test:e2e:robustness`; `frontend/playwright.config.js` sets ports 8127/4177, `reuseExistingServer: false`, an isolated OS-temp SQLite URL, and optional `PLAYWRIGHT_CHANNEL`. `backend/soma/settings.py` uses `os.environ.setdefault` for `.env`, preserving the explicit temporary `DATABASE_URL`. PowerShell `Parser.ParseInput` accepted all nine README PowerShell blocks (`POWERSHELL_BLOCKS_PARSED=9`).
- Fresh setup: `./.venv/Scripts/python.exe backend/manage.py migrate` returned `MIGRATE_EXIT=0`; `seed_demo` returned `SEED_EXIT=0` and `Seeded pathways, demo items, 10 sample opportunities, and Amina Demo.` The URL printed before each management command was `sqlite:///C:/Users/micha/AppData/Local/Temp/somai-readme-7a584ca7-de8a-409b-a6a5-0f6b661222c5/demo.sqlite3`. No `.env` was overwritten and no dependencies were installed.
- Startup: `./.venv/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload` reused that setup database; `Invoke-RestMethod http://127.0.0.1:8000/api/health/` returned `{"status":"ok","service":"soma.i"}`. `npm run dev` printed Vite ready on 5173; a separately owned Vite process on 5179 returned `FRONTEND_HTTP=200` via `Invoke-WebRequest`. These are startup/HTTP checks, not app-screen observations.
- Backend: `./.venv/Scripts/python.exe -m pytest backend` returned `117 passed, 4 warnings in 19.75s`, `PYTEST_EXIT=0`, with the explicit temporary URL printed first. Warnings came from the four `test_reminder_ops_refuses_repository_database_paths` / `test_reminder_ops_refuses_uppercase_repository_database_paths` parameter cases. Installed `.venv` Python was 3.13.7; creating a Python 3.12 environment is not tested.
- Frontend: `npm run test:e2e:guard` returned 16 passed, one Windows symlink-permission skip, `GUARD_EXIT=0`; `npm run test:e2e:robustness` returned 14 passed, `ROBUSTNESS_EXIT=0`. Named coverage includes `teardown warns and resolves after four EBUSY failures` and `child ignores a folder PYTHON and starts the selected interpreter`. `npm run lint` returned `LINT_EXIT=0`; `npm run build` reported `Gzipped JS + CSS: 106.2 KB`, `BUILD_EXIT=0`.
- Playwright: the CLI underlying `npm run test:e2e` ran through Node `spawnSync` with `PYTHON=C:/dev/soma-i/.venv/Scripts` and `PLAYWRIGHT_CHANNEL=chrome` supplied only in the child environment. Output: `16 passed (2.8m)`, `PLAYWRIGHT_EXIT=0`, `PLAYWRIGHT_COMMAND_EXIT=0`. The config printed `sqlite:///C:/Users/micha/AppData/Local/Temp/somai-playwright-cqSffz/test.sqlite3`; teardown warned `Temporary Playwright database remains at C:\Users\micha\AppData\Local\Temp\somai-playwright-cqSffz`. Coverage includes `lesson cards hide minutes and retain the low data badge`, `onboard and complete a checkpoint in English and Swahili`, and all five `pathway-request-count.spec.js` cases.
- Port check: `netstat -ano -p tcp` showed an existing listener on 9323 outside the sandbox; it was left running. Required ports 8127/4177 were free before the CLI run. Only validation-owned startup processes were stopped.
- Validation limitation: an initial sandbox server attempt could not read the URL saved by a previous command because sandbox temp directories differed. The command lacked fail-fast handling and reached `runserver` without a validated explicit URL before being interrupted (exit 1, no server output). Repository-database access during that attempt is not verified; no repository database was inspected. The successful rerun used one fail-fast process outside the sandbox with the explicit OS-temp URL above.
- Not tested: dependency/browser installation, activation-policy changes, interactive README prompts, live feed ingestion, reminder execution, PostgreSQL, offline behavior beyond existing automated coverage, and real-learner product assumptions. Black and Ruff were not run; no screenshot claims are made.
- Documentation checks: `git diff --check` returned exit 0; Python byte checks confirmed UTF-8 and CRLF for both documents. `git status --short` showed exactly ` M README.md`, ` M docs/PLANS.md`, and the pre-existing `?? frontend/package-lock.json`. No commit, push, or merge was performed.

## README conflict reconciliation - 2026-10-12

- PR #9 conflicted after PR #8 advanced `main` to `bba3e9d`. `git log --oneline -4 origin/main` identified the merged README and product-brief changes. The resolution retains main's track positioning, persona, RSS/pathway/reminder evidence, demo script, owner workflow account, constraint table and detailed limits; it incorporates PR #9's setup safeguards, exact limits/AI-assistance paragraphs and fresh validation summary. `PRODUCT_BRIEF.md` is imported from main unchanged, not edited as part of this resolution.
- Documentation-only reconciliation: backend/frontend suites are **not tested again**; the results above remain the actual earlier outputs for unchanged application code. `git diff --name-only origin/main -- backend frontend` returned no paths. PowerShell parser and UTF-8/CRLF checks pass for the final documents; `git diff --check` returns exit 0. The existing untracked frontend lockfile is untouched. PR #9 remains unmerged.

## README submission plan completion - 2026-10-12

- Status: done. PR [#9](https://github.com/michael-mathenge/soma-i/pull/9) is merged into `main` at `a298e95`. Confirmed with `git fetch origin main`, `git log --oneline -3 origin/main` and `git rev-parse origin/main`. `git diff --exit-code origin/main HEAD -- README.md docs/PLANS.md` returned exit 0 before this completion entry, confirming the reviewed documents are on main. The earlier unmerged statements above describe their historical checkpoints.
- Completed: setup safeguards, server-window database reuse, frontend check instructions, Chrome/cleanup guidance, approved limits and Codex-assistance text, dated validation, conflict reconciliation, commit/push, PR description and extended merge description. Main's capstone narrative and product-brief change were preserved.
- Validation remains the actual 2026-10-12 results above: backend 117 passed (four warnings), guard 16 passed and one skipped, robustness 14 passed, lint/build exit 0 (106.2 KB), and Playwright 16 passed with exit 0 and the expected temporary-database warning. Post-merge application checks are **not tested**; no tests or database commands were run for this completion update.
- Remaining evidence gaps: required E6/E7 UI Network screenshots and external tracker update are still pending; Python 3.12 environment creation, interactive setup prompts, offline reload and live Gmail drafting remain **not tested**. Real-learner validation and production features remain outside the completed README submission scope. The interrupted sandbox-command limitation remains recorded above.
- Local completion update: only `docs/PLANS.md` edited; UTF-8/CRLF preserved and `git diff --check` returned exit 0. The pre-existing untracked frontend/package-lock.json remains untouched. This completion entry is uncommitted and has not been pushed.

## Honest AI-use disclosure - 2026-10-12

- The owner's supplied disclosure is preserved verbatim in `docs/AI-usage.md`, linked from README.md's Built with Codex section. The full disclosure was removed from README.md at the owner's request. It covers human decisions, Claude/Codex contributions, review and approval workflow, database-safety mistakes, recorded validation and remaining product assumptions. Supporting evidence remains in README.md's workflow account and the validation entries above.
- Documentation only: application checks are **not tested again**. `git diff --check` returned exit 0; UTF-8/CRLF byte checks passed for README.md, docs/PLANS.md and docs/AI-usage.md; a byte comparison confirmed the moved disclosure is unchanged. The previously approved local completion entry is preserved. No commit, push or database command was performed for this addition; the pre-existing untracked frontend/package-lock.json remains untouched.

## Later

- Production SMS provider delivery and durable user accounts.
- Broader curated feed and live opportunity aggregation.
- Cross-device synchronization and deployment hardening.

## Submission execution plan - 2026-10-12

1. Spec/demo reconciliation: documentation edited to reflect current pathways, paused hourly alert schedule, separate seeded-Amina rehearsal and optional tracker evidence. Diff check passes; runtime validation not tested again at this checkpoint.
2. Reflection and skill scan: owner confirmed idea origin and personal lesson; incorporated in docs/REFLECTION.md. Static scan complete in docs/SKILL_SCAN.md, with an unresolved skill command-format finding. Do not invoke that skill unattended as written.
3. Fresh OS-temp rehearsal: completed with explicit DATABASE_URL printed before management commands. Browser observation verified seeded Amina at 25% progress, SQL checkpoint submission, SQL unlocked, Data Visualisation next checkpoint, Low data cards, sample Junior Data Analyst opportunity and Kiswahili settings. Screens captured under ignored .local/submission; no repository database opened for this rehearsal.
4. Video: generated narration requested by owner; seven WAV scenes total 266.9 seconds. Local WebM assembly is in progress using captured UI states and synthetic narration; this is not a continuous screen recording. Loom is signed in, but Upload a video redirects to a paid upgrade; no purchase made. Owner explicitly requires confirmation before video upload or project submission.
5. Publication and submission: destination https://andela-lms.vercel.app/course/c/090e67fd-efc1-4dea-bef6-56067ae6c6bf/capstone/submit inspected while signed in. It requests video (MP4/MOV/WebM, maximum 500 MB; recommended about five minutes) and GitHub repository URL; no reflection field or deadline visible. Form warns submission locks the project. Do not upload video or submit until owner confirms the reviewed video. Preserve the existing frontend/package-lock.json.

## Submission rehearsal evidence - 2026-10-12

- Database: sqlite:///C:/Users/micha/AppData/Local/Temp/somai-rehearsal-e166d933-9aef-4a04-9790-0e4cd2021c36/demo.sqlite3. Fresh migrate/seed commands completed without errors. reminder_ops --json with an OS-temp JSONL log returned Amina's SQL-checkpoint alert, then alerts: [] on repeat; REMINDER_OPS_FIRST_EXIT=0 and REMINDER_OPS_SECOND_EXIT=0. send_reminders printed Amina's English console reminder and Sent 1 reminder(s), then Sent 0 reminder(s); SEND_FIRST_EXIT=0 and SEND_SECOND_EXIT=0. No Gmail draft or production SMS was created.
- Browser rehearsal: Open the demo learner showed Data Analyst progress 25%, completed Spreadsheets and next SQL checkpoint. Submitting the three answers and demo attestation navigated to /next and displayed You unlocked: SQL, Data Visualisation checkpoint, low-data reading cards and labelled sample opportunity. Settings switched to Kiswahili with translated navigation and weekly reminder checkbox. The database was reset with flush --noinput and seed_demo only after its exact path was verified under OS temp, to repeat the captured walkthrough.
- Full backend/frontend suites are not tested again during this preparation; earlier recorded results remain historical. Deadline remains unconfirmed.
