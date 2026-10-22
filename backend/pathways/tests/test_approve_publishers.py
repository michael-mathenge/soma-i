"""The publisher approval command must be safe to run against real evidence."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db

TODAY = date(2026, 10, 21)
EXPIRES = TODAY + timedelta(days=60)


def write(tmp_path, name, document):
    path = Path(tmp_path) / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def approval(**overrides):
    entry = {
        "key": "one",
        "domains": ["publisher.example.test"],
        "reviewed_by": "Fixture reviewer",
        "reviewed_on": TODAY.isoformat(),
        "expires_on": EXPIRES.isoformat(),
        "evidence_url": "https://publisher.example.test/policy",
        "independence_confirmed": True,
    }
    entry.update(overrides)
    return entry


def test_command_requires_a_reviewed_publishers_file(tmp_path):
    with pytest.raises(CommandError, match="not found"):
        call_command("approve_publishers", str(Path(tmp_path) / "missing.json"))


def test_command_refuses_a_publisher_without_a_review(tmp_path):
    entry = approval()
    del entry["reviewed_by"]
    path = write(tmp_path, "publishers.json", {"publishers": [entry]})

    with pytest.raises(CommandError, match="is missing"):
        call_command(
            "approve_publishers", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_a_publisher_that_is_not_independent(tmp_path):
    path = write(
        tmp_path,
        "publishers.json",
        {"publishers": [approval(independence_confirmed=False)]},
    )

    with pytest.raises(CommandError, match="must confirm that it is independent"):
        call_command("approve_publishers", path)


def test_command_refuses_an_expired_publisher_review(tmp_path):
    path = write(
        tmp_path,
        "publishers.json",
        {
            "publishers": [
                approval(
                    reviewed_on=(TODAY - timedelta(days=30)).isoformat(),
                    expires_on=(TODAY - timedelta(days=1)).isoformat(),
                )
            ]
        },
    )

    with pytest.raises(CommandError, match="review is not current"):
        call_command(
            "approve_publishers", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_a_review_longer_than_the_window(tmp_path):
    path = write(
        tmp_path,
        "publishers.json",
        {
            "publishers": [
                approval(
                    reviewed_on=(TODAY - timedelta(days=10)).isoformat(),
                    expires_on=(TODAY + timedelta(days=120)).isoformat(),
                )
            ]
        },
    )

    with pytest.raises(CommandError, match="longer than"):
        call_command(
            "approve_publishers", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_two_publishers_on_the_same_domain(tmp_path):
    path = write(
        tmp_path,
        "publishers.json",
        {
            "publishers": [
                approval(key="one", domains=["publisher.example.test"]),
                approval(key="two", domains=["other.publisher.example.test"]),
            ]
        },
    )

    with pytest.raises(CommandError, match="share a domain"):
        call_command(
            "approve_publishers", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_refuses_an_invalid_domain(tmp_path):
    path = write(
        tmp_path,
        "publishers.json",
        {"publishers": [approval(domains=["https://publisher.example.test"])]},
    )

    with pytest.raises(CommandError, match="invalid domain"):
        call_command(
            "approve_publishers", path, "--output", str(Path(tmp_path) / "out.json")
        )


def test_command_dry_run_does_not_change_the_rules_file(tmp_path):
    path = write(tmp_path, "publishers.json", {"publishers": [approval()]})
    rules_path = Path(__file__).resolve().parents[1] / "discovery_rules.json"
    before = rules_path.read_text(encoding="utf-8")

    call_command(
        "approve_publishers",
        path,
        "--dry-run",
        "--output",
        str(Path(tmp_path) / "out.json"),
    )

    assert rules_path.read_text(encoding="utf-8") == before
    assert not (Path(tmp_path) / "out.json").exists()
