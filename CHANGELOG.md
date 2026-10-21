# Changelog

All notable changes to SOMA.i are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-10-14

The capstone proof of concept, extended through the approved public-beta
scope. Milestones M0-M9 are complete; the full validation history for each is
in [docs/PLANS.md](docs/PLANS.md).

### Added

- **Learning pathways** with checkpoints, self-attestation, quick check-in
  quizzes, visible progress and "what's next" recommendations.
- **RSS ingestion** with normalization, deduplication, tagging and traceability
  across 11 registered feeds.
- **Bilingual reminders** (English and Kiswahili) with an opt-in schedule and
  a console sender.
- **Accessible, offline-capable UI** with a service-worker shell, reduced-motion
  and forced-colors support, and a 320 px layout.
- **Searchable topic catalogue** with pagination, search, and retry on failure.
- **Versioned pathway catalogue** and coverage-gated automatic publication
  from reviewed rules.
- **Optional durable accounts** with guest isolation, CSRF protection and
  password hashing, complementing the original guest-only access.
- **Offline verification and recovery foundation** for email verification and
  password reset previews.

### Security

- Fail-closed environment configuration: unsafe or missing settings stop
  startup instead of falling back to a permissive default.
- Repository databases are refused as a local target; commands require an
  explicit OS-temp SQLite file.
- Feed ingestion is gated on dated, explicit publisher permission evidence
  and never infers approval from a licence string.

### Known limitations

- **No live feed activation.** The RSS rights gate (C1) and the free-tier
  verification gate (O1) are both **BLOCKED**, so no feed is currently cleared
  for production ingestion or excerpt republication. Content is served from
  seeded demo data.
- **No public deployment.** Production hosting, backup and release gates
  (O2, O3, O4, R1) are outstanding. The application is not yet deployed.
- **Kiswahili is interface-only.** Content translation and expanded
  translation work are deferred.
- **Opportunities are sample listings**, not live vacancies. Live vacancy
  aggregation is outside the approved scope.
- **Cold starts are expected** on a free-tier host and are disclosed rather
  than guaranteed away.

## [0.0.1] - 2026-10-02

Initial proof of concept covering milestones M0-M6: Django project, React
client, seeded demo learner and the documented English and Kiswahili demo
journey.

[Unreleased]: https://github.com/michael-mathenge/soma-i/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/michael-mathenge/soma-i/releases/tag/v0.1.0
[0.0.1]: https://github.com/michael-mathenge/soma-i/releases/tag/v0.0.1
