# SOMA.i Product Brief

**Purpose:** Help a learner connect short, curated lessons to practical skills, visible progress, and a plausible next step.

## One learner

- **ASSUMPTION:** Amina Demo is 23.
- **ASSUMPTION:** Amina lives in Nakuru.
- **ASSUMPTION:** Amina works part-time in retail.
- **ASSUMPTION:** Amina uses an entry-level Android phone with prepaid data.
- **ASSUMPTION:** Amina prefers English and can switch to Kiswahili.
- **ASSUMPTION:** Amina is aiming for a junior data role.

## One problem

**ASSUMPTION:** Amina starts self-paced learning but drops off within 2–3 weeks because nobody checks in on her progress and she cannot see how what she is reading connects to a job. Evidence for any broader drop-off rate: **[verified source needed]**. This brief makes no statistical claim.

## Product response and wow moment

SOMA.i gives Amina a Data Analyst pathway with curated, low-data reading, small checkpoints, and weekly reminders. Her demo flow and reminder are in English; the interface and reminder are also available in Kiswahili. After she submits a checkpoint, the same result screen shows the next skill unlocked, reading picks, and related sample opportunities. The opportunities are clearly labelled examples, not live vacancies. That immediate connection from effort to progress and a possible next step is the wow moment.

## We will not build in the original capstone

- Real SMS delivery
- User accounts
- Live opportunity aggregation
- Deployment

The capstone builds on SOMA.i’s existing Django and React proof of concept. Its success is demonstrated through Amina’s seeded learning journey, a reliable `/next` result, relevant content across all three pathways, and reusable Codex assistance. Assumptions above describe a demo persona and need validation with real learners before being treated as research.

## Approved public-beta extension - 2026-10-13

The owner approved an English-first small public beta with real RSS-linked learning content, a polished mobile-first UI, optional durable accounts and free hosting. Sleep/cold starts are acceptable and will be disclosed. The original capstone exclusions above describe that earlier scope; optional accounts and deployment are now permitted only under this extension. Real SMS and live opportunity aggregation remain excluded.

### Identity and privacy

Account creation adds an email address and password credential alongside the existing optional display name, language/pathway preferences and optional phone. Store passwords only through Django's password-hashing system, never as readable profile data. Guests keep access to learning and progress; email/password identity is optional. Verification and recovery require a verified free provider. No additional demographic fields, advertising profiles or session-replay analytics are authorized.

### Content-driven pathways

The three initial pathways are migration seeds, not a catalogue ceiling. Discover topic candidates from verified RSS categories and configured synonym/prerequisite rules. Automatically publish only pathways with 3-8 ordered skills, at least three distinct freely accessible English resources per skill, at least two independent publishers overall, valid provenance/dates and original practice/checkpoint criteria. Recency-sensitive resources must be within 24 months; older foundational content needs explicit evergreen classification. Unknown topics without coherent prerequisites/checkpoints remain unpublished. Preserve active learner pathway versions. Coverage below threshold for seven consecutive days stops new enrollment while preserving existing learners.

### Release boundaries

Link out to original resources; never scrape or store full articles/paywalled text/copied images. Feed-provided excerpts are capped at 300 characters and stored only where publisher permission is verified. Every candidate feed remains to verify until checked. New pathways describe learning topics, not inferred hiring qualifications. Sample opportunities remain visibly labelled. Existing Kiswahili UI is interface-only/experimental; translation expansion is next scope.

Use the existing owner-reported michaelmathenge.dev domain without a new purchase. Free hosting, database, email, scheduling and backup terms are verification gates; stop rather than silently use paid services. This beta is not an uptime-guaranteed service and its usefulness still needs learner research.
