# Architecture

## Components

- `content`: vetted RSS sources, normalized items, skill taxonomy, and keyword tagging.
- `pathways`: ordered skills, checkpoint criteria, progression, and item recommendations.
- `learners`: anonymous session-linked learner profile and self-attested item/checkpoint progress.
- `opportunities`: clearly labelled sample Kenya opportunities and skill-overlap ranking.
- `engagement`: bilingual due-reminder selection, message templates, and sender interface.
- `frontend`: text-first React client, translations, and service worker cache for the app shell and recent reads.

## Data model and flow

RSS `Source` records are parsed into deduplicated `Item` records. Rule-based keyword tagging associates items with `Skill` records. Ordered `PathwaySkill` rows and one checkpoint per skill organize those skills toward a stated outcome. A session-linked `LearnerProfile` tracks item completion and checkpoint status. Gap recommendations rank items for remaining skills, preferring low-data content after skill match. Opted-in learners due for a reminder are selected from that progress state, logged, and passed to a console or sandbox sender. Completing a checkpoint returns its unlocked skill, next checkpoint, recommended items, and skill-overlap-ranked opportunities.

`Pathway` stores title, description, target outcome, and locale. `PathwaySkill` stores order and skill; `Checkpoint` stores title, criteria, unlock text, and quiz configuration. `Opportunity` carries type, provider, URL, location, deadline, skills, and sample-source note. `ReminderLog` records the short message, destination when provided, and send time.

## Interfaces

The API is under `/api/`; `/api/health/` is public. Onboarding creates the profile and binds its ID to a Django session cookie. Subsequent profile, pathway, checkpoint, item, and settings actions resolve through that session. The frontend dev server proxies `/api/` to Django. The native service worker caches the app shell and the last successful pathway/items GET responses for offline viewing; progress mutations require connectivity.
