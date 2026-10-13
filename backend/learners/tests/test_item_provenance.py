from datetime import UTC, date, datetime

import pytest

from content.models import Item, Source
from learners.api import item_json

pytestmark = pytest.mark.django_db

REFERENCE_DATE = date(2026, 10, 13)
CONTENT_DATE = datetime(2026, 9, 1, 9, tzinfo=UTC)
FETCHED_AT = datetime(2026, 10, 12, 9, tzinfo=UTC)


def make_item(**overrides):
    source = Source.objects.create(
        name="Fixture publisher",
        url="https://publisher.example.test/feed.xml",
        attribution="Fixture author and publisher",
        rights="not stated",
        credibility_note="Offline test data; no publisher approval.",
    )
    values = {
        "title": "Fixture lesson",
        "url": "https://publisher.example.test/lesson",
        "summary": "Offline fixture excerpt.",
        "source": source,
        "published_at": CONTENT_DATE,
        "date_source": "published",
        "fetched_at": FETCHED_AT,
    }
    values.update(overrides)
    return Item.objects.create(**values)


@pytest.mark.parametrize(
    ("date_source", "expected"),
    [
        ("published", "2026-09-01"),
        ("updated", "2026-09-01"),
        ("fetched", None),
        (None, None),
    ],
)
def test_provenance_does_not_present_retrieval_or_legacy_dates_as_publication(
    date_source, expected
):
    item = make_item(date_source=date_source)
    payload = item_json(item, reference_date=REFERENCE_DATE)

    assert payload["content_date"] == expected
    assert payload["date_source"] == date_source
    assert payload["fetched_at"] == FETCHED_AT.isoformat()


def test_provenance_does_not_present_future_dates_as_verified_content_dates():
    item = make_item(published_at=datetime(2026, 10, 14, tzinfo=UTC))
    assert item_json(item, reference_date=REFERENCE_DATE)["content_date"] is None


@pytest.mark.parametrize(
    ("source_url", "expected"),
    [
        (
            "https://publisher.example.test/feed.xml",
            "https://publisher.example.test/feed.xml",
        ),
        ("javascript:alert(1)", ""),
        ("https://user:secret@publisher.example.test/feed.xml", ""),
        ("//publisher.example.test/feed.xml", ""),
    ],
)
def test_provenance_source_links_clear_unsafe_and_credential_bearing_urls(
    source_url, expected
):
    item = make_item()
    item.source.url = source_url
    payload = item_json(item, reference_date=REFERENCE_DATE)

    assert payload["source_url"] == expected
    assert payload["url"] == item.url
    assert payload["source_attribution"] == "Fixture author and publisher"


@pytest.mark.parametrize("reported_rights", ["not stated", "", "CC BY 4.0"])
def test_reported_rights_never_imply_verified_reuse(reported_rights):
    item = make_item()
    item.source.rights = reported_rights
    payload = item_json(item, reference_date=REFERENCE_DATE)

    assert payload["source_rights"] == reported_rights
    assert payload["source_reuse_verified"] is False
    item.refresh_from_db()
    assert item.summary == "Offline fixture excerpt."
