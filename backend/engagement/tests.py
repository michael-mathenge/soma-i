import json
import re
import tempfile
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import override_settings

from engagement.management.commands.reminder_ops import (
    build_draft_payload,
    create_gmail_draft,
    load_rules,
    resolve_log_path,
)
from engagement.management.commands.send_reminders import (
    Command as SendRemindersCommand,
)
from engagement.models import ReminderLog
from learners.models import LearnerProfile

pytestmark = pytest.mark.django_db


REPO_ROOT = Path(settings.BASE_DIR).parent
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "soma-reminder-ops"


@pytest.fixture
def local_temp_dir():
    local_dir = REPO_ROOT / ".local"
    local_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="test-reminder-ops-", dir=local_dir) as path:
        yield Path(path)


def _seed_due_learner():
    call_command("seed_demo", verbosity=0)
    return LearnerProfile.objects.get(display_name="Amina Demo")


def test_send_reminders_uses_injected_clock_at_seven_day_boundary():
    learner = _seed_due_learner()
    now = datetime(2030, 1, 8, 12, tzinfo=UTC)
    reminder = ReminderLog.objects.create(learner=learner, message="recent")
    reminder.sent_at = now - timedelta(days=7)
    reminder.save(update_fields=["sent_at"])
    output = StringIO()

    command = SendRemindersCommand()
    command.clock = lambda: now
    command.stdout = output
    command.handle()

    assert "Sent 1 reminder(s)." in output.getvalue()
    assert ReminderLog.objects.filter(learner=learner).count() == 2


def test_dry_run_json_omits_phone_numbers_and_display_names():
    learner = _seed_due_learner()
    learner.display_name = "Private Display Name"
    learner.phone = "+254700000001"
    learner.save(update_fields=["display_name", "phone"])
    before_count = ReminderLog.objects.filter(learner=learner).count()
    output = StringIO()

    call_command("send_reminders", "--dry-run", "--json", stdout=output)

    payload = json.loads(output.getvalue())
    assert payload["reminders"]
    assert set(payload["reminders"][0]) == {
        "learner_id",
        "pathway_title",
        "next_checkpoint_title",
        "completed_count",
        "remaining_count",
    }
    assert "Private Display Name" not in output.getvalue()
    assert "+254700000001" not in output.getvalue()
    assert ReminderLog.objects.filter(learner=learner).count() == before_count


@pytest.mark.parametrize("database_kind", ["root", "backend"])
def test_reminder_ops_refuses_repository_database_paths(
    database_kind, monkeypatch
):
    database_dir = REPO_ROOT if database_kind == "root" else Path(settings.BASE_DIR)
    database_path = database_dir / "db.sqlite3"

    def reject_connection(*_args, **_kwargs):
        pytest.fail("reminder_ops attempted to open a database connection")

    monkeypatch.setattr(BaseDatabaseWrapper, "get_new_connection", reject_connection)
    with override_settings(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(database_path),
            }
        }
    ):
        with pytest.raises(CommandError, match="Refusing to read a repository"):
            call_command("reminder_ops", verbosity=0)


def test_rules_file_schema_is_validated(local_temp_dir):
    rules_path = SKILL_DIR / "rules.json"
    rules = load_rules(rules_path)
    assert len(rules) == 1
    assert rules[0]["repeat_suppression_hours"] == 24

    invalid_path = local_temp_dir / "invalid-rules.json"
    invalid_path.write_text(
        '{"version": 1, "rules": [{"id": "missing-hours", "enabled": true}]}',
        encoding="utf-8",
    )
    with pytest.raises(CommandError, match="repeat_suppression_hours"):
        load_rules(invalid_path)


def test_skill_file_has_front_matter_and_no_secrets():
    skill_path = SKILL_DIR / "SKILL.md"
    skill_text = skill_path.read_text(encoding="utf-8")
    assert skill_text.startswith("---\nname: soma-reminder-ops\n")
    assert "description:" in skill_text.split("---", 2)[1]
    assert re.search(r"(?i)never send|never read mail", skill_text)
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b|\bAIza[\w-]{35}\b", skill_text)
    assert not re.search(
        r"(?i)\b(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9/_+=.-]{12,}",
        skill_text,
    )


def test_reminder_ops_suppresses_repeats_until_cooldown_expires(local_temp_dir):
    _seed_due_learner()
    log_path = local_temp_dir / "alerts.jsonl"
    first_now = datetime(2030, 1, 8, 12, tzinfo=UTC)

    def run_at(now):
        output = StringIO()
        call_command(
            "reminder_ops",
            "--json",
            "--log",
            str(log_path),
            "--now",
            now.isoformat(),
            stdout=output,
        )
        return json.loads(output.getvalue())

    first = run_at(first_now)
    second = run_at(first_now + timedelta(hours=23))
    third = run_at(first_now + timedelta(hours=25))

    assert len(first["alerts"]) == 1
    assert second["alerts"] == []
    assert len(third["alerts"]) == 1
    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 2


def test_reminder_ops_rejects_log_path_outside_local_or_temp():
    outside_path = REPO_ROOT / "unsafe-reminder-log.jsonl"
    with pytest.raises(CommandError, match="repository .local folder"):
        resolve_log_path(outside_path)


def test_gmail_draft_helper_only_creates_a_draft():
    alerts = [
        {
            "learner_id": 12,
            "pathway_title": "Data Analyst",
            "next_checkpoint_title": "SQL checkpoint",
            "completed_count": 1,
            "remaining_count": 3,
            "display_name": "must not appear",
            "phone": "+254700000001",
            "message": "must not appear",
        }
    ]
    payload = build_draft_payload(alerts, "ops@example.test")

    class MockGmail:
        def __init__(self):
            self.calls = []

        def create_draft(self, **kwargs):
            self.calls.append(("create_draft", kwargs))
            return {"id": "mock-draft"}

        def send(self, *_args, **_kwargs):
            self.calls.append(("send", {}))

        def read_mail(self, *_args, **_kwargs):
            self.calls.append(("read_mail", {}))

    gmail = MockGmail()
    result = create_gmail_draft(gmail, payload)

    assert result == {"id": "mock-draft"}
    assert [call[0] for call in gmail.calls] == ["create_draft"]
    assert "must not appear" not in payload["body"]
    assert "+254700000001" not in payload["body"]
    assert payload["body"] == (
        "Learner ID: 12 | Pathway: Data Analyst | "
        "Next checkpoint: SQL checkpoint | Completed: 1 | Remaining: 3"
    )
