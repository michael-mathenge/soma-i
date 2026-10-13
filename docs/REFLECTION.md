# SOMA.i development reflection

I originated the SOMA.i idea and used AI software-development tools to help turn it into a working proof of concept. My biggest lesson was getting started with AI development and engineering with OpenAI: moving from my own idea to a working model I could demonstrate. This reflection combines that personal account with the recorded project evidence.

## Problem and design choices

SOMA.i focuses on connecting a learning task to visible skill progress and a possible next step. Primary Track 3 is supported by RSS discovery and checkpoints/reminders. Amina's biography and drop-off problem are assumptions rather than research findings. Sample opportunities, console reminders and a local demo keep the proof of concept within its stated scope.

## Development process

The owner supplied the problem framing, learner assumptions, pathways and boundaries. Claude supported planning and review notes; Codex contributed implementation, tests, documentation and debugging. Scoped requests, branch-specific chats, diffs and approval before publication helped make changes reviewable. The fuller owner disclosure is in [AI-usage.md](AI-usage.md).

## What the evidence supports

The recorded 2026-10-12 validation includes 117 backend tests, 16 database-guard tests plus one skip, 14 robustness tests, lint, a 106.2 KB production build and 16 Playwright tests with exit code 0. These results cover checked software behavior. They do not demonstrate learning outcomes, measured retention, production readiness or a complete accessibility audit. A seeded-Amina browser rehearsal remains distinct from the existing bilingual onboarding test.

## Mistakes and practical lessons

Database fallback and Windows temporary-file cleanup exposed risks in otherwise ordinary validation commands. Explicit OS-temp database URLs, printed configuration and fail-fast handling became essential. A later interrupted command still lacked a validated URL; possible repository-database access is unverified. Test success must be reported alongside that limitation.

Documentation also drifted from implementation: earlier pathway names and an active daily dispatch proposal remained in the specification after the app and schedule changed. Reconciling the spec and demonstration script prevents a video from presenting historical intentions as current behavior.

## Next steps

Validate the problem and persona with real learners, assess recommendation usefulness and review language and accessibility with appropriate users. Keep production SMS, accounts, live vacancies and deployment outside this submission. The next experiment should test whether learners understand the checkpoint result and find the suggested next step useful.

## Submission context

The owner confirmed the idea origin and personal lesson on 2026-10-12. The inspected submission form requests a project video and GitHub repository URL; it shows no separate reflection field. This document accompanies the repository and does not replace any additional requirements that may be supplied later.
