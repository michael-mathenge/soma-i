# AI usage

I used AI throughout the development of SOMA.i. I chose the problem, the assumed learner persona, the pathways, and the project boundaries. Claude helped me structure plans, prompts, and review notes. Codex assisted with implementation, tests, documentation, debugging, and GitHub pull requests.

Codex contributed code across the Django backend and React frontend, including RSS ingestion, learner progress, checkpoints, sample opportunities, and reminder workflows. It also helped investigate Windows Playwright issues, improve temporary-database safeguards, and reconcile documentation conflicts.

My workflow used scoped requests, separate chats for branches, diff reviews, automated checks, and explicit approval before commits and publishing changes. I decided which findings to address, which limitations to accept, and when to merge.

AI assistance also introduced mistakes. Database safety became a particular concern after probes could fall back to a repository database. We added explicit temporary-database requirements and automated guards. A later interrupted validation command still lacked a validated database URL; its possible repository-database access remains unverified and is documented.

Recorded checks include 117 backend tests, 16 database-guard tests with one skip, 14 robustness tests, lint, a production build, and 16 Playwright tests. These results support the scenarios checked; they do not establish production readiness, accessibility compliance, or effectiveness with real learners.

SOMA.i contains substantial AI-assisted code. Amina is an assumed demo persona, opportunities are samples, and learner research and measured impact remain outstanding. I take responsibility for the submitted project and for describing its evidence and limitations honestly.

## Supporting evidence

Recorded commands and test outputs are in [PLANS.md](PLANS.md). The owner’s workflow account and artifact references remain in [README.md](../README.md).
