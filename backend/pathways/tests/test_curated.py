"""The curated curriculum route must stay as strict as the automatic one."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from pathways.models import CuratedResource, Pathway

pytestmark = pytest.mark.django_db

TODAY = date(2026, 10, 21)
EXPIRES = TODAY + timedelta(days=60)


def link(**overrides):
    entry = {
        "title": "How the web works",
        "url": "https://developer.mozilla.org/en-US/docs/Learn_web_development",
        "publisher": "MDN Web Docs",
        "evidence_url": "https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines",
        "reviewed_by": "Owner",
        "reviewed_on": TODAY.isoformat(),
        "expires_on": EXPIRES.isoformat(),
        "rationale": "Explains the request and response cycle.",
    }
    entry.update(overrides)
    return entry


def steps():
    return {
        "Computer Basics": [
            link(),
            link(url="https://example.test/one", publisher="Example One"),
            link(url="https://example.test/two", publisher="Example Two"),
        ],
        "Internet Research": [
            link(url="https://example.test/three", publisher="Example One"),
            link(url="https://example.test/four", publisher="Example Two"),
            link(url="https://example.test/five", publisher="Example One"),
        ],
        "Online Safety": [
            link(url="https://example.test/six", publisher="Example One"),
            link(url="https://example.test/seven", publisher="Example Two"),
            link(url="https://example.test/eight", publisher="Example Two"),
        ],
    }


def write(tmp_path, document):
    path = Path(tmp_path) / "curated.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def test_publishing_creates_a_published_pathway_with_the_links(tmp_path):
    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})

    call_command("publish_curriculum", path)

    pathway = Pathway.objects.get(catalogue__slug="digital-foundations")
    assert pathway.status == "published"
    assert pathway.enrollment_open is True
    assert pathway.discovery_managed is False
    assert pathway.steps.count() == 3
    assert CuratedResource.objects.count() == 9
    first = CuratedResource.objects.order_by("pk").first()
    assert first.title == "How the web works"
    assert first.publisher == "MDN Web Docs"
    assert first.reviewed_by == "Owner"


def test_a_republish_with_the_same_links_is_not_a_new_revision(tmp_path):
    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})
    call_command("publish_curriculum", path)
    first = Pathway.objects.get(catalogue__slug="digital-foundations")

    call_command("publish_curriculum", path)

    assert Pathway.objects.filter(catalogue__slug="digital-foundations").count() == 1
    assert Pathway.objects.get(pk=first.pk).version == first.version


def test_changing_the_links_creates_a_new_revision_and_retires_the_old(tmp_path):
    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})
    call_command("publish_curriculum", path)
    first = Pathway.objects.get(catalogue__slug="digital-foundations")

    changed = steps()
    changed["Computer Basics"][0]["title"] = "A different title"
    call_command(
        "publish_curriculum",
        write(tmp_path, {"topics": {"digital-foundations": changed}}),
    )

    first.refresh_from_db()
    newest = Pathway.objects.get(
        catalogue__slug="digital-foundations", status="published"
    )
    assert first.status == "retired"
    assert first.enrollment_open is False
    assert newest.version == first.version + 1


def test_a_step_with_too_few_links_is_refused(tmp_path):
    thin = steps()
    thin["Computer Basics"] = thin["Computer Basics"][:2]
    path = write(tmp_path, {"topics": {"digital-foundations": thin}})

    with pytest.raises(CommandError, match="at least 3 links"):
        call_command("publish_curriculum", path)
    assert not Pathway.objects.exists()


def test_a_topic_from_one_publisher_is_refused(tmp_path):
    single = steps()
    for links in single.values():
        for index, entry in enumerate(links):
            entry["publisher"] = "Only Publisher"
            entry["url"] = f"https://only.test/link{index}"
            entry["evidence_url"] = "https://only.test/terms"
    path = write(tmp_path, {"topics": {"digital-foundations": single}})

    with pytest.raises(CommandError, match="independent publishers"):
        call_command("publish_curriculum", path)


def test_an_expired_review_is_refused(tmp_path):
    expired = steps()
    expired["Computer Basics"][0]["expires_on"] = (
        TODAY - timedelta(days=1)
    ).isoformat()
    path = write(tmp_path, {"topics": {"digital-foundations": expired}})

    with pytest.raises(CommandError, match="not current"):
        call_command("publish_curriculum", path)


def test_a_review_longer_than_the_window_is_refused(tmp_path):
    long_review = steps()
    long_review["Computer Basics"][0]["reviewed_on"] = (
        TODAY - timedelta(days=10)
    ).isoformat()
    long_review["Computer Basics"][0]["expires_on"] = (
        TODAY + timedelta(days=120)
    ).isoformat()
    path = write(tmp_path, {"topics": {"digital-foundations": long_review}})

    with pytest.raises(CommandError, match="longer than 90 days"):
        call_command("publish_curriculum", path)


def test_a_link_without_evidence_is_refused(tmp_path):
    missing = steps()
    del missing["Computer Basics"][0]["evidence_url"]
    path = write(tmp_path, {"topics": {"digital-foundations": missing}})

    with pytest.raises(CommandError, match="evidence_url"):
        call_command("publish_curriculum", path)


def test_a_link_with_an_unsafe_url_is_refused(tmp_path):
    unsafe = steps()
    unsafe["Computer Basics"][0]["url"] = "javascript:alert(1)"
    path = write(tmp_path, {"topics": {"digital-foundations": unsafe}})

    with pytest.raises(CommandError, match="invalid url"):
        call_command("publish_curriculum", path)


def test_a_topic_outside_the_review_rules_is_refused(tmp_path):
    path = write(tmp_path, {"topics": {"not-a-reviewed-topic": steps()}})

    with pytest.raises(CommandError, match="not in the review rules"):
        call_command("publish_curriculum", path)


def test_dry_run_publishes_nothing(tmp_path):
    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})

    call_command("publish_curriculum", path, "--dry-run")

    assert not Pathway.objects.exists()
    assert not CuratedResource.objects.exists()


def test_an_expired_link_is_not_served_to_a_learner(tmp_path):
    from pathways.curated import curated_links

    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})
    call_command("publish_curriculum", path)
    step = Pathway.objects.get(catalogue__slug="digital-foundations").steps.first()

    CuratedResource.objects.filter(pathway_skill=step).update(
        expires_on=TODAY - timedelta(days=1)
    )

    assert curated_links(step, today=TODAY) == []


def test_a_current_link_is_served_to_a_learner(tmp_path):
    from pathways.curated import curated_links

    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})
    call_command("publish_curriculum", path)
    step = Pathway.objects.get(catalogue__slug="digital-foundations").steps.first()

    links = curated_links(step, today=TODAY)

    assert len(links) == 3
    assert links[0].publisher == "MDN Web Docs"


def test_the_published_pathway_is_enrollable(tmp_path):
    from pathways.catalogue import enrollable_pathways

    path = write(tmp_path, {"topics": {"digital-foundations": steps()}})
    call_command("publish_curriculum", path)

    slugs = {pathway.catalogue.slug for pathway in enrollable_pathways()}
    assert "digital-foundations" in slugs
