import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from learners.models import LearnerProfile
from pathways.models import CheckpointRecord, Pathway

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


def test_health_endpoint_is_public():
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


def test_skip_restart_switch_and_delete_are_available(seeded):
    client = APIClient()
    data_path = seeded["Data Analyst"]
    web_path = seeded["Web Developer"]
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
