import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from content.ingestion import normalize_link
from content.models import Item, Skill, Source
from learners.models import LearnerProfile
from pathways.constants import CANONICAL_PATHWAYS
from pathways.logic import progress_for, recommendations
from pathways.management.commands.seed_demo import DATA_ANALYST_DEMO_KEYS
from pathways.models import CheckpointRecord, Pathway, PathwaySkill

pytestmark = pytest.mark.django_db


def test_progress_percent_and_remaining_skills():
    pathway = Pathway.objects.create(
        title="Test", description="Test", target_outcome="Analyst"
    )
    skills = [
        Skill.objects.create(name=name, slug=name.lower()) for name in ("SQL", "Sheets")
    ]
    steps = [
        PathwaySkill.objects.create(pathway=pathway, skill=skill, order=i)
        for i, skill in enumerate(skills, 1)
    ]
    from pathways.models import Checkpoint

    checkpoints = [
        Checkpoint.objects.create(
            pathway_skill=step,
            title=skill.name,
            criteria="Practice",
            unlocks_text="Next",
        )
        for step, skill in zip(steps, skills)
    ]
    learner = LearnerProfile.objects.create(chosen_pathway=pathway)
    CheckpointRecord.objects.create(
        learner=learner, checkpoint=checkpoints[0], status="done", self_attested=True
    )

    progress = progress_for(learner)
    assert progress["percent"] == 50
    assert [skill.name for skill in progress["done"]] == ["SQL"]
    assert [skill.name for skill in progress["remaining"]] == ["Sheets"]
    assert progress["next_checkpoint"] == checkpoints[1]


def test_recommendations_prefer_low_data_for_the_requested_skill():
    skill = Skill.objects.create(name="SQL", slug="sql")
    source = Source.objects.create(
        name="Test", url="https://example.test/feed", credibility_note="fixture"
    )
    for title, low_data in (("Online video", False), ("Short text guide", True)):
        item = Item.objects.create(
            title=title,
            url=f"https://example.test/{title.replace(' ', '-')}",
            published_at="2026-01-01T00:00:00Z",
            source=source,
            is_low_data=low_data,
        )
        item.skills.add(skill)

    assert [item.title for item in recommendations(skill)] == [
        "Short text guide",
        "Online video",
    ]


def test_fixture_recommendations_keep_low_data_ahead_of_stronger_beginner_score():
    skill = Skill.objects.create(name="Python", slug="python")
    source = Source.objects.create(
        name="freeCodeCamp Python",
        url="https://www.freecodecamp.org/news/tag/python/rss/",
        credibility_note="Fixture feed",
    )
    low_data_item = Item.objects.create(
        title="Python reference material",
        url="https://example.test/python-reference",
        published_at="2026-01-01T00:00:00Z",
        source=source,
        is_low_data=True,
    )
    low_data_item.skills.add(skill)
    stronger_beginner_item = Item.objects.create(
        title="Python for beginners: step by step fundamentals",
        url="https://example.test/python-beginners",
        published_at="2026-01-02T00:00:00Z",
        source=source,
        is_low_data=False,
    )
    stronger_beginner_item.skills.add(skill)

    assert [item.title for item in recommendations(skill)] == [
        "Python reference material",
        "Python for beginners: step by step fundamentals",
    ]


def test_dump_seed_picks_returns_seed_owned_picks_without_urls():
    call_command("seed_demo", verbosity=0)
    output = StringIO()

    call_command("dump_seed_picks", stdout=output)

    picks = json.loads(output.getvalue())
    analyst_spreadsheets = picks["Data Analyst"]["Spreadsheets"]
    assert any(
        item["title"] == "Spreadsheet skills for clear data (demo)"
        for item in analyst_spreadsheets
    )
    assert all(
        item["title"].endswith(("(demo)", "(sample content)"))
        for pathway in picks.values()
        for skill_picks in pathway.values()
        for item in skill_picks
    )
    assert all(
        "url" not in item
        for pathway in picks.values()
        for skill_picks in pathway.values()
        for item in skill_picks
    )


