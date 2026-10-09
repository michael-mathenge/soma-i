import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from content.models import Item, Skill, Source
from learners.models import LearnerProfile
from pathways.logic import progress_for, recommendations
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
