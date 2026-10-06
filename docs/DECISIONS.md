# Decision log

- Use anonymous Django sessions for a low-friction demo because the requested pages do not include sign-in or password recovery.
- Use SQLite by default and `DATABASE_URL` for a straightforward later PostgreSQL switch.
- Use RSS fixtures and patched parser results in automated tests; live feed requests are a documented manual acceptance check.
- Match by simple case-insensitive keyword overlap and retain source/date traceability instead of using paid AI or hidden ranking.
- Prefer skill score first, then low-data items; this keeps relevance primary while surfacing bandwidth-friendly options.
- Weekly reminders are the default. Console output is the working sender; Africa's Talking remains a credential-driven sandbox stub.
- Opportunity records are labelled sample examples and are not represented as currently open vacancies.
- Cache static shell plus recent GET payloads with a native service worker; keep completion writes online to avoid sync conflicts.
