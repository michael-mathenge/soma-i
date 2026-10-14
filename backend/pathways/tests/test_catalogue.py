from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from content.models import Item, Skill, Source
from learners.api import item_json
from learners.models import LearnerProfile
from pathways.catalogue import (
    create_revision,
    enrollable_pathways,
    publish_demo_revision,
)
from pathways.logic import progress_for
from pathways.management.commands.seed_demo import QUIZ
from pathways.models import (
    Catalogue,
    Checkpoint,
    CheckpointRecord,
    Pathway,
    PathwaySkill,
)

pytestmark = pytest.mark.django_db


def curriculum(prefix="Fixture"):
    return [
        dict(
            skill=f"{prefix} {index}",
            title=f"Practice {index}",
            criteria=f"Produce an original example for step {index}.",
            unlocks_text=f"Continue after step {index}.",
            quiz_json=deepcopy(QUIZ),
        )
        for index in range(1, 4)
    ]


def revision(catalogue=None, **kwargs):
    catalogue = catalogue or Catalogue.objects.create(slug="fixture-topic")
    values = dict(
        title="Fixture topic",
        description="Offline curriculum.",
        target_outcome="Practice a topic",
        steps=curriculum(),
        is_demo=True,
    )
    values.update(kwargs)
    return create_revision(catalogue, **values)


def session_client(learner):
    client = APIClient()
    session = client.session
    session["learner_id"] = learner.pk
    session.save()
    return client


def test_fourth_catalogue_topic_is_listed_and_enrollable_without_constants():
    call_command("seed_demo", verbosity=0)
    extra = publish_demo_revision(revision())
    client = APIClient()
    assert len(client.get("/api/pathways/").data) == 4
    assert (
        client.post("/api/me/", {"pathway_id": extra.pk}, format="json").status_code
        == 201
    )
    assert client.get("/api/dashboard/").data["remaining"] == [
        s["skill"] for s in curriculum()
    ]


def test_new_revision_preserves_active_progress_and_old_checkpoint_access():
    old = publish_demo_revision(revision())
    first = old.steps.first().checkpoint
    learner = LearnerProfile.objects.create(chosen_pathway=old)
    record = CheckpointRecord.objects.create(
        learner=learner, checkpoint=first, status="done"
    )
    client = session_client(learner)
    new = publish_demo_revision(revision(old.catalogue, steps=curriculum("Revised")))
    old.refresh_from_db()
    learner.refresh_from_db()
    assert old.status == "retired" and not old.enrollment_open
    assert learner.chosen_pathway_id == old.pk
    assert CheckpointRecord.objects.get(pk=record.pk).checkpoint_id == first.pk
    assert progress_for(learner)["percent"] == 33
    assert client.get("/api/dashboard/").data["pathway"]["id"] == old.pk
    assert client.get("/api/next/").data["unlocked_skill"] == "Fixture 1"
    assert (
        client.post(
            f"/api/checkpoints/{first.pk}/complete/",
            {
                "self_attested": True,
                "quiz_answers": [0, 0, 0],
            },
            format="json",
        ).status_code
        == 200
    )
    assert [p.pk for p in enrollable_pathways()] == [new.pk]
    assert (
        APIClient().post("/api/me/", {"pathway_id": old.pk}, format="json").status_code
        == 404
    )
    assert client.post("/api/pathway/restart/", {}, format="json").status_code == 200
    assert learner.chosen_pathway_id == old.pk
    assert not CheckpointRecord.objects.filter(learner=learner).exists()


