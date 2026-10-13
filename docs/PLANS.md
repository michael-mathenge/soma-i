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

## Later

- Production SMS provider delivery and durable user accounts.
- Broader curated feed and live opportunity aggregation.
- Cross-device synchronization and deployment hardening.

## Approved public-beta execution - 2026-10-13

Baseline: main at 391881e. The owner approved the evidence-based plan and execution. Scope is English-first, optional accounts plus guests, a small free-hosted beta, and automatically published content-backed pathways without a three-pathway ceiling. Translation expansion is deferred. The existing domain is michaelmathenge.dev; provider eligibility, source rights and live content remain unverified.

| Order | Gate | Branch | Risk | Task | Status |
|---|---|---|---|---|---|
| 0 | G0 | docs/working-rules | high | Governance scope and database exceptions | merged PR #11; verified 2026-10-13 |
| 1 | O1 | codex/free-tier-verification | high | Verify free-service terms, quotas and cost controls | research complete; release gate BLOCKED; see FREE_TIER_VERIFICATION.md |
| 2 | C1 | codex/rss-rights-verification | high | Verify candidate feeds and permitted reuse | desk review recorded; release gate BLOCKED; see SOURCES.md |
| 3 | C2 | codex/content-provenance | medium | Expose permitted provenance metadata | pending |
| 4 | C3 | codex/feed-fetch-hardening | high | Harden fetch destination and ingestion failures | pending |
| 5 | C4 | codex/pathway-catalogue | high | Versioned database-backed catalogue | pending |
| 6 | C5 | codex/pathway-discovery | high | Coverage-gated automatic pathway publication | pending |
| 7 | U1 | codex/ui-foundations | medium | Tokens, native controls and motion rules | pending |
| 8 | U2 | codex/ui-catalogue | medium | Searchable paginated topic catalogue | pending |
| 9 | U3 | codex/ui-learning-journey | medium | Mobile learning journeys | pending |
| 10 | P1 | codex/runtime-upgrade | high | Supported pinned dependency versions | pending |
| 11 | P2 | codex/production-settings | high | Fail-closed secure configuration | pending |
| 12 | P3 | codex/account-ownership | high | Guest and durable account isolation | pending |
| 13 | P4 | codex/account-recovery | high | Verified free email verification/recovery | pending |
| 14 | P5 | codex/request-limits | high | Shared rate limits | pending |
| 15 | P6 | codex/private-offline-cache | high | Public-only offline metadata | pending |
| 16 | P7 | codex/postgres-migration | high | Disposable migration parity checks | pending |
| 17 | Q1 | codex/quality-gates | medium | Automated and manual release gates | pending |
| 18 | O2 | codex/free-host-deployment | high | Same-origin durable staging | pending |
| 19 | O3 | codex/hosted-ingestion | high | Six-hour desktop-independent schedule | pending |
| 20 | O4 | codex/backups-retention | high | Encrypted backup/restore and cleanup | pending |
| 21 | R1 | codex/beta-release | medium | Owner-approved public beta | pending |

### Governance validation

- git branch --show-current and git log --oneline -3 confirmed main at 391881e before work. git merge-base --is-ancestor docs/working-rules main returned exit 0. The existing governance branch was advanced with git merge --ff-only main, preserving commits; it then reported docs/working-rules at 391881e. The pre-existing untracked frontend/package-lock.json was left untouched.
- This task edits only AGENTS.md, PRODUCT_BRIEF.md, CAPSTONE_SPEC.md, docs/DECISIONS.md and this log. It changes documentation authority, not application behavior. Production accounts, source/provider verification, deployment and every runtime gate are not tested and not implemented by this task. No database commands, installs, Black or application tests run for the governance change.
- Python static document checks returned GOVERNANCE_CONSISTENCY_CHECK=PASS and UTF-8/CRLF/conflict-marker checks passed for all five documents. git diff --check returned DIFF_CHECK_EXIT=0. Application tests: not tested (documentation-only task). All original documents grew; no file was replaced with a shorter document.

- Governance branch synchronization: git fetch origin main reported a298e95. git merge --no-commit --no-ff origin/main merged its newer README/product-brief/validation history without conflicts. Those upstream changes are preserved, not additional application edits. git diff origin/main -- backend frontend returned no tracked application changes; the pre-existing untracked lockfile remains separate.

## O1 free-tier verification - 2026-10-13

