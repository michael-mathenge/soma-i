# RSS sources

**Current release status (2026-10-13): C1 is BLOCKED.** The October 8 registry checks below are historical demo evidence, not production rights approval. The dated C1 review at the end governs new public-beta use; none of the 11 registered feeds is cleared for production ingestion or excerpt republication.

The registry is maintained in `backend/content/feeds.json`. The feed checks
below were run on 8 October 2026 and returned HTTP 200. Counts and dates are
feed evidence, not a guarantee that a publisher will keep the endpoint
unchanged. Each accepted feed has `stale_after_days: 60`; staleness uses the
latest published or updated item date. Feeds without usable item dates are
flagged stale. Fetch time never makes a feed fresh.

| Feed | Pathways | Type | Attribution | Rights | Entries | Latest item |
|---|---|---|---|---|---:|---|
| freeCodeCamp Data Analysis | Data Analyst | nonprofit | freeCodeCamp | not stated | 15 | 19 Sep 2026 |
| freeCodeCamp SQL | Data Analyst | nonprofit | freeCodeCamp | not stated | 15 | 29 Sep 2026 |
| freeCodeCamp Python | Backend/Python Developer | nonprofit | freeCodeCamp | not stated | 15 | 29 Sep 2026 |
| freeCodeCamp JavaScript | Frontend Developer; Backend/Python Developer | nonprofit | freeCodeCamp | not stated | 15 | 4 Oct 2026 |
| freeCodeCamp Git | Frontend Developer; Backend/Python Developer | nonprofit | freeCodeCamp | not stated | 15 | 14 Sep 2026 |
| freeCodeCamp CSS | Frontend Developer | nonprofit | freeCodeCamp | not stated | 15 | 1 Oct 2026 |
| freeCodeCamp HTML | Frontend Developer | nonprofit | freeCodeCamp | not stated | 15 | 22 Jul 2026 |
| Real Python | Backend/Python Developer; Data Analyst via keyword matching | publisher | Real Python | not stated | 50 | 8 Oct 2026 |
| CSS-Tricks | Frontend Developer | publisher | CSS-Tricks | not stated | 15 | 31 Aug 2026 |
| DEV.to SQL | Data Analyst | community | DEV Community | not stated | 12 | 8 Oct 2026 |
| DEV.to beginners | all three pathways | community | DEV Community | not stated | 12 | 8 Oct 2026 |

The original link and source attribution are retained; feeds provide summaries,
not article bodies. Feed text is treated as untrusted input.

## Rejected or retired candidates

| Candidate | Reason |
|---|---|
| MIT News Research | Credible research reporting, but not entry-level learning material. |
| MDN Blog | Latest checked item was 15 Jun 2026 (over 60 days old on the check date); feed states “All rights reserved 2023, MDN.” |
| freeCodeCamp React | Latest checked item was 2 Apr 2026, over 60 days old. |
| freeCodeCamp digital marketing | Latest checked item was 7 May 2020; too stale for the pathway. |
| web.dev Blog | Latest checked item was 29 May 2026, over 60 days old. |
| HubSpot Marketing | Vendor content; not needed for the accepted pathway registry. |
| DEV.to Python | Community feed had ads and spam in the checked sample. |
| DEV.to datascience | Checked entries were research-heavy and not entry-level. |
| General freeCodeCamp News RSS | Retired in favor of the accepted topic-specific feeds, which are easier to match to pathways. |

None of these sources is locally African. The local layer is the Ajiri
opportunities story and its sample opportunity data; the RSS content itself
does not claim local relevance.

## C1 RSS rights verification - 2026-10-13

### Verdict and evidence boundaries

**Desk review recorded; C1 release gate BLOCKED.** All 11 registry entries still declare rights as not stated. Availability and free reading do not establish permission to automate retrieval or republish feed text. No registered feed passes both rights and current operational verification in this task. Do not activate these feeds for the public beta on the strength of the historical HTTP 200 table.

