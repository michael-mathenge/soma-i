# SOMA.i — learning that leads somewhere

SOMA.i connects curated RSS learning content to goal-based pathways, checkpoints, reminders and sample opportunities. It is a proof of concept for the Andela x OpenAI x MIVA Codex Accelerator theme, “Learning That Stays With You,” positioned as **Primary Track 3: Guidance, Pathways and Opportunity**. RSS discovery supports Track 1; checkpoints and reminders support Track 2. Programme context and track positioning are the owner’s description.

## Who it helps

Meet Amina Demo. We assume she is 23, lives in Nakuru, works part-time in retail, uses an entry-level Android phone on prepaid data, prefers English with a Kiswahili option, and wants a junior data role. These are a demo persona’s assumptions, not research findings or measured impact. See [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md).

The intended journey connects a short reading task to a checkpoint, an unlocked skill and a possible next step. The seeded Amina journey is covered by `test_onboard_complete_checkpoint_and_get_whats_next` in [the learner API tests](backend/learners/tests/test_api.py).

## Quick start

Use Windows PowerShell, Python 3.12 and Node 20 or newer. The contributor guide specifies these versions; [the validation log](docs/PLANS.md) also records checks with Python 3.13.7.

Configuration names are `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` and `SOMA_SENDER`. Optional sandbox configuration uses `AFRICASTALKING_USERNAME` and `AFRICASTALKING_API_KEY`; delivery is stubbed. See [.env.example](.env.example), [settings](backend/soma/settings.py) and [senders](backend/engagement/senders.py). No provider credentials are needed for the console demo.

The commands below create a temporary SQLite database and explicitly override the repository database defaults. Never use either repository `db.sqlite3` for these commands. Commands were inspected during this documentation plan, **not tested**.

**PowerShell — clone and prepare the environment**

```powershell
git clone https://github.com/michael-mathenge/soma-i.git
Set-Location soma-i
py -3.12 -m venv .venv
& ./.venv/Scripts/Activate.ps1
python -c "import sys; assert sys.prefix != sys.base_prefix, 'Project virtual environment is not active'; print(sys.executable)"
node --version
python -m pip install -r requirements.txt
```

**PowerShell — initialize and start the backend, from the repository root**

```powershell
$somaDemoDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('soma-i-demo-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $somaDemoDirectory -ErrorAction Stop | Out-Null
$somaDemoDatabase = Join-Path $somaDemoDirectory 'demo.sqlite3'
$env:DATABASE_URL = 'sqlite:///' + $somaDemoDatabase.Replace('\', '/')
$env:SOMA_SENDER = 'console'
Write-Output $env:DATABASE_URL
& ./.venv/Scripts/python.exe backend/manage.py migrate
Write-Output $env:DATABASE_URL
& ./.venv/Scripts/python.exe backend/manage.py seed_demo
Write-Output $env:DATABASE_URL
& ./.venv/Scripts/python.exe backend/manage.py runserver
```

Keep that backend window open. Start the frontend in a second PowerShell window opened at the repository root.

**PowerShell — frontend**

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the URL printed by Vite. The demo-entry labels are defined in the [English](frontend/src/i18n/en.json) and [Kiswahili](frontend/src/i18n/sw.json) translations.

If script policy blocks virtual-environment activation or npm, run the following in that window, then retry.

**PowerShell — session-only script-policy troubleshooting**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

The test server ignores an inherited `PYTHON` value unless it names an existing file; see [Python resolution](backend/python-resolution.mjs), fixed in commit `e2f0296`.

**PowerShell — checks from the repository root**

```powershell
$somaCheckDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('soma-i-check-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $somaCheckDirectory -ErrorAction Stop | Out-Null
$somaCheckDatabase = Join-Path $somaCheckDirectory 'test.sqlite3'
$env:DATABASE_URL = 'sqlite:///' + $somaCheckDatabase.Replace('\', '/')
Write-Output $env:DATABASE_URL
& ./.venv/Scripts/python.exe -m pytest backend
Set-Location frontend
npm run build
npm run test:e2e:guard
npx playwright install chromium
Write-Output $env:DATABASE_URL
npm run test:e2e
```

Playwright creates its own temporary database through [its configuration](frontend/playwright.config.js). Ports 8127 and 4177 must be free; the current configuration does not reuse existing servers.

