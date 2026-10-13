# Decision log

- Use anonymous Django sessions for a low-friction demo because the requested pages do not include sign-in or password recovery.
- Use SQLite by default and `DATABASE_URL` for a straightforward later PostgreSQL switch.
- Use RSS fixtures and patched parser results in automated tests; live feed requests are a documented manual acceptance check.
- Match by simple case-insensitive keyword overlap and retain source/date traceability instead of using paid AI or hidden ranking.
- Prefer skill score first, then low-data items; this keeps relevance primary while surfacing bandwidth-friendly options.
- Weekly reminders are the default. Console output is the working sender; Africa's Talking remains a credential-driven sandbox stub.
- Opportunity records are labelled sample examples and are not represented as currently open vacancies.
- Cache static shell plus recent GET payloads with a native service worker; keep completion writes online to avoid sync conflicts.

## Public-beta decisions approved 2026-10-13

- Preserve the capstone decisions above as history. Optional durable email/password accounts now complement guest sessions; the brief explicitly authorizes identity fields. Same-origin Django session authentication, CSRF protection and owner-resolved progress avoid browser-stored bearer tokens.
- Replace the three-pathway ceiling with a versioned published catalogue. Deterministic RSS topic discovery may publish automatically only after verified source rights and the brief's coverage/curriculum thresholds pass; unsupported topic/prerequisite mappings stay unpublished. No paid AI inference or invented job qualification is authorized.
- Release content is English first; broader Kiswahili translation is deferred. Retain and clearly identify the existing interface-only support.
- Preserve low-data-first behavior and honest labels. A content flag is not measured destination-page bandwidth. UI uses native HTML/CSS, system fonts and reduced-motion-aware transitions; no heavy component/animation framework.
- Split public catalogue metadata caching from private learner progress before accounts are introduced. Authenticated dashboard/profile payloads must never be service-worker cached.
- PostgreSQL is the production target; SQLite stays local/test only. The contributor guide narrowly allows reviewed hosted jobs and disposable PostgreSQL tests while forbidding repository database access and production seeding.
- Proposed same-origin Render web hosting, Neon PostgreSQL, GitHub Actions scheduling, Brevo mail and Cloudflare R2 encrypted backup storage all remain to verify. Existing michaelmathenge.dev is owner-reported; DNS, TLS, sender verification, quotas and effective no-charge controls are unverified. Stop at failed eligibility/cost/privacy gates instead of selecting a paid substitute.
- The target is a small public beta that tolerates disclosed cold starts/sleep; it is not an uptime-guaranteed production service. Public publication still requires satisfied gates and explicit approval. No production SMS, live vacancies, paid APIs or new demographic data.
