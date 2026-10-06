# SOMA.i milestones

Update each status and validation result as work progresses. All work is on a milestone feature branch; do not commit directly to `main`.

| Milestone | Status | Validation |
|---|---|---|
| M0 Bootstrap and project guide | done | Fresh `.env` setup, migrations, `seed_demo`, and `manage.py check` pass; `/api/health/` returns `{"status":"ok"}`. |
| M1 Content, RSS ingestion, and sources | done | Fixture ingestion/dedupe/tag/traceability tests pass; live run parsed 50 MIT News, 10 freeCodeCamp, and 71 MDN entries. |
| M2 Pathways, learner progress, and checkpoints | done | Progress and low-data recommendation tests pass; API covers completion, skip, restart, switch, and quiz storage. |
| M3 Opportunities and next steps | done | Skill-overlap and What's Next payload tests pass; demo seeds 10 labelled Kenya examples. |
| M4 Bilingual reminders | done | Tests cover opt-in/due selection, English and Swahili copy, and <=160 characters. |
| M5 Frontend, i18n, accessibility, and offline shell | done | ESLint passes; `npm run build` reports 106.0 KB gzipped JS+CSS (<200 KB); Playwright journey passes in English and Swahili. |
| M6 Demo, documentation, and acceptance | done | Fresh SQLite setup and demo seed pass; `pytest` (8 passed), Ruff, Black, ESLint, production build, and bilingual Playwright smoke pass. Live feed ingestion parsed 50 MIT News, 10 freeCodeCamp, and 71 MDN entries on 2026-10-02. |

## Later

- Production SMS provider delivery and durable user accounts.
- Broader curated feed and live opportunity aggregation.
- Cross-device synchronization and deployment hardening.