def test_dump_seed_picks_prefetches_item_skills_without_n_plus_one_queries():
    call_command("seed_demo", verbosity=0)
    output = StringIO()

    with CaptureQueriesContext(connection) as queries:
        call_command("dump_seed_picks", stdout=output)

    assert json.loads(output.getvalue())
    assert len(queries) == 2


def test_data_analyst_declared_picks_are_nonempty_and_exclude_python_fixtures():
    call_command("seed_demo", verbosity=0)
    output = StringIO()
    call_command("dump_seed_picks", stdout=output)

    picks = json.loads(output.getvalue())["Data Analyst"]
    assert all(picks[skill] for skill in CANONICAL_PATHWAYS[0]["skills"])

    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "content"
        / "tests"
        / "fixtures"
        / "feeds"
        / "fcc_python.json"
    )
    python_links = {
        normalize_link(entry["link"])
        for entry in json.loads(fixture_path.read_text(encoding="utf-8"))
    }
    python_item_ids = set(
        Item.objects.filter(normalized_link__in=python_links).values_list(
            "pk", flat=True
        )
    )
    assert not any(
        item["id"] in python_item_ids
        for skill_picks in picks.values()
        for item in skill_picks
    )


def test_data_analyst_manual_demo_items_have_no_other_pathway_skills():
    call_command("seed_demo", verbosity=0)
    other_pathway_skills = {
        skill_name
        for pathway in CANONICAL_PATHWAYS[1:]
        for skill_name in pathway["skills"]
    }

    for url, title in DATA_ANALYST_DEMO_KEYS:
        item = Item.objects.get(url=url, title=title)
        assert not item.skills.filter(name__in=other_pathway_skills).exists()


def test_seed_demo_preserves_live_item_sharing_a_demo_url():
    source = Source.objects.create(
        name="Live research feed",
        url="https://news.mit.edu/rss/research",
        credibility_note="Live ingested feed",
    )
    sql = Skill.objects.get_or_create(slug="sql", defaults={"name": "SQL"})[0]
    item = Item.objects.create(
        title="Live MIT research article",
        url="https://news.mit.edu/rss/research",
        published_at="2026-01-01T00:00:00Z",
        is_low_data=False,
        source=source,
    )
    item.skills.add(sql)

    call_command("seed_demo", verbosity=0)

    item.refresh_from_db()
    assert item.title == "Live MIT research article"
    assert list(item.skills.values_list("name", flat=True)) == ["SQL"]


def test_seed_demo_handwritten_samples_share_one_source_and_distinct_links():
    from pathways.management.commands.seed_demo import SAMPLE_SOURCE_URL

    call_command("seed_demo", verbosity=0)

    samples = list(
        Item.objects.filter(title__endswith="(demo)", url__contains="#demo-")
        .select_related("source")
        .order_by("title")
    )
    assert len(samples) == 5
    assert len({item.url for item in samples}) == 5
    assert {item.normalized_link for item in samples} == {None}
    assert {item.source.name for item in samples} == {"SOMA.i sample content"}
    source = samples[0].source
    assert source.url == SAMPLE_SOURCE_URL
    assert source.attribution == "SOMA.i"
    assert source.rights == "not stated"
    assert source.level == "beginner"