The reviewed publisher/platform groups are freeCodeCamp, Real Python, CSS-Tricks/DigitalOcean and DEV/Forem. Seven freeCodeCamp topic feeds count as one publisher, and DEV tag feeds as one platform, not independent publishers per tag. Author identity and independent editorial provenance need item-level checks. The brief requires at least two independent publishers per pathway and three resources per skill; the spec also requires manual verification across at least three independent publishers. Reviewing three sets of terms is not the same as obtaining three approved sources or proving curriculum coverage.

All source links below were reviewed on 2026-10-13 (Africa/Nairobi). Web research results may use indexed/cached publisher pages. A research-tool error is recorded as such: it is not a measured origin outage or proof that the feed is gone. No fresh parsed entry counts, full-feed dates, HTTP status sweep or scheduled ingestion were obtained. The October 8 counts/dates remain historical.

No publisher contact, signup, licence purchase, scraping, database access or ingestion command occurred. Article/policy pages were read for research; no full articles, images or feed payloads were saved to the repository. No access restriction was bypassed. Application tests: **not tested** (documentation-only).

### Registered endpoint inventory and current decision

A = freeCodeCamp automation/reuse permission unresolved; B = Real Python public-reuse permission unresolved; C = CSS-Tricks current policy/access unresolved; D = DEV default copying/public-display restriction. These are production decisions, not changes to backend/content/feeds.json.

