import logging
import re
import unicodedata
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from content.matching import exclusion_reason, load_config, plain_text, topic_matches
from content.models import Item, Skill
from content.skill_keywords import SKILL_KEYWORDS

SUMMARY_MAX_CHARS = 300
logger = logging.getLogger(__name__)


def safe_http_link(value):
    """Return a trimmed absolute HTTP(S) URL, or None for an unsafe link."""
    link = str(value or "").strip()
    if not link or any(
        char.isspace() or unicodedata.category(char) in {"Cc", "Cf"} for char in link
    ):
        return None
    try:
        parsed = urlsplit(link)
        hostname = parsed.hostname
        parsed.port  # Validate malformed or out-of-range ports.
    except ValueError:
        return None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or "@" in parsed.netloc
    ):
        return None
    return link


def normalize_link(value):
    parsed = urlsplit((value or "").strip())
    original_scheme = parsed.scheme.lower()
    scheme = original_scheme
    if scheme == "http":
        scheme = "https"
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port and not (
        (original_scheme == "http" and port == 80)
        or (original_scheme == "https" and port == 443)
    ):
        host = f"{host}:{parsed.port}"
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ],
        doseq=True,
    )
    return urlunsplit((scheme, host, path, query, ""))


def entry_date(entry, fetched_at):
    """Return the preferred entry date and the field that supplied it."""
    for field, source in (
        ("published_parsed", "published"),
        ("updated_parsed", "updated"),
    ):
        parsed = entry.get(field)
        if parsed:
            value = datetime(*parsed[:6], tzinfo=UTC)
            return (
                timezone.make_aware(value) if timezone.is_naive(value) else value
            ), source

    fixture_source = entry.get("date_source")
    if fixture_source == "fetched":
        return fetched_at, "fetched"

    fixture_date = entry.get("date")
    if fixture_date:
        try:
            value = datetime.fromisoformat(str(fixture_date).replace("Z", "+00:00"))
            if timezone.is_naive(value):
                value = timezone.make_aware(value, UTC)
            source = (
                fixture_source
                if fixture_source in {"published", "updated"}
                else "published"
            )
            return value, source
        except (TypeError, ValueError, OverflowError):
            try:
                value = parsedate_to_datetime(fixture_date)
                if timezone.is_naive(value):
                    value = timezone.make_aware(value, UTC)
                source = (
                    fixture_source
                    if fixture_source in {"published", "updated"}
                    else "published"
                )
                return value, source
            except (TypeError, ValueError, OverflowError):
                pass

    for field, source in (("published", "published"), ("updated", "updated")):
        raw = entry.get(field)
        if not raw:
            continue
        try:
            value = parsedate_to_datetime(raw)
            if timezone.is_naive(value):
                value = timezone.make_aware(value, UTC)
            return value, source
        except (TypeError, ValueError, OverflowError):
            try:
                value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if timezone.is_naive(value):
                    value = timezone.make_aware(value, UTC)
                return value, source
            except (TypeError, ValueError, OverflowError):
                continue
    return fetched_at, "fetched"


def _content_text(entry):
    content = entry.get("content") or []
    values = [plain_text(part.get("value", "")) for part in content]
    values = [value for value in values if value]
    if values:
        return max(values, key=len)
    return ""


def word_count_for_entry(entry):
    content_text = _content_text(entry)
    if not content_text:
        return None
    return len(re.findall(r"\b[\w’'-]+\b", content_text, flags=re.UNICODE))


def clean_summary(value):
    return plain_text(value)[:SUMMARY_MAX_CHARS]


def pathway_matches(feed_config, title, summary, config=None):
    config = config or load_config()
    if exclusion_reason(title, feed_config["source_type"], config):
        return []
    return [
        pathway
        for pathway in feed_config["pathways"]
        if topic_matches(
            pathway,
            title,
            summary,
            feed_config["source_type"],
            config,
        )
    ]


def items_for_pathway(pathway_key):
    """Filter pathway key lists in Python for SQLite-compatible queries."""
    return [
        item
        for item in Item.objects.all().order_by("pk")
        if pathway_key in item.pathway_keys
    ]


def staleness_for(source, reference_date, stale_after_days):
    """Compute source freshness without consulting the system clock."""
    if isinstance(reference_date, datetime):
        reference_date = reference_date.date()
    if source.latest_item_at is None:
        return {"stale": True, "reason": "no dates", "age_days": None}
    latest_date = source.latest_item_at.date()
    age_days = (reference_date - latest_date).days
    if age_days > stale_after_days:
        return {"stale": True, "reason": "age", "age_days": age_days}
    return {"stale": False, "reason": "", "age_days": age_days}