[docs/PLANS.md](docs/PLANS.md) records 117 backend tests passing, 16 database-guard tests passing with one symlink-permission skip, a 106.2 KB gzipped build against a 200 KB budget, and clean Black/Ruff checks. It records 16 Playwright tests passing with a teardown failure. Commit `e2f0296` fixes cleanup handling; the later exit-0 result was **not verified** for this README. These checks were **not tested** during documentation planning.

## How it works

### RSS and skills

[The registry](backend/content/feeds.json) contains 11 feeds. Configuration-driven rules match content to pathways and skills, then rank beginner suitability. [The ingestion tests](backend/content/tests/test_ingestion.py) cover malformed feeds, missing dates, deduplication, HTML stripping, unsafe links, timeouts and ETag/Last-Modified handling. [SOURCES.md](docs/SOURCES.md) records source checks and attribution; those are historical checks, not guarantees of current availability.

The [canonical pathways](backend/pathways/constants.py) are:

| Pathway | Skills |
|---|---|
| Data Analyst | Spreadsheets, SQL, Data Visualisation, Statistics |
| Frontend Developer | HTML, CSS, JavaScript, Accessibility, Git |
| Backend/Python Developer | Python, Git, API Development, Testing |

Git uses one shared skill record. Learners can skip, restart or switch pathways; see `test_skip_restart_switch_and_delete_are_available`.

`seed_demo` uses committed fixtures and hand-written items without fetching live feeds. Hand-written Data Analyst items carry “(demo)” and the source “SOMA.i sample content”; developer fixture items carry “(sample content).” See `test_seed_demo_handwritten_samples_share_one_source_and_distinct_links` and `test_seed_demo_fixture_picks_are_offline_low_data_and_labeled`. Opening external lessons still requires connectivity.

### Reminders, skill and schedule

`send_reminders` uses the console sender for this demo; real SMS delivery is not implemented. The dry-run option previews due reminders without sending or creating reminder records. See [the command](backend/engagement/management/commands/send_reminders.py) and `test_send_reminders_dry_run_sends_and_logs_nothing`.

The reusable [SOMA.i Reminder Ops skill](.agents/skills/soma-reminder-ops/SKILL.md) calls `reminder_ops`: a database-read workflow with 24-hour repeat suppression and a JSONL log restricted to `.local/` or the OS temporary directory. It refuses both repository database paths. See `test_reminder_ops_refuses_repository_database_paths`, `test_reminder_ops_suppresses_repeats_until_cooldown_expires` and `test_reminder_ops_rejects_log_path_outside_local_or_temp`.

The skill permits at most one Gmail digest draft and forbids sending messages or reading mail. The helper has mocked coverage in `test_gmail_draft_helper_only_creates_a_draft`; the live Gmail step is **not tested**.

[The scheduled-task record](docs/SCHEDULED_TASK.md) documents two failed scheduled attempts, followed by a successful run after working-directory and log-permission fixes. The hourly schedule was then paused. It requires the machine and Codex app to stay open; its database copy can become stale.

## Demo script

This is a suggested demo sequence derived from the seed, API and browser tests; no app screen was inspected during this documentation plan.

1. Open the seeded Amina Demo learner in English and use the Data Analyst pathway.
2. Follow a recommended lesson, return and submit the three-question checkpoint.
3. Inspect the returned unlocked skill, next checkpoint, reading recommendations and labelled sample opportunities.
4. Switch to Kiswahili to demonstrate the available interface translation, then inspect reminder preferences.
5. Explain the reusable reminder skill and the documented successful scheduled run; the schedule is paused and Gmail was not exercised.

The checkpoint journey has test coverage in `test_onboard_complete_checkpoint_and_get_whats_next` and the Playwright test “onboard and complete a checkpoint in English and Swahili.” Amina is seeded part-way through Data Analyst with English weekly reminders enabled; see `test_seed_demo_is_repeatable_and_opts_amina_into_english_weekly_reminders`.