@pytest.mark.parametrize("state", ["draft", "retired", "closed", "unregistered"])
def test_onboarding_and_switch_reject_unavailable_versions_without_profile_changes(
    state,
):
    active = publish_demo_revision(revision())
    unavailable = revision(active.catalogue)
    if state in {"retired", "closed"}:
        unavailable = publish_demo_revision(unavailable)
        unavailable.enrollment_open = False
        if state == "retired":
            unavailable.status = "retired"
        unavailable.save(update_fields=["status", "enrollment_open"])
    if state == "unregistered":
        unavailable = Pathway.objects.create(
            title="Legacy", description="Preserved", target_outcome="Legacy"
        )
    learner = LearnerProfile.objects.create(chosen_pathway=active)
    client = session_client(learner)
    before = LearnerProfile.objects.count()
    assert (
        APIClient()
        .post("/api/me/", {"pathway_id": unavailable.pk}, format="json")
        .status_code
        == 404
    )
    assert (
        client.post(
            "/api/pathway/switch/", {"pathway_id": unavailable.pk}, format="json"
        ).status_code
        == 404
    )
    learner.refresh_from_db()
    assert learner.chosen_pathway_id == active.pk
    assert LearnerProfile.objects.count() == before
    assert unavailable.pk not in [p["id"] for p in client.get("/api/pathways/").data]


def test_explicit_switch_uses_new_revision_and_keeps_previous_records():
    old = publish_demo_revision(revision())
    learner = LearnerProfile.objects.create(chosen_pathway=old)
    record = CheckpointRecord.objects.create(
        learner=learner, checkpoint=old.steps.first().checkpoint, status="done"
    )
    new = publish_demo_revision(revision(old.catalogue, steps=curriculum("Revised")))
    client = session_client(learner)
    assert (
        client.post(
            "/api/pathway/switch/", {"pathway_id": new.pk}, format="json"
        ).status_code
        == 200
    )
    learner.refresh_from_db()
    assert learner.chosen_pathway_id == new.pk
    assert progress_for(learner)["percent"] == 0
    assert CheckpointRecord.objects.filter(pk=record.pk).exists()
    assert (
        client.post(
            f"/api/checkpoints/{record.checkpoint_id}/skip/", {}, format="json"
        ).status_code
        == 404
    )


def test_seed_rerun_never_overwrites_revision_or_selects_an_unpublished_draft():
    call_command("seed_demo", verbosity=0)
    old = Pathway.objects.get(title="Data Analyst")
    snapshot = list(
        old.steps.values_list("pk", "skill_id", "order", "checkpoint__criteria")
    )
    revision(old.catalogue, title="New draft", steps=curriculum("Draft"))
    call_command("seed_demo", verbosity=0)
    old.refresh_from_db()
    assert (
        list(old.steps.values_list("pk", "skill_id", "order", "checkpoint__criteria"))
        == snapshot
    )
    assert (
        LearnerProfile.objects.get(display_name="Amina Demo").chosen_pathway_id
        == old.pk
    )
    assert old.catalogue.versions.count() == 2


@pytest.mark.parametrize("entity", ["pathway", "step", "checkpoint"])
@pytest.mark.parametrize("action", ["save", "delete"])
def test_published_curriculum_model_writes_are_rejected_even_with_stale_instances(
    entity, action
):
    draft = revision()
    step = draft.steps.first()
    checkpoint = step.checkpoint
    publish_demo_revision(draft)
    obj = dict(pathway=draft, step=step, checkpoint=checkpoint)[entity]
    if action == "save":
        if entity == "step":
            obj.order = 2
        else:
            obj.title = "Mutated"
    with pytest.raises(ValidationError):
        getattr(obj, action)()


@pytest.mark.parametrize(
    "mutation",
    [
        "too_few",
        "too_many",
        "duplicate",
        "blank",
        "bad_quiz",
        "bad_answer",
        "slug_collision",
    ],
)
def test_invalid_curriculum_rolls_back_all_revision_writes(mutation):
    steps = curriculum()
    if mutation == "too_few":
        steps = steps[:2]
    elif mutation == "too_many":
        steps = steps * 3
    elif mutation == "duplicate":
        steps[1]["skill"] = steps[0]["skill"]
    elif mutation == "blank":
        steps[1]["criteria"] = " "
    elif mutation == "bad_quiz":
        steps[1]["quiz_json"] = []
    elif mutation == "bad_answer":
        steps[1]["quiz_json"][0]["answer"] = True
    elif mutation == "slug_collision":
        Skill.objects.create(name="Different name", slug="fixture-2")
    catalogue = Catalogue.objects.create(slug="rollback")
    count = Skill.objects.count()
    with pytest.raises(ValidationError):
        revision(catalogue, steps=steps)
    assert not catalogue.versions.exists()
    assert not PathwaySkill.objects.exists()
    assert not Checkpoint.objects.exists()
    assert Skill.objects.count() == count