| Registry key | Exact endpoint | Research-tool result on 2026-10-13 | Production decision |
|---|---|---|---|
| fcc_data_analysis | [Data Analysis RSS](https://www.freecodecamp.org/news/tag/data-analysis/rss/) | Cache miss; no parsed XML | BLOCKED A |
| fcc_sql | [SQL RSS](https://www.freecodecamp.org/news/tag/sql/rss/) | Cache miss; no parsed XML | BLOCKED A |
| fcc_python | [Python RSS](https://www.freecodecamp.org/news/tag/python/rss/) | Unsupported application/xml; no parsed XML | BLOCKED A |
| fcc_javascript | [JavaScript RSS](https://www.freecodecamp.org/news/tag/javascript/rss/) | Cache miss; no parsed XML | BLOCKED A |
| fcc_git | [Git RSS](https://www.freecodecamp.org/news/tag/git/rss/) | Cache miss; no parsed XML | BLOCKED A |
| fcc_css | [CSS RSS](https://www.freecodecamp.org/news/tag/css/rss/) | Cache miss; no parsed XML | BLOCKED A |
| fcc_html | [HTML RSS](https://www.freecodecamp.org/news/tag/html/rss/) | Cache miss; no parsed XML | BLOCKED A |
| realpython | [Real Python Atom](https://realpython.com/atom.xml) | Unsupported application/xml; no parsed XML | BLOCKED B |
| csstricks | [CSS-Tricks RSS](https://css-tricks.com/feed/) | Tool reported 403 Forbidden; no parsed XML | BLOCKED C |
| devto_sql | [DEV SQL RSS](https://dev.to/feed/tag/sql) | Not accessible through research tool | BLOCKED D |
| devto_beginners | [DEV beginners RSS](https://dev.to/feed/tag/beginners) | Not accessible through research tool | BLOCKED D |

### Publisher policy findings

**A - freeCodeCamp.** [Terms of Service](https://www.freecodecamp.org/news/terms-of-service/) (page dated May 25, 2018) restrict automated access/monitoring except public search-engine indexing. They retain contributor ownership and leave other permissions to contributors. No RSS-specific exception or permission for SOMA.i public excerpt storage was verified. [Copyright policy](https://www.freecodecamp.org/news/copyright-policy/) describes takedowns, not a blanket reuse licence. The [repository BSD licence](https://github.com/freeCodeCamp/freeCodeCamp/blob/main/LICENSE.md) covers that software; it cannot establish News article rights. The [curriculum announcement](https://www.freecodecamp.org/news/building-a-data-science-curriculum-with-advanced-math-and-machine-learning) describes CC-BY-SA coursework, not a licence for every News contributor article. Require a documented RSS access basis and applicable item/excerpt licence before activation. Preserve original URL, publisher, author and supplied notices; attribution alone cannot cure missing permission. Public News reading is supported by the [publisher's mission statement](https://www.freecodecamp.org/news), but free access is a separate gate.

**B - Real Python.** [Terms](https://realpython.com/terms/) (last updated September 22, 2026) reserve intellectual-property rights and limit copying/display of portions to one's own non-commercial use or ordering. No exception permitting a public SOMA.i excerpt catalogue was verified. A non-commercial project is not automatically the same as personal use. Require an applicable syndication/reuse grant before public storage/display. Attribution should identify Real Python, the named author and original resource URL, with any required notices. [The homepage](https://realpython.com/) mixes articles, courses and membership offerings; a feed inclusion or visible course overview does not prove the full learning resource is freely accessible. No account/payment was used.

**C - CSS-Tricks.** The current [licence endpoint](https://css-tricks.com/license/) and homepage/feed could not be verified through the tool; the licence/feed returned 403. Indexed official [RSS discussion](https://css-tricks.com/is-having-an-rss-feed-just-giving-content-away-for-free/) (February 7, 2020) describes syndication and programmatic post lists. It is not a verified current, item-specific excerpt grant. An indexed [About page](https://css-tricks.com/about/) says the site is powered by DigitalOcean. A third-party copy of an older permissive Chris Coyier licence was found but is not accepted as current publisher evidence. Do not infer article rights from old code/design permission. Require current publisher policy, authorship/licence scope and accessible feed evidence; retain author, CSS-Tricks and the original URL if later approved. Free article access for current items remains unverified.

**D - DEV.** [Terms](https://dev.to/terms) grant temporary personal non-commercial viewing and restrict copying, transfer/mirroring and public display, including non-commercial display. They also reserve brand/logo uses and require contributors to own posting rights. This does not grant SOMA.i a general RSS republication licence. Both tag feeds remain blocked for automated public ingestion/excerpt reuse absent an applicable permission that resolves platform and author scope. An individual author's explicit licence would need verification for that item; it cannot clear all tag-feed entries. Preserve author identity, DEV, source URL, licence/notice evidence and original canonical provenance when supplied. Do not use DEV logos or imply endorsement. A public tag page can be read without login, but article-level English/free access and suitability remain separate checks.

These are conservative project gate decisions based on published evidence, not claims that RSS itself transfers copyright or that a particular statutory exception applies. The 300-character cap is a product maximum, not a legal safe harbour. Unknown, contradictory or inaccessible permission evidence means no copied excerpt; linking/metadata use also needs its own approved basis rather than bypassing a blocked feed.

### Limited manual reading and date checks

| Publisher | Official sample read | Observation and limit |
|---|---|---|
| freeCodeCamp | [SQL subqueries article](https://www.freecodecamp.org/news/how-to-work-with-subqueries-in-sql/) | Tool exposed substantive English article content without login; Abdullah Rufai, August 17, 2026. The prerequisite section requires prior SQL knowledge. One article is not a whole-feed access/rights check or beginner curriculum approval. |
| Real Python | [Python first steps article](https://realpython.com/python-first-steps/) | Tool exposed substantive English article content without login; Leodanis Pozo Ramos, updated October 13, 2025. The separately listed course is a different resource; membership pricing exists. No full-course access claim is made. |
| DEV | [SQL tag listing](https://dev.to/t/sql) | Public English titles, authors and tags were visible; opening the selected execution-order article failed through the tool. Full article/free access, absolute publication date and excerpt rights were not verified. |
| CSS-Tricks | [Homepage](https://css-tricks.com/) | Tool reported 403; no current article-access or date claim. |

The sample dates above are within 24 months of this check; that does not establish pathway coverage. Prefer the resource's absolute published/updated date over relative listing ages, and record which supplied it. Fetch time cannot make content fresh. English tag names do not prove English article content (the SQL listing also includes a Spanish course). Paywalled/logged-in destinations, missing/future/conflicting dates and unknown author/licence information require item-level review; older foundations require explicit evergreen classification. No destination-page bandwidth was measured, so the existing low-data flag is not such evidence.

### Historical candidates and licence scope

The rejected/retired table above stays as history. No previously rejected feed is reactivated by C1, and its old staleness date is not a current check. MDN documentation has an [official attribution/licensing policy](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Attrib_copyright_license) allowing documented reuse under CC-BY-SA with attribution and exceptions; it does not by itself prove rights for the separate MDN Blog feed that historically carried a reserved-rights notice. The attempted MDN Blog and web.dev feed opens were unsuccessful in this tool. Neither is approved as a replacement. MIT News, HubSpot and the other retired variants were not re-fetched or newly rights-cleared; no scraping, paid content or silent substitute was introduced.

### Required handoff to C2/C3 and release

Read-only code evidence: backend/content/feeds.json has 11 entries with rights not stated. backend/content/ingestion.py defines a 300-character summary cap, cleans and stores excerpts in ingest_entries, and processes feed content for word counts. backend/content/management/commands/ingest_feeds.py copies the rights string into source metadata; the inspected path does not gate fetching/storage on verified permission. Thus the historical assertion that feeds supply only summaries must not be assumed universally. A feed can include article bodies even when the database saves only an excerpt.

This documentation does not implement a guard or alter active flags/data. Before any public-beta ingestion, a separately scoped implementation must enforce permission before fetching and before copied text is persisted or exposed. Unknown/revoked permissions must fail closed. C2 needs visible source/author/canonical URL and licence/permission evidence, review date/scope, date provenance and correction/takedown handling. C3 needs an approved endpoint allowlist, bounded requests/size/time/retries, redirects and destination checks, conditional requests where available, and honest failure reporting. A robots file or HTTP 200 cannot substitute for reuse terms.

C1 can pass only when:

- A documented applicable permission clears automated feed access and the specific public metadata/excerpt use, including authors and third-party materials; policy ambiguities are resolved without treating a software licence as an article licence.
- Permitted endpoints are checked with bounded RSS/Atom requests, parsed successfully and dated; item links/English/free access, author/canonical provenance and staleness are verified. Do not scrape article bodies or work around access controls.
- At least three independent publishers satisfy the manual source-verification gate; each proposed pathway separately meets its two-publisher/three-resources-per-skill requirements and original checkpoint rules.
- Unknown/unapproved entries cannot be activated, their text cannot leak through old data or caches, and permission revocation/takedown can be handled without erasing historical provenance.

Publisher clarification/contact, if needed, requires a separately authorized action; no messages were sent. Until those gates pass, C2/C3 may build the approved controls but must not label candidate sources verified. O1 remains blocked independently; C1 research is not deployment or public-release approval.

## C3 feed-fetch enforcement - 2026-10-14

C3 implements safeguards; it does not clear any publisher rights. All 11 registered feeds still lack permission evidence and live ingest_feeds therefore blocks them before a source is created/updated or a fetch occurs. --force bypasses only the minimum fetch interval; --reference-date changes staleness reporting, never permission validity. C1 and O1 remain BLOCKED.

### Permission evidence contract

A future, separately reviewed registry change must supply a permissions object. The code treats it as trusted operator-reviewed evidence, not an automatically verified licence or an account approval. No such objects were added to backend/content/feeds.json in C3.

| Field | Enforced requirement |
|---|---|
| feed_access | Boolean true for automated access to the feed. |
| metadata_reuse | Boolean true for the intended public metadata use. |
| excerpt_reuse | Boolean true for the intended capped public excerpt use. |
| reviewed_by | Nonempty reviewer identity; this is operational evidence, not learner profile data. |
| scope | Nonempty description of the covered metadata/excerpts, author and third-party limitations; semantic rights review remains C1 work. |
| evidence_url | Valid HTTPS evidence link, without userinfo, fragment or unsafe destination syntax. It is not fetched by the permission checker. |
| reviewed_on, expires_on | Valid dates with reviewed_on <= actual current date <= expires_on and a window at most 90 days. This is the project's re-review policy, not a publisher's licence term. Earlier real expiry/revocation must be reflected. |
| allowed_urls | One to six exact approved HTTPS endpoints, including the registry URL and each permitted redirect target. A host-wide wildcard, rights string or arbitrary caller URL is not permission. |

Permission is checked again after fetching, before 304 validator writes and before entry ingestion. A missing/false/malformed/future/expired grant fails closed. Evidence still needs the C1 article/author/free-access/provenance checks; flag values cannot prove legal permission. Review changes through a dedicated approved file scope rather than treating this schema as an invitation to fill in unverified grants.

### Transport and parser limits

- Initial and redirect URLs must be exact allowlisted HTTPS endpoints on port 443. Userinfo, fragments, controls/whitespace, backslashes and local/ambiguous hostnames are rejected. DNS answers must all be public unicast addresses; private, loopback, link-local, shared, multicast, reserved and unsafe IPv6 transition destinations are rejected, including mixed public/private answers.
- Connections use at most two vetted numeric DNS addresses per request, retaining the original TLS hostname and certificate verification. This prevents a second hostname lookup between validation and connection. Redirect targets are resolved/checked independently. The direct transport does not consume environment proxy settings and forbids tunnelling.
- Socket operations are capped at ten seconds and the whole network fetch at twenty seconds, including DNS waiting, redirects and retry delays. A watchdog closes/shuts down the active connection at the deadline, including TLS/header/body reads. The underlying OS DNS call can finish later in a daemon worker; no connection is opened from a late/unvalidated result.
- There are at most two attempts and five redirects per attempt. Only transient connection/DNS failures and HTTP 429/500/502/503/504 are retried. Retry delay defaults to one second and cannot exceed two seconds or the remaining total budget; a larger/invalid Retry-After fails instead of retrying early. TLS validation failures, invalid URLs, permission blocks, unsafe destinations and malformed payloads are not retried. Cross-host redirects drop conditional validators.
- Bodies are bounded to 5 MiB by declared length and chunked reads. Invalid/negative lengths, truncated declared bodies and compressed responses fail; the request asks for identity encoding. Parsing/storage are separate from the network deadline: UTF-8 RSS/Atom XML is required, HTML/unsupported media types and DTD/entity declarations are rejected, and parsing is capped at 500 entries before writes. Feeds with usable partial entries retain a generic warning; raw parser exceptions are not logged.
- ETag/Last-Modified values must fit their model fields and contain no CR/LF. Unexpected exceptions are logged by class; fixed controlled diagnostics never echo remote body text, credential-bearing URLs or raw network exceptions. Other registry feeds can continue, but any blocked/failed feed makes the aggregate command raise CommandError after its summary, so schedulers receive failure rather than a partial-success exit.

Design references reviewed on 2026-10-14: [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [Python 3.13 HTTPS client](https://docs.python.org/3.13/library/http.client.html#http.client.HTTPSConnection), and [Python default TLS context](https://docs.python.org/3.13/library/ssl.html#ssl.create_default_context). These support the design review; mocked tests are the implementation evidence, not a live provider/TLS compatibility check.

### Offline and release boundaries

--offline remains a local fixture path and never calls the fetcher. It requires an in-memory SQLite target (including an explicitly parsed mode=memory URI) or a SQLite file resolved under OS temp; repository/hosted targets are rejected before source writes. These fixtures are test/demo evidence, not publisher approval. The caller must still print its explicit temporary DATABASE_URL before any database-backed command.

C3 guards this live management-command entry point. The internal ingest_entries function and existing seeded/stored records/caches are not globally permission-filtered or purged by this change. Direct trusted local fixture helpers remain in use; production initialization, API visibility and cache cleanup must honor C1 before release. Do not activate legacy candidate rows merely because the fetch command is now protected.

Tests use fabricated grants on example.test endpoints, patched DNS/socket/HTTP/TLS operations and existing offline RSS bytes only. No live feed was fetched, no publisher was contacted, no real registry grant was created, and no service/database was provisioned or deployed. Live provider compatibility, rights clearance and real ingestion across three independent publishers are **not tested** and remain blocked. The exact test outputs and retained roadmap history are recorded in docs/PLANS.md.


## C5 coverage-gated discovery - 2026-10-14

C5 implements a local, network-free publication engine over stored metadata. It does not approve any real publisher or activate a public beta. The real feed registry is unchanged, all 11 feeds still lack C3 permission evidence, discovery_rules.json has an empty publishers map, and migrations create no ResourceReview approvals. O1/C1 remain BLOCKED. Evidence: test_actual_unapproved_registry_cannot_publish_stored_demo_items and local discover_pathways dry-run/apply outputs recorded in PLANS.md.

### Trusted evidence and matching data

RSS/Atom tags are stripped to plain text, case-folded and limited to 32 distinct tags of at most 120 characters. Known configured category aliases can retain a candidate outside the legacy title matcher; unknown unmatched categories do not invent a curriculum. Existing quiz/community exclusions apply to category candidates and reviewed resources. Title/excerpt/category matching uses escaped token boundaries, never executes feed instructions, and does not scrape destination pages. Evidence: test_rss_categories_are_bounded_sanitized_matching_data, test_known_rss_category_can_store_candidate_outside_legacy_title_matching, test_unknown_rss_category_does_not_invent_a_curriculum_or_store_unmatched_text, test_discovery_categories_do_not_bypass_feed_exclusions and test_reviewed_resource_still_obeys_feed_exclusion_rules.

The owner-controlled discovery_rules.json defines topic identities, aliases, ordered skills, prerequisites and original practice/check-in criteria. The initial definitions cover data analysis, accessible web foundations and Python service foundations, with three skills each; they are not a catalogue ceiling. Every definition must have 3-8 distinct skills and explicit checkpoint criteria/questions. Prerequisites must refer to earlier configured skills; cycles and unknown prerequisites are rejected. Unsupported categories remain unpublished instead of producing inferred occupations or job qualifications. Evidence: test_fourth_rule_has_no_hardcoded_catalogue_ceiling, test_unknown_or_incoherent_curriculum_rules_never_publish and test_unknown_categories_cannot_invent_a_curriculum.

Eligibility requires all of the following evidence; a licence string, English-looking title, tag or low-data flag cannot supply it:

| Evidence | Enforcement |
|---|---|
| Feed access and excerpt reuse | Current approved_feed_urls evidence from C3 for the exact source URL; source must be active. No real grants are added. |
| Publisher identity | Feed publisher_key matches ResourceReview.publisher_key and an owner-reviewed publishers entry. That entry has reviewed_by, reviewed_on, expires_on, evidence_url, domains and independence_confirmed=true. Both feed and resource hosts must belong to those reviewed domains. Overlapping domains assigned to different publisher identities fail validation. Multiple feeds/tags under one publisher_key count once. |
| Resource access/language/authorship | ResourceReview explicitly records free_access, english_confirmed, author, reviewer, evidence URL and review/expiry dates. Both stored source and item language must be en. These are owner-reviewed claims, not facts inferred from RSS or automatically checked at the destination. |
| Binding to reviewed content | A SHA256 fingerprint binds title, excerpt, item/source URLs, language, published/updated date provenance and normalized tag data. Changed metadata needs a fresh review. Retrieval timestamps alone do not invalidate an unchanged review or make old content fresh. |
| Dates and evergreen classification | Known non-future published/updated time and a non-future retrieval time are required. The recency boundary is 24 calendar months. Older material needs evergreen=true plus an explicit reviewed reason; future dates are never rescued by that flag. |
| Review lifetime | Resource and publisher review dates must include the actual evaluation date and span at most 90 days, matching the existing project re-review policy. This is a project limit, not a publisher term. Earlier revocation must be reflected immediately. |

Independent editorial ownership still needs human verification and dated evidence; different domains alone do not prove independence. Resource reviews and publisher declarations have no public write API or implemented hosted import workflow in C5. Future real approvals require C1 clearance and a separately reviewed operational workflow. No publisher was contacted and no destination was fetched. Relevant evidence: test_unverified_or_changed_resources_cannot_publish, test_one_publisher_across_multiple_feeds_is_not_independent_coverage, test_overlapping_publisher_domains_fail_closed, test_duplicate_tracking_urls_never_increase_resource_count, test_explicit_evergreen_review_accepts_old_foundations_but_not_future_dates and test_24_month_boundary_uses_calendar_months.

### Publication, continued access and scheduling limits

For each configured topic, every skill needs at least three distinct eligible resources, with at least two independent publisher identities across the pathway. Canonical URL normalization removes tracking/fragment duplicates. Selection is deterministic and retains publisher diversity even when the first three sorted resources come from one publisher. Publication binds three selected resources to each step and snapshots dated resource, publisher and feed-permission evidence. Identical inputs reuse the published revision; a changed curriculum or selected content creates another version, retiring the earlier version without moving learners or changing their checkpoint records. The whole apply run is transactional, including observations and resource/skill bindings; a later topic failure rolls back earlier writes from that run. Evidence: test_publication_is_deterministic_and_repeat_run_preserves_revision_and_resources, test_selected_three_resources_retain_two_publishers_even_if_sorted_first_three_do_not, test_failure_before_activation_rolls_back_all_revision_and_audit_writes, test_later_topic_failure_rolls_back_earlier_publication_in_same_run, test_new_revision_never_moves_enrolled_learner_or_changes_bound_resources and test_publication_retains_dated_evidence_snapshot_after_review_revocation.

Current review/permission validity is checked again for live revision reading picks. Revoked, expired or changed resources disappear immediately, with no fallback to unrelated or unreviewed items. Historical demo recommendations remain isolated under is_demo; C5 does not make old stored rows, cache entries or demo content release-approved. Public provenance UI remains conservative and unchanged. Evidence: test_resource_revocation_removes_reading_immediately_without_fallback, test_repeat_retrieval_does_not_invalidate_unchanged_review_but_content_edits_do and test_unreviewed_non_demo_pathway_never_falls_back_to_seeded_reading.

Coverage observations retain reports. First failed evaluation starts a persisted seven-day elapsed-time clock; a healthy observation resets it. Repeated failures after seven elapsed days close new enrollment while preserving learner/version/progress IDs. Missing jobs do not reset that clock or count as successful observations; this is conservative treatment of unverified intervals, not proof that a feed was continuously unavailable. A removed rule is monitored as failed coverage. Independently, a managed live version with no evaluation in the last 24 hours (or a future evaluation timestamp) cannot accept new enrollment. No schedule is created here and six-hour reliability is not claimed; O3 must supply reviewed hosted scheduling and monitoring. Evidence: test_coverage_loss_closes_after_seven_elapsed_days_and_preserves_learners, test_good_observation_resets_failure_clock_and_missed_jobs_do_not_reset_it, test_removed_rule_eventually_closes_managed_enrollment, test_stale_coverage_blocks_new_enrollment_until_a_new_observation and test_future_coverage_timestamp_cannot_enable_enrollment.

The discover_pathways command defaults to a write-free dry run; --apply is explicit. Both modes reject repository and hosted database targets before queries and require an explicit OS-temp/in-memory SQLite target. Command success can report blocked topics with zero writes; it is not a release-gate pass. Invalid rules/changed activation coverage fail with a nonzero CommandError. Hosted execution remains disabled until the separately reviewed target-allowlisted workflow exists. Evidence: test_dry_run_reports_eligibility_without_creating_catalogues_or_audits, test_command_defaults_to_dry_run_and_apply_stays_local, test_command_refuses_missing_target_before_database_reads and test_command_refuses_hosted_and_repository_targets_without_opening_them.

New tables contain public resource metadata, operator review identity/evidence and coverage observations, not new learner profile fields or full articles. Published resource bindings/snapshots use the C4 model/bulk-write guards; raw SQL/base-manager writes and shared Skill mutations remain outside those safeguards. Retention/export/backup/recovery workflows and PostgreSQL/concurrent-write behavior are not tested or implemented here. Reversing these migrations removes the newly added review/tag/link/observation/coverage data but preserves original content, pathway and progress rows in the SQLite round-trip test; this is not a production recovery drill. Evidence: test_discovery_migrations_preserve_legacy_content_versions_and_progress_without_approvals. Real resources/rights, coverage across three independent publishers for release, provider operations, private-cache hardening, hosted jobs and owner release approval remain open gates.
