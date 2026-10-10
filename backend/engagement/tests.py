import json
import os
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


def test_send_reminders_dry_run_sends_and_logs_nothing(monkeypatch):
    learner = _seed_due_learner()
    before_count = ReminderLog.objects.filter(learner=learner).count()

    def fail_if_sender_is_created(*_args, **_kwargs):
        pytest.fail("dry-run created an SMS sender")

    monkeypatch.setenv("SOMA_SENDER", "africastalking")
    monkeypatch.setattr(
        "engagement.management.commands.send_reminders.AfricasTalkingSender",
        fail_if_sender_is_created,
    )
    monkeypatch.setattr(
        "engagement.management.commands.send_reminders.ConsoleSender",
        fail_if_sender_is_created,
    )
    output = StringIO()

    call_command("send_reminders", "--dry-run", stdout=output)

    assert output.getvalue() == "Would send 1 reminder(s).\n"
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


@pytest.mark.skipif(
    os.name != "nt",
    reason="Upper-case path alias behavior is specific to Windows filesystems.",
)
@pytest.mark.parametrize("database_kind", ["root", "backend"])
def test_reminder_ops_refuses_uppercase_repository_database_paths(
    database_kind, monkeypatch
):
    database_dir = REPO_ROOT if database_kind == "root" else Path(settings.BASE_DIR)
    database_path = Path(str(database_dir / "db.sqlite3").upper())

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


def test_rules_allow_disabled_extras_but_reject_multiple_enabled(local_temp_dir):
    rules_path = local_temp_dir / "multiple-rules.json"
    rules_path.write_text(
        json.dumps(
            {
                "version": 1,
                "rules": [
                    {
                        "id": "active-one",
                        "enabled": True,
                        "repeat_suppression_hours": 24,
                    },
                    {
                        "id": "inactive",
                        "enabled": False,
                        "repeat_suppression_hours": 12,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    assert len(load_rules(rules_path)) == 2

    rules_data = json.loads(rules_path.read_text(encoding="utf-8"))
    rules_data["rules"][1]["enabled"] = True
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")
    with pytest.raises(CommandError, match="at most one enabled rule"):
        load_rules(rules_path)


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
    command = re.search(r"`([^`]*manage\.py reminder_ops --json)`", skill_text)
    assert command is not None
    command_parts = command.group(1).split()
    assert command_parts[0].startswith(".\\")
    assert command_parts[1] == r"backend\manage.py"
    assert (REPO_ROOT / "backend" / "manage.py").is_file()
    assert "DATABASE_URL" in skill_text
    assert "never point it at either repository `db.sqlite3`" in skill_text
    assert "If Gmail is unavailable, skip the draft and keep the alert report." in skill_text


def test_reminder_ops_returns_one_alert_per_due_learner(local_temp_dir):
    amina = _seed_due_learner()
    second_learner = LearnerProfile.objects.create(
        display_name="Second Due Learner",
        reminder_opt_in=True,
        chosen_pathway=amina.chosen_pathway,
    )
    output = StringIO()
    call_command(
        "reminder_ops",
        "--json",
        "--log",
        str(local_temp_dir / "alerts.jsonl"),
        "--now",
        "2030-01-08T12:00:00+00:00",
        stdout=output,
    )

    payload = json.loads(output.getvalue())
    learner_ids = [alert["learner_id"] for alert in payload["alerts"]]
    assert sorted(learner_ids) == sorted([amina.pk, second_learner.pk])


def test_reminder_ops_reports_alerts_without_gmail(local_temp_dir, monkeypatch):
    _seed_due_learner()
    monkeypatch.delenv("SOMA_REMINDER_DRAFT_TO", raising=False)
    output = StringIO()

    call_command(
        "reminder_ops",
        "--json",
        "--log",
        str(local_temp_dir / "alerts.jsonl"),
        "--now",
        "2030-01-08T12:00:00+00:00",
        stdout=output,
    )

    payload = json.loads(output.getvalue())
    assert payload["alerts"]
    assert payload["alert_lines"]
    assert payload["draft"]["body"] == payload["alert_lines"][0]


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


def test_reminder_ops_skips_corrupt_middle_log_line_and_warns(local_temp_dir):
    learner = _seed_due_learner()
    log_path = local_temp_dir / "alerts.jsonl"
    rule_id = "weekly-due-reminder"
    log_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "alerted_at": "2030-01-08T12:00:00+00:00",
                        "rule_id": rule_id,
                        "learner_id": learner.pk,
                    }
                ),
                '{"private":"DO NOT ECHO THIS RAW LOG TEXT"',
                json.dumps({"alerted_at": "2030-01-08T12:15:00+00:00"}),
                json.dumps(
                    {
                        "alerted_at": "2030-01-08T12:30:00+00:00",
                        "rule_id": rule_id,
                        "learner_id": 999999,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = StringIO()

    call_command(
        "reminder_ops",
        "--json",
        "--log",
        str(log_path),
        "--now",
        "2030-01-08T13:00:00+00:00",
        stdout=output,
    )

    payload = json.loads(output.getvalue())
    assert payload["alerts"] == []
    assert payload["warnings"] == ["Skipped 2 malformed log line(s)."]
    assert set(payload) == {
        "evaluated_at",
        "alerts",
        "alert_lines",
        "draft",
        "warnings",
    }
    assert "DO NOT ECHO THIS RAW LOG TEXT" not in output.getvalue()


def test_reminder_ops_separates_append_after_truncated_log_line(local_temp_dir):
    _seed_due_learner()
    log_path = local_temp_dir / "truncated.jsonl"
    truncated_line = b'{"private truncated record":'
    log_path.write_bytes(truncated_line)
    output = StringIO()

    call_command(
        "reminder_ops",
        "--json",
        "--log",
        str(log_path),
        "--now",
        "2030-01-08T12:00:00+00:00",
        stdout=output,
    )

    payload = json.loads(output.getvalue())
    assert len(payload["alerts"]) == 1
    assert payload["warnings"] == ["Skipped 1 malformed log line(s)."]
    lines = log_path.read_bytes().splitlines()
    assert lines[0] == truncated_line
    assert json.loads(lines[1])["rule_id"] == "weekly-due-reminder"


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
