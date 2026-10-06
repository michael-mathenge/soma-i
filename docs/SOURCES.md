# RSS sources

Verified by a live `feedparser` ingestion on 2026-10-02. Each endpoint returned entries and created the counts shown below. The management command reports fetch/parse failures per source and continues with remaining feeds.

| Source | Feed URL | Why credible | Verification |
|---|---|---|---|
| MIT News Research | https://news.mit.edu/rss/research | Official MIT News research feed; useful for data, computing, and research literacy. MIT publishes a directory of topic and school feeds. | 2026-10-02 — 50 entries parsed and ingested. |
| freeCodeCamp News | https://www.freecodecamp.org/news/rss/ | Educational publication associated with freeCodeCamp's active learning platform; tutorials cover programming and career skills. | 2026-10-02 — 10 entries parsed and ingested. |
| MDN Blog | https://developer.mozilla.org/en-US/blog/rss.xml | Mozilla Developer Network publishes web development guidance and tutorials and links to this RSS feed from its blog. | 2026-10-02 — 71 entries parsed and ingested. |

The app stores each source URL and a credibility note, and retains source and publication date on every ingested item. Articles remain hosted by their publishers and are linked rather than copied wholesale.