def feed_staleness(source, feed_config, reference_date, config=None):
    config = config or load_config()
    threshold = feed_config.get(
        "stale_after_days", config["defaults"]["stale_after_days"]
    )
    return staleness_for(source, reference_date, threshold)


def _matched_skills(title, summary):
    text = f"{title} {summary}".lower()
    matched = []
    for name, words in SKILL_KEYWORDS.items():
        if any(
            re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text) for word in words
        ):
            slug = slugify(name)
            skill, _ = Skill.objects.get_or_create(slug=slug, defaults={"name": name})
            matched.append(skill)
    return matched


@transaction.atomic
def ingest_entries(source, feed_config, entries, fetched_at, config=None):
    """Store matching entries and merge duplicates without replacing attribution."""
    config = config or load_config()
    registry_rank = {feed["url"]: index for index, feed in enumerate(config["feeds"])}
    created = 0
    duplicates_merged = 0
    dates = {"published": 0, "updated": 0, "fetched": 0}
    latest_item_at = None
    pathway_counts = {pathway: 0 for pathway in feed_config["pathways"]}
    duplicate_pathway_counts = {pathway: 0 for pathway in feed_config["pathways"]}
    rejected_unsafe_link = 0

    for entry in entries:
        title = plain_text(entry.get("title", "")).strip()[:300]
        original_link = safe_http_link(entry.get("link", ""))
        if original_link is None:
            rejected_unsafe_link += 1
            logger.warning(
                "%s: rejected item with unsafe link",
                feed_config.get("name") or source.name,
            )
            continue
        normalized_link = normalize_link(original_link)
        summary = clean_summary(
            entry.get("summary", entry.get("description", entry.get("excerpt", "")))
        )
        if not title or not original_link or not normalized_link:
            continue

        published_at, date_source = entry_date(entry, fetched_at)
        if date_source in {"published", "updated"}:
            latest_item_at = (
                max(latest_item_at, published_at) if latest_item_at else published_at
            )
        pathway_keys = pathway_matches(feed_config, title, summary, config)
        if not pathway_keys:
            continue

        dates[date_source] += 1

        guid = str(entry.get("id", entry.get("guid", ""))).strip()
        item = None
        matched_same_feed = False
        if guid:
            item = Item.objects.filter(source=source, guid=guid).order_by("pk").first()
            matched_same_feed = item is not None
        if item is None:
            item = (
                Item.objects.filter(normalized_link=normalized_link)
                .order_by("pk")
                .first()
            )
            matched_same_feed = item is not None and item.source_id == source.pk
        if item is None:
            item = Item.objects.filter(url=original_link).order_by("pk").first()
            matched_same_feed = item is not None and item.source_id == source.pk

        skills = _matched_skills(title, summary)
        if item is not None:
            duplicates_merged += 1
            item.pathway_keys = list(dict.fromkeys(item.pathway_keys + pathway_keys))
            update_fields = ["pathway_keys"]
            if matched_same_feed:
                item.title = title
                item.summary = summary
                item.published_at = published_at
                item.fetched_at = fetched_at
                item.date_source = date_source
                item.word_count = word_count_for_entry(entry)
                update_fields.extend(
                    [
                        "title",
                        "summary",
                        "published_at",
                        "fetched_at",
                        "date_source",
                        "word_count",
                    ]
                )
            if not item.guid and guid:
                item.guid = guid
                update_fields.append("guid")
            if not item.normalized_link:
                item.normalized_link = normalized_link
                update_fields.append("normalized_link")
            current_rank = registry_rank.get(source.url)
            existing_rank = registry_rank.get(item.source.url)
            if existing_rank is None or (
                current_rank is not None and current_rank < existing_rank
            ):
                item.source = source
                item.url = original_link
                item.normalized_link = normalized_link
                update_fields.extend(["source", "url", "normalized_link"])
            item.save(update_fields=update_fields)
            item.skills.add(*skills)
            for pathway in pathway_keys:
                duplicate_pathway_counts[pathway] += 1
        else:
            item = Item.objects.create(
                title=title,
                url=original_link,
                normalized_link=normalized_link,
                guid=guid,
                summary=summary,
                published_at=published_at,
                fetched_at=fetched_at,
                date_source=date_source,
                word_count=word_count_for_entry(entry),
                pathway_keys=pathway_keys,
                source=source,
                language=source.language,
                estimated_minutes=10,
                is_low_data=True,
            )
            item.skills.set(skills)
            created += 1
        for pathway in pathway_keys:
            pathway_counts[pathway] += 1

    return {
        "created": created,
        "duplicates_merged": duplicates_merged,
        "rejected_unsafe_link": rejected_unsafe_link,
        "date_counts": dates,
        "latest_item_at": latest_item_at,
        "pathway_counts": pathway_counts,
        "duplicate_pathway_counts": duplicate_pathway_counts,
    }
