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

## Tailwind CSS v4 for the design system - 2026-10-21

- The owner chose Tailwind CSS v4 for the interface revamp. The contributor guide previously recorded "no heavy UI libraries" and "native HTML/CSS". That rule is narrowed rather than removed: Tailwind is a build-time stylesheet compiler with no runtime component library, no animation library and no client-side JavaScript, so the bundle cost is compiled away and the dependency count stays at one build tool.
- The design tokens move into a Tailwind theme block, so the custom properties and the utility classes share one source of truth. The token values are unchanged, which keeps the recorded contrast, focus, reduced-motion and forced-colours behaviour.
- Tailwind only emits a theme variable when a utility class references it, and the authored stylesheet reads several variables by name. The spacing scale is therefore declared explicitly in the theme. Without this the build silently drops the variables and the layout loses its spacing.
- The system fonts, the reduced-motion rules, the forced-colours overrides and the minimum target size stay as they are. Those are accessibility guarantees, not styling preferences.
