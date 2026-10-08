# RSS sources

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