def test_seed_demo_upgrade_repoints_all_legacy_rows_and_preserves_live_collision():
    from pathways.management.commands.seed_demo import (
        LEGACY_DEMO_URLS,
        SAMPLE_SOURCE_URL,
    )

    legacy_source = Source.objects.create(
        name="Legacy demo source",
        url="https://example.test/legacy-demo-source-upgrade",
        credibility_note="Legacy hand-written demo source.",
    )
    legacy_rows = []
    for title, legacy_url in LEGACY_DEMO_URLS.items():
        if title == "Organize a small dataset (demo)":
            continue
        legacy_rows.append(
            Item.objects.create(
                title=title,
                url=legacy_url,
                normalized_link=normalize_link(legacy_url),
                published_at="2020-01-01T00:00:00Z",
                source=legacy_source,
                is_low_data=True,
            )
        )
    sql, _ = Skill.objects.get_or_create(slug="sql", defaults={"name": "SQL"})
    live_item = Item.objects.create(
        title="Live MIT research article",
        url=LEGACY_DEMO_URLS["Organize a small dataset (demo)"],
        published_at="2020-01-01T00:00:00Z",
        source=legacy_source,
        is_low_data=False,
    )
    live_item.skills.add(sql)

    call_command("seed_demo", verbosity=0)

    expected_links = {
        "Spreadsheet skills for clear data (demo)": "https://github.com/michael-mathenge/soma-i#demo-spreadsheet-skills",
        "Practice spreadsheet formulas (demo)": "https://github.com/michael-mathenge/soma-i#demo-spreadsheet-formulas",
        "Organize a small dataset (demo)": "https://github.com/michael-mathenge/soma-i#demo-small-dataset",
        "CSS layout foundations (demo)": "https://github.com/michael-mathenge/soma-i#demo-css-layout",
        "JavaScript essentials (demo)": "https://github.com/michael-mathenge/soma-i#demo-javascript-essentials",
    }
    samples = [Item.objects.get(title=title) for title in expected_links]
    assert {item.url for item in samples} == set(expected_links.values())
    assert {item.normalized_link for item in samples} == {None}
    assert {item.source.url for item in samples} == {SAMPLE_SOURCE_URL}
    assert all(Item.objects.filter(pk=item.pk).exists() for item in legacy_rows)

    live_item.refresh_from_db()
    assert live_item.url == LEGACY_DEMO_URLS["Organize a small dataset (demo)"]
    assert live_item.title == "Live MIT research article"
    assert live_item.is_low_data is False
    assert list(live_item.skills.values_list("name", flat=True)) == ["SQL"]


def test_seed_demo_skips_legacy_row_when_sample_url_is_taken(capsys):
    from pathways.management.commands.seed_demo import LEGACY_DEMO_URLS

    legacy_title = "CSS layout foundations (demo)"
    legacy_url = LEGACY_DEMO_URLS[legacy_title]
    sample_url = "https://github.com/michael-mathenge/soma-i#demo-css-layout"
    legacy_source = Source.objects.create(
        name="Legacy demo source",
        url="https://example.test/legacy-demo-source-url-conflict",
        credibility_note="Legacy hand-written demo source.",
    )
    live_source = Source.objects.create(
        name="Live destination source",
        url="https://example.test/live-destination-source",
        credibility_note="Live ingested item.",
    )
    legacy_item = Item.objects.create(
        title=legacy_title,
        url=legacy_url,
        published_at="2020-01-01T00:00:00Z",
        source=legacy_source,
    )
    live_item = Item.objects.create(
        title="Live article at sample destination",
        url=sample_url,
        published_at="2026-01-01T00:00:00Z",
        source=live_source,
        is_low_data=False,
    )

    call_command("seed_demo", verbosity=0)

    legacy_item.refresh_from_db()
    live_item.refresh_from_db()
    assert (legacy_item.url, legacy_item.title) == (legacy_url, legacy_title)
    assert (live_item.url, live_item.title) == (
        sample_url,
        "Live article at sample destination",
    )
    assert live_item.source == live_source
    assert "Skipped 1 legacy demo row(s) due to destination URL conflicts." in (
        capsys.readouterr().out
    )


def test_seeded_functional_css_summary_keeps_200_character_fixture_excerpt():
    call_command("seed_demo", verbosity=0)
    item = Item.objects.get(
        url="https://www.freecodecamp.org/news/atomic-and-functional-css/"
    )

    print(f"Functional CSS stored summary length: {len(item.summary)}")
    assert len(item.summary) == 200
