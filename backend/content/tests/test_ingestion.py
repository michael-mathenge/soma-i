from pathlib import Path

import feedparser
import pytest

from content.ingestion import ingest_entries
from content.models import Source

pytestmark = pytest.mark.django_db


def test_fixture_ingestion_deduplicates_tags_and_keeps_traceability():
    fixture = Path(__file__).parent / "fixtures" / "feed.xml"
    parsed = feedparser.parse(fixture.read_bytes())
    source = Source.objects.create(
        name="Fixture source",
        url="https://example.test/feed.xml",
        credibility_note="Test fixture",
    )

    assert ingest_entries(source, parsed.entries) == 2
    assert ingest_entries(source, parsed.entries) == 0
    items = list(source.items.order_by("title"))
    assert len(items) == 2
    assert all(item.source_id == source.pk and item.published_at for item in items)
    sql = next(item for item in items if "SQL" in item.title)
    assert "SQL" in list(sql.skills.values_list("name", flat=True))
    assert "Statistics" in list(sql.skills.values_list("name", flat=True))
    html = next(item for item in items if "HTML" in item.title)
    assert "HTML" in list(html.skills.values_list("name", flat=True))
