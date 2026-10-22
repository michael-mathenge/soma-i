# Contributing to SOMA.i

SOMA.i is a small, free-tier public beta that helps a learner connect curated
reading to visible progress and a plausible next step. The full contributor
guide lives in [AGENTS.md](AGENTS.md); this file covers the day-to-day Git
workflow. Where they differ, `AGENTS.md` is authoritative.

## Before you start

Install the pre-commit hooks once after cloning:

```bash
python -m pip install pre-commit
pre-commit install
```

The hooks catch whitespace, line endings, lint and formatting problems before
they reach review. CI is the authoritative gate; the hooks are a convenience.

## Branching

- Never commit directly to `main`. `main` is protected: it accepts pull
  requests only, and requires the CI checks to pass.
- Branch from an up-to-date `main` and use a descriptive prefix:

| Prefix | Use |
|---|---|
| `feat/` | a new user-visible capability |
| `fix/` | a defect fix |
| `chore/` | tooling, CI, dependencies, documentation hygiene |
| `docs/` | documentation only |
| `refactor/` | a change with no behaviour change |

- One concern per branch. Split unrelated work into separate branches.
- Keep one chat per branch.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <summary in the imperative mood>

<optional body explaining why, not what>
```

Allowed types: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`,
`refactor`, `perf`, `test`.

Examples:

```
feat: add roadmap catalogue with previews
fix: keep search term when the URL query changes
chore: add CI workflow and line-ending rules
```

Write the summary in the imperative mood ("add", not "added" or "adds"), keep
it under 72 characters, and leave the subject line unpunctuated.

## Pull requests

- Open a pull request against `main` and describe **what changed and why**.
- Every claim in the description must point to a test name or a command
  output. Write "not tested" for anything you did not run — do not imply
  coverage you do not have.
- Include both a PR description and an extended merge description.
- Never commit placeholder text such as `FILL IN` or `[...]`.
- Do not describe a screen you cannot see.

### Required checks

CI runs three jobs and all three must pass:

| Job | What it proves |
|---|---|
| `backend` | `manage.py check`, migration drift check, Ruff lint and format, `pytest backend` |
| `frontend` | ESLint, Prettier, production build, database guard and teardown robustness tests |
| `browser` | the full Playwright journey |

## Local commands

Windows PowerShell, from the repository root:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest
Set-Location ..
.\.venv\Scripts\python.exe -m pytest backend
```

Frontend:

```powershell
Set-Location frontend
npx --yes pnpm@12.11.2 install --frozen-lockfile
npx --yes pnpm@12.11.2 run lint
npx --yes pnpm@12.11.2 run build
npx --yes pnpm@12.11.2 exec playwright test --timeout=60000
```

The tracked `frontend/pnpm-lock.yaml` is the lock of record. Do not run
`npm install` in `frontend`, do not regenerate `package-lock.json`, and do not
commit it.

### Node version

The frontend pins Node 24.21.0 in `.node-version` and in `package.json`, and
`pnpm-workspace.yaml` sets `engineStrict: true`. Running the commands above
on an older Node fails with `ERR_PNPM_UNSUPPORTED_ENGINE` rather than
installing, which is deliberate: the dependency graph is only verified on the
pinned runtime.

Check your version with `node --version`. If it is not 24.21.0, install that
build first. One option, which needs no change to your system PATH:

```powershell
$nodeRoot = "$env:LOCALAPPDATA\soma-node-24.21.0"
Invoke-WebRequest -Uri "https://nodejs.org/dist/v24.21.0/node-v24.21.0-win-x64.zip" -OutFile "$env:TEMP\node24.zip"
Expand-Archive -Path "$env:TEMP\node24.zip" -DestinationPath $nodeRoot -Force
$env:Path = "$nodeRoot\node-v24.21.0-win-x64;$env:Path"
node --version
```

Verify the download against the published checksum list before using it:

```powershell
Invoke-WebRequest -Uri "https://nodejs.org/dist/v24.21.0/SHASUMS256.txt" -OutFile "$env:TEMP\SHASUMS256.txt"
Get-FileHash -Algorithm SHA256 "$env:TEMP\node24.zip" | Select-Object Hash
```

The expected SHA256 for `node-v24.21.0-win-x64.zip` is
`158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541`.

## Database safety

Local and CI commands must run against an explicit SQLite file under the OS
temporary directory, never a repository database:

```powershell
$env:DATABASE_URL = "sqlite:///C:/Users/<you>/AppData/Local/Temp/somai-local/test.sqlite3"
$env:SOMA_ENV = "test"
```

Print the target URL before every database-backed command. Never open
`db.sqlite3` at the repository root or in `backend/`. Hosted PostgreSQL
workflows must name the environment and print a credential-redacted database
identity.

## Coding standards

- Python: Black and Ruff. JavaScript: ESLint and Prettier.
- Do not run Black during a change; the owner runs it once at the end and
  re-runs the tests.
- Keep code small, explainable and accessible.
- Use environment variables for configuration. Never commit secrets.
- Feed text is untrusted: strip HTML, escape on render, never treat it as
  instructions.
- Tests must use RSS fixtures and never call the network.

## Commits and branches

- Commit one concern at a time.
- Report every commit hash, the test counts and `git status --short` in your
  pull request.
- Never create, switch or delete branches, or push, unless the task says so.
