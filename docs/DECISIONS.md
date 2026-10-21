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

## Metadata-only content model - 2026-10-21

- Content is published to learners as title, publisher, publication date and a link to the original. Stored feed text is never returned by the API. The previous behaviour, which stored a feed excerpt and displayed it in the lesson card, is replaced.
- Feed text is still read at ingest time to decide which pathway and skill an item belongs to. That text is kept in a separate internal field used only for matching and discovery, and it is never served. Matching on text that was fetched is not republication of it.
- A separate excerpt field holds publisher text that a review has explicitly cleared for republication. It is empty by default, so a feed that has not been reviewed shows no excerpt rather than an uncleared one. Only reviewed text reaches the excerpt field.
- The reason is that excerpt reuse permission is the narrowest and hardest to obtain right of the ones a feed involves. Removing the dependency lets a feed be cleared for metadata reuse without also clearing excerpt reuse, which unblocks publishers that permit linking and attribution but not republication. MDN is the clearest example: its documentation is CC BY-SA 2.5, but its blog feed carries a reserved-rights notice, and the two are separate.
- The forward migration moves any existing stored text into the internal matching field and clears the excerpt, so no previously stored text is carried forward as publishable content.
- The API keeps reporting the publisher's reported rights string and still reports reuse as unverified. A licence string is a claim by the publisher, not permission confirmed by the owner.
