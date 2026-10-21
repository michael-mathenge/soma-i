"""The feed approval command must be safe to run against real evidence."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db

TODAY = date(2026, 10, 21)
EXPIRES = TODAY + timedelta(days=60)
FEED_URL = "https://www.freecodecamp.org/news/tag/sql/rss/"


def write(tmp_path, name, document):
    path = Path(tmp_path) / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def approval(**overrides):
    entry = {
        "key": "fcc_sql",
        "reviewed_by": "Fixture reviewer",
        "scope": "Fixture scope",
        "reviewed_on": TODAY.isoformat(),
        "expires_on": EXPIRES.isoformat(),
        "evidence_url": "https://www.freecodecamp.org/copyright/",
        "allowed_urls": [FEED_URL],
        "publisher_key": "one",
    }
    entry.update(overrides)
    return entry


def test_command_requires_a_reviewed_feeds_file(tmp_path):
    with pytest.raises(CommandError, match="not found"):
        call_command("approve_feeds", str(Path(tmp_path) / "missing.json"))


def test_command_refuses_an_approval_missing_a_field(tmp_path):
    entry = approval()
    del entry["scope"]
    path = write(tmp_path, "feeds.json", {"feeds": [entry]})

    with pytest.raises(CommandError, match="is missing"):
        call_command(
            "approve_feeds", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_an_approval_that_does_not_cover_the_endpoint(tmp_path):
    path = write(
        tmp_path,
        "feeds.json",
        {"feeds": [approval(allowed_urls=["https://www.freecodecamp.org/other/"])]},
    )

    with pytest.raises(CommandError, match="does not cover the registry endpoint"):
        call_command(
            "approve_feeds", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_a_feed_that_is_not_in_the_registry(tmp_path):
    path = write(tmp_path, "feeds.json", {"feeds": [approval(key="unknown")]})

    with pytest.raises(CommandError, match="not in the registry"):
        call_command(
            "approve_feeds", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_an_expired_approval(tmp_path):
    path = write(
        tmp_path,
        "feeds.json",
        {
            "feeds": [
                approval(
                    reviewed_on=(TODAY - timedelta(days=30)).isoformat(),
                    expires_on=(TODAY - timedelta(days=1)).isoformat(),
                )
            ]
        },
    )

    with pytest.raises(CommandError, match="is not current"):
        call_command(
            "approve_feeds", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_too_many_approved_endpoints(tmp_path):
    path = write(
        tmp_path,
        "feeds.json",
        {
            "feeds": [
                approval(
                    allowed_urls=[f"https://example.test/{index}" for index in range(7)]
                )
            ]
        },
    )

    with pytest.raises(CommandError, match="one to six exact endpoints"):
        call_command(
            "approve_feeds", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_records_an_approval_without_excerpt_reuse(tmp_path):
    path = write(tmp_path, "feeds.json", {"feeds": [approval()]})
    output = Path(tmp_path) / "out.json"

    call_command("approve_feeds", path, "--output", str(output))

    registry = json.loads(output.read_text(encoding="utf-8"))
    feed = next(entry for entry in registry["feeds"] if entry["key"] == "fcc_sql")
    assert feed["permissions"]["feed_access"] is True
    assert feed["permissions"]["metadata_reuse"] is True
    # Excerpt reuse is not granted unless the owner grants it.
    assert feed["permissions"]["excerpt_reuse"] is False
    assert feed["publisher_key"] == "one"


def test_command_records_excerpt_reuse_when_the_owner_grants_it(tmp_path):
    path = write(tmp_path, "feeds.json", {"feeds": [approval(excerpt_reuse=True)]})
    output = Path(tmp_path) / "out.json"

    call_command("approve_feeds", path, "--output", str(output))

    registry = json.loads(output.read_text(encoding="utf-8"))
    feed = next(entry for entry in registry["feeds"] if entry["key"] == "fcc_sql")
    assert feed["permissions"]["excerpt_reuse"] is True


def test_command_dry_run_does_not_change_the_registry(tmp_path):
    path = write(tmp_path, "feeds.json", {"feeds": [approval()]})
    registry_path = Path(__file__).resolve().parents[1] / "feeds.json"
    before = registry_path.read_text(encoding="utf-8")

    call_command(
        "approve_feeds", path, "--dry-run", "--output", str(Path(tmp_path) / "out.json")
    )

    assert registry_path.read_text(encoding="utf-8") == before
