"""The review commands must be safe to run against real evidence."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from content.models import Item, ResourceReview, Source

pytestmark = pytest.mark.django_db

TODAY = date(2026, 10, 21)
EXPIRES = TODAY + timedelta(days=60)


@pytest.fixture
def source():
    # The source uses a registered feed endpoint so that the feed registry
    # lookup in the review command has something to find.
    return Source.objects.create(
        name="Fixture publisher",
        url="https://realpython.com/atom.xml",
        attribution="Fixture author and publisher",
        rights="not stated",
        credibility_note="Offline test data; no publisher approval.",
    )


@pytest.fixture
def item(source):
    return Item.objects.create(
        source=source,
        title="Fixture lesson",
        url="https://realpython.com/lesson",
        match_text="Internal matching text.",
        published_at=datetime(2026, 9, 1, tzinfo=UTC),
        date_source="published",
        language="en",
        pathway_keys=["Data Analyst"],
    )


@pytest.fixture
def feed_permission(monkeypatch):
    """Give the fixture feed verified permission evidence."""
    from content import matching

    registry = matching.load_config()
    for feed in registry["feeds"]:
        if feed["url"] == "https://realpython.com/atom.xml":
            feed["permissions"] = {
                "reviewed_by": "Fixture reviewer",
                "scope": "Fixture scope",
                "reviewed_on": TODAY.isoformat(),
                "expires_on": EXPIRES.isoformat(),
                "evidence_url": "https://realpython.com/policy",
                "allowed_urls": ["https://realpython.com/atom.xml"],
                "feed_access": True,
                "metadata_reuse": True,
                "excerpt_reuse": False,
            }
            feed["publisher_key"] = "one"
    monkeypatch.setattr(matching, "load_config", lambda: registry)
    return registry


@pytest.fixture
def rules(monkeypatch):
    """Record a single current and independent publisher."""
    from pathways import discovery

    loaded = discovery.load_rules()
    loaded["publishers"] = {
        "one": {
            "domains": ["realpython.com"],
            "reviewed_by": "Fixture reviewer",
            "reviewed_on": TODAY.isoformat(),
            "expires_on": EXPIRES.isoformat(),
            "evidence_url": "https://realpython.com/policy",
            "independence_confirmed": True,
        }
    }
    monkeypatch.setattr(discovery, "load_rules", lambda: loaded)
    return loaded


def write(tmp_path, name, document):
    path = Path(tmp_path) / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def approval(**overrides):
    entry = {
        "url": "https://realpython.com/lesson",
        "publisher_key": "one",
        "author": "Fixture author",
        "reviewed_by": "Fixture reviewer",
        "reviewed_on": TODAY.isoformat(),
        "expires_on": EXPIRES.isoformat(),
        "evidence_url": "https://realpython.com/policy",
        "free_access": True,
        "english_confirmed": True,
    }
    entry.update(overrides)
    return entry


def test_review_command_requires_a_reviewed_items_file(tmp_path):
    with pytest.raises(CommandError, match="not found"):
        call_command("review_resources", str(Path(tmp_path) / "missing.json"))


def test_review_command_refuses_an_item_that_was_not_ingested(tmp_path):
    path = write(
        tmp_path, "reviews.json", {"items": [approval(url="https://nowhere.test/x")]}
    )

    with pytest.raises(CommandError, match="has not been ingested"):
        call_command("review_resources", path)


def test_review_command_refuses_a_feed_without_permission_evidence(tmp_path, item):
    path = write(tmp_path, "reviews.json", {"items": [approval()]})

    with pytest.raises(CommandError, match="without verified permission"):
        call_command("review_resources", path)


def test_review_command_refuses_an_unreviewed_publisher(
    tmp_path, item, feed_permission, monkeypatch
):
    from pathways import discovery

    monkeypatch.setattr(discovery, "load_rules", lambda: {"publishers": {}})
    path = write(tmp_path, "reviews.json", {"items": [approval()]})

    with pytest.raises(CommandError, match="not recorded"):
        call_command("review_resources", path)


def test_review_command_refuses_an_expired_review(
    tmp_path, item, feed_permission, rules
):
    path = write(
        tmp_path,
        "reviews.json",
        {
            "items": [
                approval(
                    reviewed_on=(TODAY - timedelta(days=30)).isoformat(),
                    expires_on=(TODAY - timedelta(days=1)).isoformat(),
                )
            ]
        },
    )

    with pytest.raises(CommandError, match="not current"):
        call_command("review_resources", path)


def test_review_command_refuses_a_review_longer_than_the_window(
    tmp_path, item, feed_permission, rules
):
    path = write(
        tmp_path,
        "reviews.json",
        {
            "items": [
                approval(
                    reviewed_on=(TODAY - timedelta(days=10)).isoformat(),
                    expires_on=(TODAY + timedelta(days=120)).isoformat(),
                )
            ]
        },
    )

    with pytest.raises(CommandError, match="longer than"):
        call_command("review_resources", path)


def test_review_command_refuses_an_evergreen_item_without_a_reason(
    tmp_path, item, feed_permission, rules
):
    path = write(tmp_path, "reviews.json", {"items": [approval(evergreen=True)]})

    with pytest.raises(CommandError, match="must give a reason"):
        call_command("review_resources", path)


def test_review_command_writes_nothing_when_any_entry_is_invalid(
    tmp_path, item, feed_permission, rules
):
    path = write(
        tmp_path,
        "reviews.json",
        {"items": [approval(), approval(url="https://nowhere.test/x")]},
    )

    with pytest.raises(CommandError):
        call_command("review_resources", path)
    assert ResourceReview.objects.count() == 0


def test_review_command_records_a_valid_review(tmp_path, item, feed_permission, rules):
    path = write(tmp_path, "reviews.json", {"items": [approval()]})

    call_command("review_resources", path)

    review = ResourceReview.objects.get(item=item)
    assert review.publisher_key == "one"
    assert review.reviewed_by == "Fixture reviewer"
    assert review.author == "Fixture author"
    assert review.free_access is True
    assert review.english_confirmed is True
    assert review.evergreen is False


def test_review_command_dry_run_writes_nothing(tmp_path, item, feed_permission, rules):
    path = write(tmp_path, "reviews.json", {"items": [approval()]})

    call_command("review_resources", path, "--dry-run")

    assert ResourceReview.objects.count() == 0
