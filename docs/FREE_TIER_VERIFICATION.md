# O1 free-tier verification

Research date: 2026-10-13 (Africa/Nairobi). All official links below were checked on that date. Published terms can change; recheck before activation. This document records desk research, not service operation.

## Verdict

**O1 research complete; release gate BLOCKED.** The full Render/Neon/GitHub Actions/Brevo/Cloudflare R2 candidate stack is not verified as enforceably zero-charge. R2 subscription billing is a candidate-stack blocker: no provider-enforced zero-charge cutoff was verified. Do not activate it on the strength of allowances, alerts or application counters. No paid substitute is proposed.

Render's free-instance guidance discourages production use, despite the roadmap accepting sleep for a small public beta. Resolve suitability before O2; accepting cold starts alone does not resolve that guidance. GitHub scheduling cannot guarantee six-hour execution; O3 must explicitly define tolerated delay, stale-data handling and missed-run recovery. Brevo activation and domain authentication remain P4 gates. O4 backup storage, retention and restore remain blocked.

## Evidence boundaries and governance

- Published: the linked provider documentation/pricing supports the terms below.
- Account-specific: actual plan, eligibility, payment-method state, allowances shared with other projects, sender approval and selectable regions are **unverified**. A published free plan does not prove this owner's eligibility.
- Operational: deployment, cold-start timing, quota handling, recovery, delivery, schedules, DNS and TLS are **not tested**.
- GitHub REST PR #11 returned closed, merged=true, merged_at=2026-10-13T19:33:17Z and merge_commit_sha=6c70bf494dd1b7cee4f989f315bd99d267690c7b. git merge-base --is-ancestor confirmed it belongs to fetched origin/main. [Governance PR](https://github.com/michael-mathenge/soma-i/pull/11).
- Starting branch docs/working-rules and full HEAD 3beee75de1019c0499b8ffda93044a54de148633 matched. Created codex/free-tier-verification from merged origin/main. Local main stays at 391881e8818eff2cb99255d14b8d2de82054cf6b.
- Existing michaelmathenge.dev is owner-reported. Ownership/control, renewal cost, DNS capacity and chosen subdomain are unverified; no new domain purchase is authorized.
- No accounts, agreements, payment methods, services, DNS changes, email sends, database access or deployments were performed.

## Render: conditional hosting candidate

