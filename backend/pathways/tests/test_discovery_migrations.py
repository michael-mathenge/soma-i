from datetime import UTC, datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_discovery_migrations_preserve_legacy_content_versions_and_progress_without_approvals():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    old_targets = [
        ("content", "0003_source_level"),
        ("pathways", "0002_versioned_catalogue"),
    ]
    executor = MigrationExecutor(connection)
    executor.migrate(old_targets)
    apps = executor.loader.project_state(old_targets).apps
    Source = apps.get_model("content", "Source")
    Item = apps.get_model("content", "Item")
    Catalogue = apps.get_model("pathways", "Catalogue")
    Pathway = apps.get_model("pathways", "Pathway")
    Skill = apps.get_model("content", "Skill")
    Step = apps.get_model("pathways", "PathwaySkill")
    Checkpoint = apps.get_model("pathways", "Checkpoint")
    Learner = apps.get_model("learners", "LearnerProfile")
    Record = apps.get_model("pathways", "CheckpointRecord")
    source = Source.objects.create(
        name="Legacy",
        url="https://legacy.example.test/feed",
        attribution="Original attribution",
    )
    item = Item.objects.create(
        source=source,
        title="Original content",
        summary="Original excerpt",
        url="https://legacy.example.test/item",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        pathway_keys=["Data Analyst"],
    )
    catalogue = Catalogue.objects.create(slug="legacy-catalogue")
    path = Pathway.objects.create(
        catalogue=catalogue,
        title="Original pathway",
        description="Original description",
        target_outcome="Original outcome",
        status="published",
        version=4,
        enrollment_open=True,
        is_demo=True,
    )
    skill = Skill.objects.create(name="Legacy skill", slug="legacy-skill")
    step = Step.objects.create(pathway=path, skill=skill, order=1)
    checkpoint = Checkpoint.objects.create(
        pathway_skill=step,
        title="Original checkpoint",
        criteria="Original practice",
        unlocks_text="Original next",
        quiz_json=[],
    )
    learner = Learner.objects.create(chosen_pathway=path)
    record = Record.objects.create(
        learner=learner, checkpoint=checkpoint, status="done"
    )
    try:
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new_apps = executor.loader.project_state(latest).apps
        NewItem = new_apps.get_model("content", "Item")
        NewPath = new_apps.get_model("pathways", "Pathway")
        saved = NewItem.objects.get(pk=item.pk)
        assert saved.topic_tags == []
        assert saved.match_text == "Original excerpt" and saved.date_source is None
        # The forward migration moves the stored text into internal matching
        # text and clears any republicable excerpt.
        assert saved.excerpt == ""
        assert not new_apps.get_model("content", "ResourceReview").objects.exists()
        assert not new_apps.get_model("pathways", "PathwayResource").objects.exists()
        current = NewPath.objects.get(pk=path.pk)
        assert (
            current.version == 4 and current.status == "published" and current.is_demo
        )
        assert not current.discovery_managed and current.publication_key == ""
        assert (
            current.coverage_checked_at is None
            and current.coverage_failed_since is None
        )
        assert (
            new_apps.get_model("learners", "LearnerProfile")
            .objects.get(pk=learner.pk)
            .chosen_pathway_id
            == path.pk
        )
        assert (
            new_apps.get_model("pathways", "CheckpointRecord")
            .objects.get(pk=record.pk)
            .checkpoint_id
            == checkpoint.pk
        )
        MigrationExecutor(connection).migrate(old_targets)
        assert Pathway.objects.get(pk=path.pk).version == 4
        assert Item.objects.get(pk=item.pk).summary == "Original excerpt"
        assert Record.objects.get(pk=record.pk).checkpoint_id == checkpoint.pk
    finally:
        MigrationExecutor(connection).migrate(latest)
