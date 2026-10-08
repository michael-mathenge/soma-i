"""Config-driven topic matching, exclusions, and lightweight ranking."""

import json
import re
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = _TextExtractor()
    parser.feed(unescape(value or ""))
    return " ".join(" ".join(parser.parts).split())


@lru_cache(maxsize=1)
def load_config():
    path = Path(__file__).with_name("feeds.json")
    return json.loads(path.read_text(encoding="utf-8"))


def source_for_url(url, config=None):
    registry = (config or load_config())["feeds"]
    return next((feed for feed in registry if feed["url"] == url), None)


def matching_text(title, summary, source_type="publisher", config=None):
    config = config or load_config()
    title_text = plain_text(title)
    if source_type == "community":
        return title_text
    excerpt = plain_text(summary)[: config["defaults"]["summary_match_characters"]]
    return f"{title_text} {excerpt}".strip()


def _contains(term, text):
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I))


def matches_terms(text, terms):
    return any(_contains(term, text) for term in terms)


def topic_matches(pathway, title, summary="", source_type="publisher", config=None):
    config = config or load_config()
    pathway_config = config["pathways"].get(pathway)
    if not pathway_config:
        return False
    text = matching_text(title, summary, source_type, config)
    terms = pathway_config["keywords"]
    conditional = pathway_config.get("conditional_keywords", {})
    for term in terms:
        if not _contains(term, text):
            continue
        rule = conditional.get(term)
        if rule and not matches_terms(text, rule["requires_any"]):
            continue
        return True
    return False


def exclusion_reason(title, source_type="publisher", config=None):
    config = config or load_config()
    text = plain_text(title)
    patterns = list(config["exclusions"].get("all", []))
    if source_type == "community":
        patterns.extend(config["exclusions"].get("community", []))
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            return pattern
    return ""


def beginner_score(title, summary="", source_type="publisher", config=None):
    config = config or load_config()
    text = matching_text(title, summary, source_type, config)
    signals = config["ranking"]["beginner_score"]
    strong = sum(_contains(term, text) for term in signals["strong_signals"])
    medium = sum(_contains(term, text) for term in signals["medium_signals"])
    negative = sum(_contains(term, text) for term in signals["negative_signals"])
    return (
        strong * signals["strong_weight"]
        + medium * signals["medium_weight"]
        + negative * signals["negative_weight"]
    )


def ranking_score(title, summary="", source_type="publisher", config=None):
    config = config or load_config()
    score = beginner_score(title, summary, source_type, config)
    if source_type == "community":
        score += config["ranking"]["community_adjustment"]
    return score


def ranking_key(item, source_type="publisher", config=None):
    """Sort higher scores first; only parsed publication dates break score ties."""
    date_source = getattr(item, "date_source", "published")
    published_at = getattr(item, "published_at", None)
    has_published_date = date_source in {"published", "updated"} and published_at
    if has_published_date:
        timestamp = published_at.timestamp()
    else:
        timestamp = 0
    return (
        -ranking_score(item.title, item.summary, source_type, config),
        -int(bool(has_published_date)),
        -timestamp,
    )
