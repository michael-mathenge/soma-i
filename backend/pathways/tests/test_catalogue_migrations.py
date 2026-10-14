import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_catalogue_migration_preserves_all_legacy_ids_duplicates_and_learner_progress():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    old_targets = [("pathways", "0001_initial"), ("learners", "0002_initial")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_targets)
    apps = executor.loader.project_state(old_targets).apps
    Pathway = apps.get_model("pathways", "Pathway")
    Skill = apps.get_model("content", "Skill")
    Step = apps.get_model("pathways", "PathwaySkill")
    Checkpoint = apps.get_model("pathways", "Checkpoint")
    Learner = apps.get_model("learners", "LearnerProfile")
    Record = apps.get_model("pathways", "CheckpointRecord")
    rows = []
    learners = []
    records = []
    for index, title in enumerate(
        (
            "Data Analyst",
            "Data Analyst",
            "Frontend Developer",
            "Backend/Python Developer",
            "Custom legacy topic",
        )
    ):
        pathway = Pathway.objects.create(
            title=title,
            description=f"Keep description {index}",
            target_outcome="Original outcome",
            locale="KE",
        )
        skill = Skill.objects.create(
            name=f"Legacy skill {index}", slug=f"legacy-skill-{index}"
        )
        step = Step.objects.create(pathway=pathway, skill=skill, order=1)
        checkpoint = Checkpoint.objects.create(
            pathway_skill=step,
            title="Original checkpoint",
            criteria="Original work",
            unlocks_text="Original next",
            quiz_json=[],
        )
        learner = Learner.objects.create(chosen_pathway=pathway)
        record = Record.objects.create(
            learner=learner,
            checkpoint=checkpoint,
            status="done",
            self_attested=True,
            quiz_answers={"legacy": True},
        )
        rows.append(pathway)
        learners.append(learner)
        records.append(record)
    try:
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        CurrentPathway = apps.get_model("pathways", "Pathway")
        CurrentLearner = apps.get_model("learners", "LearnerProfile")
        CurrentRecord = apps.get_model("pathways", "CheckpointRecord")
        assert CurrentPathway.objects.count() == 5
        assert apps.get_model("pathways", "Catalogue").objects.count() == 3
        for index, (old, learner, record) in enumerate(
            zip(rows, learners, records, strict=True)
        ):
            current = CurrentPathway.objects.get(pk=old.pk)
            assert (
                current.title,
                current.description,
                current.target_outcome,
                current.locale,
            ) == (old.title, old.description, old.target_outcome, old.locale)
            assert CurrentLearner.objects.get(pk=learner.pk).chosen_pathway_id == old.pk
            saved = CurrentRecord.objects.get(pk=record.pk)
            assert saved.checkpoint_id == record.checkpoint_id
            assert saved.quiz_answers == {"legacy": True}
            assert saved.status == "done"
            step = current.steps.get()
            assert step.checkpoint.criteria == "Original work"
            assert step.checkpoint.quiz_json == []
            if index in (0, 2, 3):
                assert current.version == 1 and current.status == "published"
                assert current.enrollment_open and current.is_demo
                assert current.catalogue_id is not None
            else:
                assert current.catalogue_id is None and current.status == "draft"
                assert not current.enrollment_open and not current.is_demo
        # Reversal removes catalogue fields, not the original rows or progress.
        MigrationExecutor(connection).migrate(old_targets)
        assert Pathway.objects.count() == 5
        assert Record.objects.count() == 5
        assert [Learner.objects.get(pk=p.pk).chosen_pathway_id for p in learners] == [
            p.pk for p in rows
        ]
        MigrationExecutor(connection).migrate(latest)
        assert CurrentPathway.objects.count() == 5
    finally:
        MigrationExecutor(connection).migrate(latest)