Free web supports custom domains/TLS. Idle after 15 minutes; restart takes about a minute. Filesystem changes disappear on sleep/restart/deploy; no persistent disk, shell or one-off jobs. Workspace allowance is 750 instance-hours/calendar month; exhaustion suspends free web until next month. Bandwidth exhaustion suspends free services without a payment method, but bills supplementary usage with one. Build exhaustion disables builds without a payment method or at the pipeline spend limit. High service-initiated traffic can also suspend a service. SMTP ports 25/465/587 are blocked. Free instances are discouraged for production. [Free instances](https://render.com/docs/free).

Hobby currently lists 5 GB outbound bandwidth and 500 pipeline minutes/month; these are workspace-shared, not per-service. Old workspace figures must not be reused. [Official hosting cost guide](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses), [platform plan table](https://render.com/docs/platform-features-by-plan). Actual workspace allotment and payment state must be recorded later. No time-limited web trial expiry is stated in the free-web documentation; this is not a permanence guarantee.

No-charge control: only select Free compute/Hobby, keep no payment method, prohibit paid jobs/disks/upgrades and verify those settings before deployment. An email alert or build-only spend limit does not cap every billing category. SMTP-based Brevo integration on the blocked ports fails this candidate; a reviewed HTTPS API integration is the proposed route, not tested.

Regions: Oregon, Ohio, Virginia, Frankfurt and Singapore; region changes require migration to a new service. [Regions](https://render.com/docs/regions). Frankfurt alongside Neon Frankfurt is a candidate, not a selection or Kenyan latency result. Render processes requests and potentially IP/request/error logs; minimize identifiers and never log passwords/tokens. Review its DPA, subprocessors and deletion/retention terms before learner data. [Security and subprocessors](https://render.com/security). Exact application-log retention is unresolved. Local files cannot be backups; deploy rollback does not restore learner data.

## Neon: conditional durable database candidate

Current [pricing](https://neon.com/pricing) publishes no card required, no time limit, 100 projects, 100 CU-hours/project/month, 1 GB/project, up to 2 CU and mandatory idle scale-to-zero after five minutes. Instant restore is limited to six hours or 1 GB of changes, with one manual snapshot. Scheduled backups are not included in the Free comparison. Pricing is the current planning baseline, not proof of an account entitlement.

Discrepancy resolved: the [official storage increase announcement](https://neon.com/blog/neon-free-plan-1-gb-per-project) explicitly increases 0.5 GB to 1 GB. An [older official scale-to-zero article](https://neon.com/blog/building-patterns-unlocked-by-scale-to-zero) still states 0.5 GB. The [current official FAQ source](https://raw.githubusercontent.com/neondatabase/website/main/content/faqs/free-plan-limits-and-quotas.md) now agrees with 1 GB, lists 20 GB account-wide storage and 5 GB public transfer/project/month. Compute/transfer exhaustion suspends connections until the next billing period; storage-increasing operations fail at the project/account cap. Free overages are not billed and these quota limits do not delete data. Keep Free; never auto-upgrade. Confirm actual account limits before O2.

Cold-start reconnect/retry and migration compatibility remain not tested. At minimum 0.25 CU, continuous 30-day operation needs 180 CU-hours, exceeding 100; keeping the database awake undermines this budget (calculation, not a load test). Inactivity policy outside normal quota suspension, account closure and post-deletion recovery remain unresolved.

[Regions](https://neon.com/docs/introduction/regions) include AWS Frankfurt and Singapore among US/European/Asia-Pacific locations; no Kenyan region is listed. Cross-provider connections use public TLS, not a shared private network. [Security](https://neon.com/security) describes encryption, restricted access, DPA and subprocessors. Learner email, password hashes and progress would be processed here; region choice alone does not prove all processing stays there. Review DPA/transfers and deletion handling before use. Six-hour history is insufficient for delayed incident discovery or a missed backup; restore/export and isolated recovery are not tested.

## GitHub Actions: conditional best-effort scheduler

[Billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) makes standard hosted runner use free for public repositories. Larger runners always charge. GitHub Free includes 500 MB artifact storage and 10 GB repository cache; storage shares/billing settings still matter. Without a valid payment method, usage beyond included quota is blocked. With billing enabled, extra storage may charge; public runner minutes do not make all Actions storage free.

[Schedule terms](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule): runs can delay or drop under load, run only on the default branch and disable after 60 days without repository activity. UTC is the default; minimum interval is five minutes. A six-hour cron is a requested cadence, not a guarantee. No free scheduler expiry is stated beyond inactivity disabling; no sleep/cold-start SLA is verified.

Proposed O3 controls: off-hour schedule, bounded timeout/retries, concurrency and idempotent due-work catch-up; persist last-success metadata and fail honestly when stale. An independent missed-run signal and manual recovery procedure must be defined; a dead scheduler cannot reliably alert about itself. No workflow was added or run.

No-charge gate: public visibility must remain true, use only standard Linux runners, disallow larger runners and paid cache increases, verify zero-budget stop controls/payment state, avoid backup artifacts/caches entirely. GitHub REST repository metadata returned visibility=public on 2026-10-13. Actions permissions and billing controls remain account-specific and unverified; recheck visibility before activation.

[Retention settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository) default logs/artifacts to 90 days; public retention permits 1-90 days. [Artifact deletion](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts) is irreversible. Public logs/artifacts must contain no learner data or database dumps. [Secret reference](https://docs.github.com/en/actions/reference/security/secrets) warns about redaction limitations with structured secret values. Hosted runner region/residency is not an app-controlled guarantee verified here. Least-privilege environment secrets, target allowlists and redacted identities are future reviewed-workflow gates.

## Brevo: conditional transactional email candidate

[Free-plan limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan) publish 300 sends/day, no rollover or time limit, 100,000 contacts and mandatory branding. At the daily transactional limit, up to 1,000 extra messages queue; beyond that they are undelivered. This is a delivery constraint, not permission to buy credits. [Free signup](https://www.brevo.com/products/marketing-platform/) says no card needed.

[SMTP troubleshooting](https://help.brevo.com/hc/en-us/articles/115000188150-Troubleshooting-Issues-with-Brevo-SMTP) confirms separate transactional activation. [Domain authentication](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC) requires owned/controlled DNS and Brevo code, DKIM and DMARC records. Actual activation, sender/domain approval and deliverability for michaelmathenge.dev remain unverified. No-charge controls: retain Free/no card, no purchased credits/add-ons/auto-upgrade, bounded app sending with recovery capacity reserved. Exact account reset boundary and queue/token expiry interaction need validation; no sleep or guaranteed delivery latency is established.

[Data storage](https://help.brevo.com/hc/en-us/articles/360001005510-Data-storage-location) lists EU hosting: OVH France/Germany and Google Cloud Belgium, replicated copies and at least weekly encrypted backups. These are provider resilience statements, not customer-controlled restore/RPO commitments. [Transactional logs/previews](https://help.brevo.com/hc/en-us/articles/360021533839-Manage-your-transactional-logs-and-email-previews) are retained indefinitely by default, configurable; deletion can take 72 hours and deleted events cannot be recovered. Configure minimum necessary retention later and disable unnecessary tracking/previews. Send only recipient and necessary message content; no password, profile export or learner progress. DPA/subprocessor and deletion-policy review remains open. Recovery delivery, bounded retries and expired-token handling are not tested.

## Cloudflare R2: blocked backup candidate

[Get started](https://developers.cloudflare.com/r2/get-started/) requires a Cloudflare account plus R2 subscription checkout and monthly usage billing. [Pricing](https://developers.cloudflare.com/r2/pricing/) includes Standard storage allowances of 10 GB-month, one million Class A and ten million Class B operations/month, free direct egress, then metered storage/operations with billing-unit rounding. Allowances do not apply to Infrequent Access; that class has retrieval/minimum-duration charges. No free trial expiry is stated; recurring allowances are not a zero-cost contract.

**No enforceable provider hard zero-charge cutoff verified.** Alerts, app limits, retention and scoped credentials can reduce exposure but cannot prove a billing ceiling under bugs, retries or stolen credentials. Do not subscribe/provision until an enforceable no-charge route is verified; no paid alternative authorized.

[Data location](https://developers.cloudflare.com/r2/reference/data-location/) distinguishes best-effort hints from jurisdiction restrictions. Automatic location/hints do not promise Kenyan/EU residency; a jurisdiction restriction would need explicit selection and review. [Data security](https://developers.cloudflare.com/r2/reference/data-security/) describes provider-managed encryption at rest and TLS. O4 additionally needs client-side encrypted private dumps, separate key custody, scoped credentials and no public bucket/domain.

[Object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/) support expiration and incomplete-upload cleanup; lifecycle cleanup is not a spend cap or restore guarantee. No customer backup retention exists until designed/configured. Provider durability alone does not recover accidental deletion or unusable encryption keys. Before O4 passes, document snapshot count/size/retention and operation budgets, deletion lag, key recovery, integrity verification and restore into isolated disposable staging. Approved recovery targets and measured RPO/RTO remain unresolved; no dump or restore was performed.

## Unresolved release gates

| Gate | Required evidence before passing |
|---|---|
| O1 cost | Provider-enforced zero-charge backup route; all account plan/payment/cap settings recorded. R2 is blocked now. |
| O2 hosting | Resolve Render production suitability; verify Free eligibility, allowances, region, same-origin DNS/TLS and measured cold starts. |
| P4 email | Brevo transactional approval, domain control/authentication, no-charge settings, quota-aware recovery and actual controlled delivery. |
| O3 cadence | Explicitly accept best-effort timing or resolve strict six-hour requirement; prove catch-up, stale-data behavior, missed-run detection and manual recovery. |
| O4 recovery | Approved retention/RPO/RTO, independent encrypted storage and key recovery, isolated restore and cleanup evidence. Neon history is insufficient alone. |
| Privacy | Minimized data flow, provider DPA/subprocessors/transfers, logs/previews retention and deletion across backups; no learner-data upload yet. |
| R1 release | All runtime/content/security/quality gates plus explicit owner release approval. |

Research does not authorize activation. Unrelated roadmap implementation can proceed within its approved scope; O2/O3/O4 and public release must not treat this document as a passed infrastructure gate.

## Validation scope

Application tests: **not tested** (documentation-only). Provider operations and account eligibility: **not tested**. Documentation consistency, UTF-8/CRLF, preserved planning history, scoped diff and git diff --check are checked in the O1 validation log in docs/PLANS.md.

## P4 offline foundation and live-delivery gate - 2026-10-14

The O1 research/validation above remains historical. P4 now has an offline verification/recovery implementation, with application validation in docs/PLANS.md. This does not pass the live-email gate. Delivery defaults to disabled; only development/test can select Django's explicit in-memory backend. Staging/production reject that mode, and no SMTP/HTTPS Brevo adapter exists. No account, agreement, payment method, credential, DNS change or real message was used.

Official sources rechecked 2026-10-14: [Free-plan limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan) still publish 300 sends/day with no rollover; up to 1,000 additional transactional messages queue, then excess messages are not delivered. [Transactional activation](https://help.brevo.com/hc/en-us/articles/115000188150-Troubleshooting-Issues-with-Brevo-SMTP) and [domain authentication](https://help.brevo.com/hc/en-us/articles/12163873383186-Authenticate-your-domain-with-Brevo-Brevo-code-DKIM-DMARC) remain required published steps. These are published terms, not evidence of this owner's plan, activation, authenticated sender/domain or delivery.

Live P4 remains **BLOCKED** pending account-specific free eligibility/no-charge settings, transactional approval, authenticated sender/domain under michaelmathenge.dev, privacy/DPA/subprocessor/log-preview retention review, bounded quota use with recovery capacity, and a separately authorized controlled delivery/expiry/failure validation. The 30-minute reset expiry and 24-hour verification expiry are application choices tested offline; queued provider messages could arrive too late. Queue delay/expiry interaction, reset boundary, deliverability and operational recovery are not tested. No quota allowance is treated as a spending cap; no paid substitute is proposed. O1's R2/Render/scheduling blockers and C1 source-rights gate remain unchanged.

Offline evidence: test_deployed_runtime_never_enables_memory_delivery, test_settings_reject_deployed_preview_without_database_connection, test_preview_uses_fixed_fragment_link_and_explicit_memory_backend, test_recovery_request_is_generic_for_unknown_unverified_inactive_and_malformed, and test_expiry_and_replacement_make_old_tokens_unusable in backend/learners/tests/test_recovery.py. Shared request limits remain P5; broad caching/concurrency/retention/release gates remain outstanding. Application preview success is not provider or public-release approval.
