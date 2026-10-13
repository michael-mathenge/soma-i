# SOMA.i skill scan — 2026-10-12

## Scope

Static inspection of .agents/skills/soma-reminder-ops/SKILL.md, rules.json and the reminder command implementation. No Gmail action, schedule activation or application-database access was performed for this scan.

## Findings

- The skill separates alert reporting from delivery, requires verbatim alert/warning text, and permits at most one Gmail draft. It forbids sending and reading mail. Live Gmail remains not tested.
- reminder_ops refuses both repository database paths before reading reminders, invokes send_reminders in dry-run JSON mode and restricts its JSONL log to .local or OS temp. Its application-database behavior is a dry-run convention, not a SQLite read-only connection flag.
- rules.json enables weekly due reminders with 24-hour alert-repeat suppression. Weekly delivery eligibility and 24-hour alert suppression are separate rules.
- The command in SKILL.md is relative, uses backslashes and does not itself set or print DATABASE_URL. This fails the current contributor-guide requirement for absolute forward-slash commands in unattended skills. The skill must not be invoked unattended as written for the rehearsal. A repair is pending; run an explicitly configured OS-temp command directly if validating behavior.
- Overlapping runs can duplicate reports or drafts; the skill correctly asks for one instance at a time.
- Stored learner and feed text is explicitly treated as data. The skill forbids seed/ingestion operations and schedule changes within its own workflow.

## Validation status

Static scan complete. Direct, explicitly configured command execution was validated separately in the fresh OS-temp rehearsal: one alert, followed by no alerts on repeat, both exit 0. The skill itself was not invoked, no Gmail action was taken, and the command-format issue remains unresolved. Earlier test evidence is recorded in PLANS.md, including repository-path refusal, log-path restrictions, repeat suppression, corrupt-log tolerance and mocked draft-only behavior. Rehearsal outputs should be recorded separately after execution.