- Starting checks confirmed docs/working-rules at 3beee75de1019c0499b8ffda93044a54de148633. GitHub REST PR #11 returned merged=true, closed, merge commit 6c70bf494dd1b7cee4f989f315bd99d267690c7b; git fetch origin main advanced origin/main to that commit and git merge-base --is-ancestor returned exit 0. Created codex/free-tier-verification from origin/main; local main remains 391881e8818eff2cb99255d14b8d2de82054cf6b.
- Read AGENTS.md, PRODUCT_BRIEF.md, CAPSTONE_SPEC.md, docs/DECISIONS.md and this plan. Only docs/FREE_TIER_VERIFICATION.md and this file change; prior history is retained apart from updating current G0/O1 table status.
- [O1 evidence and verdict](FREE_TIER_VERIFICATION.md): dated official-source research complete; infrastructure/release gate BLOCKED. R2 has subscription/overage billing without a verified hard zero-charge cutoff. Render production guidance needs resolution; GitHub schedules cannot guarantee six-hour execution. Neon current 1 GB pricing supersedes older 0.5 GB guidance. Brevo transactional approval/domain authentication, all account cost controls, privacy/retention and operational backup/recovery gates remain open.
- No service accounts, agreements, payment methods, provisioning, DNS changes, email sends, database access or deployments. Application tests: **not tested** (documentation-only); provider operations/account eligibility: **not tested**. No Black, build or application suites run.
- Documentation validation: strict UTF-8 decoding, CRLF-only line endings and conflict-marker checks returned UTF8_CRLF_MARKERS=PASS for both files. O1_CONSISTENCY_HISTORY_MAIN_LOCKFILE=PASS checked provider/gate/date/evidence markers, preserved origin/main planning prefix except the two status cells, unchanged local main and unchanged SHA256 A453D1D238289C19F6AE1F573F4D253EE084252DD63ACF6FCF190D0967A57F95 for the pre-existing lockfile. git diff --check exited 0. GitHub REST repository metadata returned REPOSITORY_VISIBILITY=public; no account billing settings were inspected.

## C1 RSS rights verification - 2026-10-13

- User confirmed PR #12 merged and authorized proceeding here; that continuation overrides one-chat-per-branch for this task. Starting git branch --show-current and git log --oneline -3 matched codex/free-tier-verification at 9a67a9b97223f458e95438dceaa689857081ac48.
- GitHub REST PR #12 returned closed, merged=true, merged_at=2026-10-13T19:58:38Z and merge_commit_sha=651ed833a7c916c510ea303998b0135e0503e14a. git fetch origin main advanced origin/main to that commit; git merge-base --is-ancestor returned exit 0. Created codex/rss-rights-verification from merged origin/main without modifying local main (391881e8818eff2cb99255d14b8d2de82054cf6b).
- Read repository governance/brief/spec/decisions, source history and feed registry. Only docs/SOURCES.md and this plan change. Preserve all historical source rows; a current notice and dated appendix distinguish them from production approval.
- [C1 evidence](SOURCES.md#c1-rss-rights-verification---2026-10-13): all 11 configured feeds inventoried, four publisher/platform groups reviewed, zero feeds cleared for production ingestion/excerpt reuse. freeCodeCamp automated-access terms, Real Python personal-use limits, DEV public-display/copying restrictions and inaccessible current CSS-Tricks policy/access leave C1 BLOCKED. RSS availability, a software licence, attribution and the 300-character cap are not permission evidence. Sample freeCodeCamp/Real Python English reading was observed through the research tool; whole-feed/current parse counts and independent-publisher curriculum coverage remain unverified.
- Research-tool feed opens returned cache misses, unsupported XML, inaccessible results or 403; these are recorded as tool limitations, not a fresh successful HTTP/entry-count sweep. No publisher contact, paid licence, signup, scraping, database access, ingestion command, dependency install, runtime/configuration edit or deployment occurred. Application tests: **not tested** (documentation-only); provider/feed ingestion operations: **not tested**. Existing rights handling was inspected read-only for C2/C3 handoff; no runtime guard is claimed implemented. O1 remains BLOCKED independently.
- Documentation checks returned UTF8_CRLF_MARKERS=PASS for both files and C1_CONSISTENCY_HISTORY_SCOPE=PASS; exact registry key/URL coverage was FEED_KEYS_URLS=11/11 and APPROVED_FEEDS=0. Checks preserved the original source text apart from the inserted current-status notice and the full origin/main planning prefix apart from the C1 status cell. git diff --check exited 0; git diff origin/main -- backend frontend returned no tracked application changes. Local main and lockfile SHA256 A453D1D238289C19F6AE1F573F4D253EE084252DD63ACF6FCF190D0967A57F95 remain unchanged.
