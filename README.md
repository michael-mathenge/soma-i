# SOMA.i — learning that leads somewhere

SOMA.i is an invention-sprint proof of concept that connects credible learning content to practical skills, checkpoints, and next-step opportunities. Its primary track is **Guidance, Pathways & Opportunity**; it also demonstrates **Access & Discovery** through curated RSS and **Engagement** through checkpoints and reminders.

## Clone (PowerShell)

```powershell
git clone https://github.com/michael-mathenge/soma-i.git
```

Open PowerShell in the cloned repository directory and continue with setup below.

## How the operating constraints are addressed

- **Credibility:** vetted RSS sources, visible publisher links, and source/date traceability; see `docs/SOURCES.md`.
- **Low bandwidth:** text-first screens, low-data badges and ranking, small assets, and offline read caching.
- **Accessibility:** semantic controls, labels, keyboard navigation, contrast, and plain language.
- **Personalisation without exclusion:** pathway skill matching guides recommendations, while skip, restart, and switch remain available.
- **Privacy:** minimal learner fields, optional phone, and delete-my-data endpoint.
- **Multilingual:** English and Kiswahili UI and reminder templates.
- **Local relevance:** Kenya-oriented pathways and clearly labelled sample local opportunities.

## Setup (PowerShell)

Install Python 3.12 and Node 20 or newer. Check the installed versions, then run setup from the repository root:

Create an isolated SQLite database under the OS temporary directory. Stop if temporary-directory creation fails; do not use a repository database. Keep this setup window open so the backend window can reuse the printed database URL. Development settings come from `.env`; the explicit `DATABASE_URL` below overrides its database setting. Copy `.env.example` only when `.env` does not already exist.

```powershell
$ErrorActionPreference = 'Stop'
python --version
node --version
py -3.12 -m venv .venv
./.venv/Scripts/Activate.ps1
python -c "import sys; assert sys.prefix != sys.base_prefix, 'Project virtual environment is not active'; print(sys.executable)"
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$setupDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("somai-setup-" + [guid]::NewGuid())
try { New-Item -ItemType Directory -Path $setupDirectory -ErrorAction Stop | Out-Null } catch { throw "Temporary database directory could not be created; stop setup." }
$env:DATABASE_URL = "sqlite:///" + (Join-Path $setupDirectory "demo.sqlite3").Replace('\', '/')
Write-Output $env:DATABASE_URL
python backend/manage.py migrate
if ($LASTEXITCODE -ne 0) { throw "Migrations failed; stop setup." }
Write-Output $env:DATABASE_URL
python backend/manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed; stop setup." }
```

If PowerShell blocks activation, run this in the same window, then retry activation and the virtual-environment check:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

In a frontend PowerShell window, select the cloned repository root when prompted, then start Vite. This window does not run database commands and needs no database configuration.

```powershell
$ErrorActionPreference = 'Stop'
$repositoryRoot = Read-Host "Enter the full path to the cloned soma-i repository"
Set-Location -LiteralPath $repositoryRoot -ErrorAction Stop
Set-Location frontend
npm install
npm run dev
```

In a backend PowerShell window, select the same repository root and paste the exact `DATABASE_URL` printed by setup when prompted. Verify that its temporary database exists before starting Django.

```powershell
$ErrorActionPreference = 'Stop'
$repositoryRoot = Read-Host "Enter the full path to the cloned soma-i repository"
Set-Location -LiteralPath $repositoryRoot -ErrorAction Stop
$env:DATABASE_URL = Read-Host "Paste the DATABASE_URL printed by setup"
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $env:DATABASE_URL.StartsWith('sqlite:///')) { throw "Use the setup SQLite URL." }
$databasePath = [System.IO.Path]::GetFullPath($env:DATABASE_URL.Substring(10))
if (-not $databasePath.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $databasePath -PathType Leaf)) { throw "Use the existing setup database under the OS temporary directory." }
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py runserver
```

Open the Vite URL printed by the frontend command and select **Open the demo learner**
(in Kiswahili: **Fungua mwanafunzi wa majaribio**).

For backend checks, use the setup PowerShell window at the repository root with its temporary `DATABASE_URL` still set:

```powershell
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe -m pytest backend
```

For frontend checks, use the frontend window in `frontend`. Playwright creates its own isolated OS-temp SQLite database and prints its URL. Free ports 8127 and 4177 before running it: inspect any listeners, then stop the owning servers in their original windows. Do not stop an unfamiliar process. Server reuse is disabled in the config, so `PW_REUSE_SERVER` has no effect.

```powershell
npm run test:e2e:guard
npm run test:e2e:robustness
npm run lint
npm run build
netstat -ano -p tcp | Select-String ':8127 |:4177 '
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:e2e
```

`PLAYWRIGHT_CHANNEL=chrome` uses installed Google Chrome. To use Playwright's Chromium instead, remove the channel variable and install that browser if it is missing:

```powershell
Remove-Item Env:PLAYWRIGHT_CHANNEL -ErrorAction SilentlyContinue
npx playwright install chromium
npm run test:e2e
```

On Windows, a locked temporary database can produce a cleanup warning after teardown retries; an otherwise successful run still exits successfully.

To ingest live feeds or preview due reminders, use the setup window at the repository root with its temporary database URL:

```powershell
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py ingest_feeds
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py send_reminders
```

Tests use local XML fixtures and do not require network access. Set `DATABASE_URL` to a PostgreSQL URL and configure the matching driver for a later database switch.

## Demo script

1. Open SOMA.i, select English or Kiswahili, and choose a pathway.
2. Open the Data Analyst pathway, inspect remaining skills, and open a recommended lesson.
3. Mark a lesson done, complete the three-question checkpoint, and inspect the unlocked skill, next checkpoint, and Kenya sample opportunities.
4. Switch the language in Settings, confirm the same flow copy is localized, and opt into weekly reminders if desired.
5. Reload with the network disabled to show cached app shell and last-viewed pathway/items; progress submissions need connectivity.

The demo learner is `Amina Demo`, mid-way through Data Analyst, with seeded content and sample opportunities. `docs/PLANS.md` tracks milestone status and validation; `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/SOURCES.md` record design details.

## Known limits

SOMA.i is a local proof of concept using anonymous sessions rather than
durable user accounts. Opportunities are labelled sample examples, not
live vacancies. Reminder delivery uses console output; production SMS
delivery, deployment, and live opportunity aggregation are outside scope.

Offline support covers the cached app shell and previously viewed reading
data. Progress submissions require connectivity. The demo persona and
product assumptions still need validation with real learners.

On Windows, Playwright may leave its isolated temporary database behind
when the file remains locked. Teardown retries briefly, then warns without
failing an otherwise successful run.

## Built with Codex

Codex assisted with planning, implementation, tests, documentation, and
debugging, including Windows Playwright cleanup and Python resolution.
This repository contains AI-assisted code. Changes were developed through
scoped requests and checked using backend tests, node:test suites, lint,
production builds, and Playwright runs. Test results demonstrate the
checked scenarios; they do not establish production readiness or validate
the product assumptions with real learners.

Licensed under the MIT License; see [LICENSE](LICENSE).
