import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from django.utils import timezone
from django.utils.text import slugify

from content.models import Item, Skill, Source
from content.skill_keywords import SKILL_KEYWORDS


def tag_item(item):
    text = f"{item.title} {item.summary}".lower()
    matched = []
    for name, words in SKILL_KEYWORDS.items():
        if any(
            re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text) for word in words
        ):
            slug = slugify(name)
            skill, _ = Skill.objects.get_or_create(slug=slug, defaults={"name": name})
            matched.append(skill)
    item.skills.set(matched)


def entry_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return timezone.make_aware(datetime(*parsed[:6]), UTC)
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, UTC)
            return dt
        except (TypeError, ValueError, OverflowError):
            pass
    return timezone.now()


def clean_summary(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()[:2000]


def ingest_entries(source: Source, entries):
    created = 0
    for entry in entries:
        url = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not url or not title:
            continue
        item, was_created = Item.objects.get_or_create(
            url=url,
            defaults={
                "title": title[:300],
                "summary": clean_summary(entry.get("summary", "")),
                "published_at": entry_date(entry),
                "source": source,
                "language": source.language,
                "estimated_minutes": 10,
                "is_low_data": True,
            },
        )
        if was_created:
            tag_item(item)
            created += 1
    return created