Offline reload is **not tested** and is not part of this demo promise. [PLANS.md](docs/PLANS.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [DECISIONS.md](docs/DECISIONS.md) and [SOURCES.md](docs/SOURCES.md) provide supporting project records.

## Built with Codex

The following workflow account is mine as the project owner; repository commits verify the artifacts, not which assistant authored each line.

I chose the idea, Amina’s assumed learner profile, Primary Track 3, the three pathways and the boundaries: no real SMS, accounts, live opportunity aggregation or deployment. I decided which review findings to fix, accept or defer.

I used Plan mode first, four-part prompts, one task per chat and read-only reviews of named commit ranges. Planning, prompts and review notes were drafted with Claude; implementation code was written with Codex. [AGENTS.md](AGENTS.md) records working rules developed from mistakes.

Confirmed artifacts include the Django/DRF backend, React/Vite frontend, migrations and tests (`5d8e4e6`); RSS ingestion (`cadb257`); the reminder command and skill (`a2e289b`, `1b6afde`); repository-database protection (`ade65fe`); and scheduled-task documentation (`0d3d56e`).

One review found that a corrupt reminder log line could block later runs. Commit `647e611` tolerates malformed lines and reports warnings; `test_reminder_ops_skips_corrupt_middle_log_line_and_warns` covers that case.

One incident shaped the safeguards: a Codex probe fell back through `.env` to the repository-root database and changed demo data. This is my account of the incident. The resulting contributor rules require explicit temporary databases; the e2e guard protects both repository paths, and reminder previews use dry run. Dry run is not a SQLite read-only connection flag.

[PLANS.md](docs/PLANS.md) records validation results and remaining evidence gaps.

## Track and operating-constraint mapping

| Track or constraint | What the repository demonstrates | Remaining limit |
|---|---|---|
| Primary Track 3 | Ordered skills, checkpoints and next-step sample opportunities; learner API tests | Real opportunity aggregation: **not done** |
| Track 1 | Registered RSS sources, matching and ingestion tests | Source quality is curated, not independently certified |
| Track 2 | Checkpoints and bilingual console reminders; engagement tests | Real SMS: **not done** |
| Credibility | Attribution, original links, date provenance and stale-source handling; ingestion tests and SOURCES.md | External content is not independently fact-checked |
| Low bandwidth | Text-based lesson cards, pathway payload under 1,500 bytes in `test_pathways_list_omits_seeded_picks_and_stays_under_1500_bytes`, recorded build below 200 KB | “Low data” is a fixed flag, not measured usage; offline journey **not tested** |
| Accessibility and inclusion | Native controls, labels and navigation landmarks in App.jsx; skip/restart/switch API coverage | Full keyboard, contrast, screen-reader and plain-language audit: **not done** |
| Personalisation without exclusion | Pathway/skill recommendations and supported skip, restart and switch actions | Learning outcomes and recommendation quality have not been validated with learners |
| Privacy and security | Optional phone, deletion endpoint, feed-text stripping and link validation | Durable accounts and production access control: **not done** |
| Multilingual | English/Kiswahili interface and reminder strings; bilingual test definitions | Pathway-specific translation is limited to Data Analyst; native-speaker review **not done** |
| Local relevance | Kenya-labelled sample opportunities and the assumed Nakuru learner | Locally African RSS sources and verified local vacancies: **not done** |

## Known limits

- Amina and the retention problem are assumptions. Learner research and measured impact are **not done**; [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) makes no statistical claim.
- Recommendations remain thin for API Development and Testing. `test_seed_demo_fixture_picks_are_offline_low_data_and_labeled` accepts a minimum of one fixture pick for those skills, versus two for the others.
- Lesson cards hide reading minutes. “Low data” is a fixed content flag, not a bandwidth measurement; see the card-metadata test and ingestion code.
- English/Kiswahili interface support does not translate external lessons or all pathway-specific terminology. The app’s “ · hatua” checkpoint gloss needs native-speaker review; see `App.jsx`.
- Opportunity percentages compare one supplied unlocked skill with the listing’s skills. A “100% match” is not a hiring probability or a measure of overall job readiness; see [matching.py](backend/opportunities/matching.py).
- Service-worker caching exists, but offline reload is **not tested**. No offline progress-submission queue is implemented in [sw.js](frontend/public/sw.js).
- The scheduled task is documented as paused. Copies can become stale, overlapping runs can duplicate alerts or drafts, and live Gmail drafting is **not tested**.
- Real SMS, accounts, live opportunity aggregation and deployment are outside this capstone. Production privacy/security hardening is **not done**.
- The current PostgreSQL path and fresh execution of the README commands are **not tested**.

Licensed under the MIT License; see [LICENSE](LICENSE).
