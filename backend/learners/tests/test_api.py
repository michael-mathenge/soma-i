import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from content.models import Skill
from learners.models import LearnerProfile
from pathways.constants import CANONICAL_PATHWAYS
from pathways.models import Checkpoint, CheckpointRecord, Pathway, PathwaySkill

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    call_command("seed_demo", verbosity=0)
    return {path.title: path for path in Pathway.objects.all()}


def test_onboard_complete_checkpoint_and_get_whats_next(seeded):
    client = APIClient()
    pathway = seeded["Data Analyst"]
    response = client.post(
        "/api/me/",
        {
            "display_name": "Test learner",
            "preferred_language": "en",
            "pathway_id": pathway.pk,
        },
        format="json",
    )
    assert response.status_code == 201
    first = pathway.steps.select_related("checkpoint").first().checkpoint
    response = client.post(
        f"/api/checkpoints/{first.pk}/complete/",
        {"self_attested": True, "quiz_answers": [0, 0, 0]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["unlocked_skill"] == "Spreadsheets"
    assert response.data["next_checkpoint"]["skill"] == "SQL"
    assert len(response.data["items"]) in (2, 3)
    assert response.data["opportunities"]
    record = CheckpointRecord.objects.get(
        learner__display_name="Test learner", checkpoint=first
    )
    assert record.quiz_answers == [0, 0, 0]


def test_direct_next_returns_latest_checkpoint_opportunities(seeded):
    client = APIClient()
    client.post("/api/demo/")

    response = client.get("/api/next/")

    assert response.status_code == 200
    assert response.data["unlocked_skill"] == "Spreadsheets"
    assert response.data["next_checkpoint"]["skill"] == "SQL"
    assert response.data["opportunities"]
    assert all(opportunity["sample"] for opportunity in response.data["opportunities"])
    assert all(
        opportunity["match_percent"] > 0
        for opportunity in response.data["opportunities"]
    )


def test_direct_next_without_learner_returns_empty_state(seeded):
    response = APIClient().get("/api/next/")

    assert response.status_code == 200
    assert response.data == {"available": False, "reason": "no_learner"}


def test_direct_next_without_pathway_returns_empty_state():
    learner = LearnerProfile.objects.create(display_name="No pathway")
    client = APIClient()
    session = client.session
    session["learner_id"] = learner.pk
    session.save()

    response = client.get("/api/next/")

    assert response.status_code == 200
    assert response.data == {"available": False, "reason": "no_pathway"}


def test_seed_demo_is_repeatable_and_opts_amina_into_english_weekly_reminders():
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    pathway_titles = [pathway["title"] for pathway in CANONICAL_PATHWAYS]
    assert LearnerProfile.objects.filter(display_name="Amina Demo").count() == 1
    assert {
        title: Pathway.objects.filter(title=title).count() for title in pathway_titles
    } == {title: 1 for title in pathway_titles}

    amina = LearnerProfile.objects.get(display_name="Amina Demo")
    assert amina.chosen_pathway.title == "Data Analyst"
    assert amina.preferred_language == "en"
    assert amina.reminder_opt_in is True
    assert amina.reminder_frequency == "weekly"
    assert amina.phone == ""


def test_seed_demo_upgrades_old_seed_without_losing_amina_progress():
    old_pathways = {
        "Data Analyst": ["Spreadsheets", "SQL", "Data Visualisation", "Statistics"],
        "Web Developer": ["HTML", "CSS", "JavaScript", "Accessibility"],
        "Digital Marketing Assistant": [
            "Content Strategy",
            "Social Media",
            "SEO",
            "Marketing Analytics",
        ],
    }
    paths = {}
    first_checkpoint = None
    for title, names in old_pathways.items():
        pathway = Pathway.objects.create(
            title=title, description="Old seeded path", target_outcome=title
        )
        paths[title] = pathway
        for order, name in enumerate(names, start=1):
            skill, _ = Skill.objects.get_or_create(
                slug=name.lower().replace(" ", "-"), defaults={"name": name}
            )
            step = PathwaySkill.objects.create(
                pathway=pathway, skill=skill, order=order
            )
            checkpoint = Checkpoint.objects.create(
                pathway_skill=step,
                title=f"{name} checkpoint",
                criteria="Practice",
                unlocks_text="Next",
            )
            if title == "Data Analyst" and order == 1:
                first_checkpoint = checkpoint

    amina = LearnerProfile.objects.create(
        display_name="Amina Demo", chosen_pathway=paths["Data Analyst"]
    )
    progress = CheckpointRecord.objects.create(
        learner=amina,
        checkpoint=first_checkpoint,
        status="done",
        self_attested=True,
        quiz_answers={"demo": True},
    )

    call_command("seed_demo", verbosity=0)

    amina.refresh_from_db()
    progress.refresh_from_db()
    assert amina.chosen_pathway_id == paths["Data Analyst"].pk
    assert progress.checkpoint_id == first_checkpoint.pk
    assert progress.status == "done"
    assert Pathway.objects.filter(pk=paths["Digital Marketing Assistant"].pk).exists()
    frontend = Pathway.objects.get(pk=paths["Web Developer"].pk)
    assert frontend.title == CANONICAL_PATHWAYS[1]["title"]
    assert list(
        frontend.steps.order_by("order").values_list("skill__name", flat=True)
    ) == list(CANONICAL_PATHWAYS[1]["skills"])

    response = APIClient().get("/api/pathways/")
    assert response.status_code == 200
    assert [path["title"] for path in response.data] == [
        pathway["title"] for pathway in CANONICAL_PATHWAYS
    ]


def test_seed_demo_fixture_picks_are_offline_low_data_and_labeled():
    from datetime import UTC, datetime

    from content.models import Item

    call_command("seed_demo", verbosity=0)

    fixed_date = datetime(2026, 1, 1, tzinfo=UTC)
    data_item = Item.objects.get(
        url="https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content"
    )
    assert data_item.title == "Spreadsheet skills for clear data (demo)"
    assert data_item.published_at == fixed_date

    for pathway in CANONICAL_PATHWAYS[1:]:
        for skill_name in pathway["skills"]:
            minimum = 1 if skill_name in {"API Development", "Testing"} else 2
            picks = Item.objects.filter(
                skills__name=skill_name,
                is_low_data=True,
                title__endswith="(sample content)",
            ).distinct()
            assert (
                sum(pathway["title"] in item.pathway_keys for item in picks) >= minimum
            ), (
                f"{pathway['title']} / {skill_name} should have at least "
                f"{minimum} picks"
            )


def test_seed_demo_keeps_existing_duplicate_rows_and_updates_lowest_id_match():
    call_command("seed_demo", verbosity=0)
    pathway = Pathway.objects.get(title="Data Analyst")
    duplicate_pathway = Pathway.objects.create(
        title="Data Analyst",
        description="Leave this duplicate pathway untouched.",
        target_outcome="Legacy outcome",
    )
    duplicate_learner = LearnerProfile.objects.create(
        display_name="Amina Demo",
        preferred_language="sw",
        reminder_opt_in=False,
        chosen_pathway=duplicate_pathway,
    )

    call_command("seed_demo", verbosity=0)

    assert Pathway.objects.filter(title="Data Analyst").count() == 2
    assert LearnerProfile.objects.filter(display_name="Amina Demo").count() == 2
    assert Pathway.objects.get(pk=duplicate_pathway.pk).description == (
        "Leave this duplicate pathway untouched."
    )
    assert (
        LearnerProfile.objects.get(pk=duplicate_learner.pk).preferred_language == "sw"
    )
    canonical_amina = (
        LearnerProfile.objects.filter(display_name="Amina Demo").order_by("pk").first()
    )
    assert canonical_amina is not None
    amina = canonical_amina
    assert amina.chosen_pathway_id == pathway.pk
    assert amina.preferred_language == "en"
    assert amina.reminder_opt_in is True


def test_health_endpoint_is_public():
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


def test_skip_restart_switch_and_delete_are_available(seeded):
    client = APIClient()
    data_path = seeded["Data Analyst"]
    web_path = seeded["Frontend Developer"]
    client.post("/api/me/", {"pathway_id": data_path.pk}, format="json")
    first = data_path.steps.first().checkpoint
    assert (
        client.post(f"/api/checkpoints/{first.pk}/skip/", {}, format="json").status_code
        == 200
    )
    assert CheckpointRecord.objects.filter(status="skipped").exists()
    assert client.get("/api/dashboard/").data["next_checkpoint"]["skill"] == "SQL"
    assert client.post("/api/pathway/restart/", {}, format="json").data["restarted"]
    assert not CheckpointRecord.objects.filter(status="skipped").exists()
    assert (
        client.post(
            "/api/pathway/switch/", {"pathway_id": web_path.pk}, format="json"
        ).data["pathway_id"]
        == web_path.pk
    )
    assert client.delete("/api/me/").data["deleted"]
    assert LearnerProfile.objects.filter(chosen_pathway=web_path).count() == 0


def test_quiz_must_have_three_answers_and_due_reminders_are_opt_in_and_bilingual(
    seeded, capsys
):
    from datetime import timedelta

    from django.utils import timezone

    from engagement.models import ReminderLog

    client = APIClient()
    pathway = seeded["Data Analyst"]
    client.post("/api/me/", {"pathway_id": pathway.pk}, format="json")
    checkpoint = pathway.steps.first().checkpoint
    assert (
        client.post(
            f"/api/checkpoints/{checkpoint.pk}/complete/",
            {"self_attested": True, "quiz_answers": [0]},
            format="json",
        ).status_code
        == 400
    )

    learner = LearnerProfile.objects.get(display_name="Learner")
    learner.reminder_opt_in = True
    learner.preferred_language = "sw"
    learner.save()
    recent = ReminderLog.objects.create(learner=learner, message="recent")
    recent.sent_at = timezone.now() - timedelta(days=1)
    recent.save(update_fields=["sent_at"])
    LearnerProfile.objects.create(chosen_pathway=pathway, display_name="No reminders")
    english_learner = LearnerProfile.objects.create(
        chosen_pathway=pathway,
        display_name="English reminders",
        preferred_language="en",
        reminder_opt_in=True,
    )
    call_command("send_reminders")
    output = capsys.readouterr().out
    assert "No reminders" not in output
    assert "English reminders" in output
    assert "lessons to your next checkpoint" in output
    english_message = ReminderLog.objects.get(learner=english_learner).message
    assert len(english_message) <= 160
    assert ReminderLog.objects.filter(learner=learner).count() == 1

    recent.sent_at = timezone.now() - timedelta(days=8)
    recent.save(update_fields=["sent_at"])
    call_command("send_reminders")
    output = capsys.readouterr().out
    message = [line for line in output.splitlines() if "SOMA.i:" in line][0].split(
        "SOMA.i: ", 1
    )[1]
    assert "Masomo" in message
    assert len("SOMA.i: " + message) <= 160
    assert ReminderLog.objects.filter(learner=learner).count() == 2