def test_database_constraints_prevent_duplicate_versions_and_two_published_versions():
    first = publish_demo_revision(revision())
    with pytest.raises(IntegrityError), transaction.atomic():
        Pathway.objects.create(catalogue=first.catalogue, version=first.version)
    with pytest.raises(IntegrityError), transaction.atomic():
        Pathway.objects.create(catalogue=first.catalogue, version=2, status="published")
    with pytest.raises(IntegrityError), transaction.atomic():
        Pathway.objects.create(
            catalogue=first.catalogue, version=2, enrollment_open=True
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Pathway.objects.create(catalogue=first.catalogue, version=0)


def test_demo_publication_cannot_publish_live_drafts_or_retire_a_live_version():
    live = revision(is_demo=False)
    with pytest.raises(ValidationError):
        publish_demo_revision(live)
    # Simulate a future reviewed live publisher; no feeds or network are involved.
    live.status = "published"
    live.enrollment_open = True
    live.save()
    demo = revision(live.catalogue)
    with pytest.raises(ValidationError):
        publish_demo_revision(demo)
    live.refresh_from_db()
    assert live.status == "published" and live.enrollment_open
    assert demo.status == "draft"


def test_draft_revision_never_changes_current_catalogue_or_skill_labels():
    old = publish_demo_revision(revision())
    revision(old.catalogue, steps=curriculum("Draft"))
    source = Source.objects.create(name="Fixture", url="https://example.test/feed")
    item = Item.objects.create(
        title="Fixture",
        url="https://example.test/item",
        source=source,
        published_at="2026-01-01T00:00:00Z",
    )
    item.refresh_from_db()
    item.skills.add(
        Skill.objects.get(name="Fixture 1"), Skill.objects.get(name="Draft 1")
    )
    assert item_json(item)["skills"] == ["Fixture 1"]
    assert [p.pk for p in enrollable_pathways()] == [old.pk]


def test_retired_curriculum_cannot_be_reopened_or_edited():
    old = publish_demo_revision(revision())
    publish_demo_revision(revision(old.catalogue))
    old.refresh_from_db()
    old.status = "draft"
    with pytest.raises(ValidationError):
        old.save()
    old.status = "published"
    with pytest.raises(ValidationError):
        old.save()


@pytest.mark.parametrize("entity", ["pathway", "step", "checkpoint"])
@pytest.mark.parametrize(
    "operation", ["update", "delete", "bulk_update", "bulk_create"]
)
def test_curriculum_bulk_mutations_cannot_bypass_published_history(entity, operation):
    pathway = publish_demo_revision(revision())
    step = pathway.steps.first()
    checkpoint = step.checkpoint
    obj = dict(pathway=pathway, step=step, checkpoint=checkpoint)[entity]
    model = type(obj)
    with pytest.raises(ValidationError):
        if operation == "update":
            model.objects.filter(pk=obj.pk).update(pk=obj.pk)
        elif operation == "delete":
            model.objects.filter(pk=obj.pk).delete()
        elif operation == "bulk_update":
            model.objects.bulk_update([obj], ["title" if entity != "step" else "order"])
        else:
            model.objects.bulk_create([obj])
    assert model.objects.filter(pk=obj.pk).exists()


@pytest.mark.parametrize("entity", ["step", "checkpoint"])
@pytest.mark.parametrize("action", ["save", "delete"])
def test_reassigning_a_frozen_instance_parent_cannot_bypass_curriculum_guards(
    entity, action
):
    published = publish_demo_revision(revision())
    draft = revision(published.catalogue)
    step = published.steps.first()
    if entity == "step":
        obj = step
        obj.pathway = draft
    else:
        obj = step.checkpoint
        obj.pathway_skill = draft.steps.first()
    with pytest.raises(ValidationError):
        getattr(obj, action)()
    assert type(obj).objects.filter(pk=obj.pk).exists()
