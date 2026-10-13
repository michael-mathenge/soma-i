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

## Approved public-beta execution - 2026-10-13

Baseline: main at 391881e. The owner approved the evidence-based plan and execution. Scope is English-first, optional accounts plus guests, a small free-hosted beta, and automatically published content-backed pathways without a three-pathway ceiling. Translation expansion is deferred. The existing domain is michaelmathenge.dev; provider eligibility, source rights and live content remain unverified.

| Order | Gate | Branch | Risk | Task | Status |
|---|---|---|---|---|---|
| 0 | G0 | docs/working-rules | high | Governance scope and database exceptions | documented; PR pending |
| 1 | O1 | codex/free-tier-verification | high | Verify free-service terms, quotas and cost controls | pending |
| 2 | C1 | codex/rss-rights-verification | high | Verify candidate feeds and permitted reuse | pending |
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
