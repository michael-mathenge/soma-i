import json
import os
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from engagement.management.commands.send_reminders import (
    Command as SendRemindersCommand,
)

RULES_PATH = (
    Path(settings.BASE_DIR).parent
    / ".agents"
    / "skills"
    / "soma-reminder-ops"
    / "rules.json"
)
LOG_PATH = (
    Path(settings.BASE_DIR).parent / ".local" / "soma-reminder-ops" / "alerts.jsonl"
)
DRAFT_SUBJECT = "SOMA.i reminder digest"
ALERT_FIELDS = (
    "learner_id",
    "pathway_title",
    "next_checkpoint_title",
    "completed_count",
    "remaining_count",
)


def _normalized_path(path):
    return os.path.normcase(str(path))


def _same_path(first, second):
    return _normalized_path(first) == _normalized_path(second)


def _path_is_under(path, parent):
    try:
        common = Path(os.path.commonpath([str(path), str(parent)]))
    except ValueError:
        return False
    return _same_path(common, parent) and not _same_path(path, parent)


def refuse_repository_databases():
    database_name = settings.DATABASES["default"].get("NAME")
    if not isinstance(database_name, (str, os.PathLike)) or str(database_name) in {
        "",
        ":memory:",
    }:
        return

    resolved_database = Path(database_name).expanduser().resolve(strict=False)
    backend_dir = Path(settings.BASE_DIR).resolve(strict=False)
    protected_paths = (
        backend_dir.parent / "db.sqlite3",
        backend_dir / "db.sqlite3",
    )
    for protected_path in protected_paths:
        if _same_path(resolved_database, protected_path.resolve(strict=False)):
            raise CommandError(
                "Refusing to read a repository db.sqlite3; set DATABASE_URL to an "
                "explicit safe database."
            )


def resolve_log_path(path):
    resolved_path = Path(path).expanduser().resolve(strict=False)
    repo_root = Path(settings.BASE_DIR).resolve(strict=False).parent
    local_dir = (repo_root / ".local").resolve(strict=False)
    temp_dir = Path(tempfile.gettempdir()).resolve(strict=False)

    if not _path_is_under(local_dir, repo_root):
        local_dir = None
    if not any(
        allowed is not None and _path_is_under(resolved_path, allowed)
        for allowed in (local_dir, temp_dir)
    ):
        raise CommandError(
            "The JSONL log path must resolve under the repository .local folder "
            "or the OS temporary directory."
        )
    if resolved_path.suffix.lower() != ".jsonl":
        raise CommandError("The reminder log path must end in .jsonl.")
    return resolved_path


def load_rules(path):
    try:
        rules_data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise CommandError(f"Cannot read rules file {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise CommandError(f"Rules file {path} is not valid JSON: {error.msg}.") from error

    if not isinstance(rules_data, dict) or set(rules_data) != {"version", "rules"}:
        raise CommandError(
            "Rules must be an object with exactly the 'version' and 'rules' fields."
        )
    if type(rules_data["version"]) is not int or rules_data["version"] != 1:
        raise CommandError("Rules field 'version' must be the integer 1.")
    rules = rules_data["rules"]
    if not isinstance(rules, list) or not rules:
        raise CommandError("Rules field 'rules' must be a non-empty array.")

    seen_ids = set()
    validated = []
    expected_fields = {"id", "enabled", "repeat_suppression_hours"}
    for index, rule in enumerate(rules, start=1):
        prefix = f"Rule {index}"
        if not isinstance(rule, dict) or set(rule) != expected_fields:
            raise CommandError(
                f"{prefix} must contain exactly 'id', 'enabled', and "
                "'repeat_suppression_hours'."
            )
        rule_id = rule["id"]
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise CommandError(f"{prefix} field 'id' must be a non-empty string.")
        if rule_id in seen_ids:
            raise CommandError(f"Rule id '{rule_id}' is duplicated.")
        seen_ids.add(rule_id)
        if type(rule["enabled"]) is not bool:
            raise CommandError(f"{prefix} field 'enabled' must be true or false.")
        hours = rule["repeat_suppression_hours"]
        if type(hours) is not int or hours < 1:
            raise CommandError(
                f"{prefix} field 'repeat_suppression_hours' must be a positive integer."
            )
        validated.append(rule)
    return validated


def _read_log(path):
    if not path.exists():
        return []
    events = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise CommandError(f"Cannot read JSONL log {path}: {error}") from error
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            event_time = parse_datetime(event["alerted_at"])
            rule_id = event["rule_id"]
            learner_id = event["learner_id"]
            if (
                event_time is None
                or timezone.is_naive(event_time)
                or not isinstance(rule_id, str)
                or type(learner_id) is not int
            ):
                raise ValueError("invalid event fields")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise CommandError(
                f"Invalid JSONL reminder event at {path}:{line_number}."
            ) from error
        events.append((event_time, rule_id, learner_id))
    return events


def format_alert_line(alert):
    return (
        f"Learner ID: {alert['learner_id']} | "
        f"Pathway: {alert['pathway_title']} | "
        f"Next checkpoint: {alert['next_checkpoint_title']} | "
        f"Completed: {alert['completed_count']} | "
        f"Remaining: {alert['remaining_count']}"
    )


def build_draft_payload(alerts, recipient=""):
    lines = [format_alert_line(alert) for alert in alerts]
    return {
        "to": recipient,
        "subject": DRAFT_SUBJECT,
        "body": "\n".join(lines),
    }


def create_gmail_draft(gmail_connector, payload):
    """Create a draft through an injected connector; never send or read mail."""
    return gmail_connector.create_draft(
        to=payload["to"], subject=payload["subject"], body=payload["body"]
    )


class Command(BaseCommand):
    help = "Evaluate due reminder rules and report new alerts without sending reminders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rules", default=str(RULES_PATH), help="Path to the reminder rules JSON."
        )
        parser.add_argument(
            "--log", default=str(LOG_PATH), help="Path to the repeat-suppression JSONL log."
        )
        parser.add_argument(
            "--now",
            help="Demo/test option: evaluate at this timezone-aware ISO datetime.",
        )
        parser.add_argument(
            "--json", action="store_true", help="Return structured data for the skill."
        )

    def handle(self, *args, **options):
        refuse_repository_databases()
        rules = load_rules(options["rules"])
        log_path = resolve_log_path(options["log"])
        now = self._parse_now(options.get("now"))

        preview_output = StringIO()
        preview = SendRemindersCommand()
        preview.clock = lambda: now
        preview.stdout = preview_output
        preview.handle(dry_run=True, json=True)
        candidate_data = json.loads(preview_output.getvalue())
        prior_events = _read_log(log_path)
        alerts = []
        events_to_log = []

        for candidate in candidate_data["reminders"]:
            alert = {field: candidate[field] for field in ALERT_FIELDS}
            for rule in rules:
                if not rule["enabled"]:
                    continue
                cutoff = now - timedelta(hours=rule["repeat_suppression_hours"])
                if any(
                    event_rule == rule["id"]
                    and event_learner == alert["learner_id"]
                    and event_time > cutoff
                    for event_time, event_rule, event_learner in prior_events
                ):
                    continue
                alerts.append(alert)
                events_to_log.append(
                    {
                        "alerted_at": now.isoformat(),
                        "rule_id": rule["id"],
                        "learner_id": alert["learner_id"],
                    }
                )
                prior_events.append((now, rule["id"], alert["learner_id"]))

        if events_to_log:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8", newline="\n") as log_file:
                    for event in events_to_log:
                        log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError as error:
                raise CommandError(f"Cannot append JSONL log {log_path}: {error}") from error

        alert_lines = [format_alert_line(alert) for alert in alerts]
        draft_payload = build_draft_payload(
            alerts, os.environ.get("SOMA_REMINDER_DRAFT_TO", "")
        )
        result = {
            "evaluated_at": now.isoformat(),
            "alerts": alerts,
            "alert_lines": alert_lines,
            "draft": draft_payload,
        }
        if options.get("json"):
            self.stdout.write(json.dumps(result, ensure_ascii=False))
        elif alert_lines:
            self.stdout.write("\n".join(alert_lines))
        else:
            self.stdout.write("No alerts.")

    @staticmethod
    def _parse_now(value):
        if value is None:
            return timezone.now()
        result = parse_datetime(value)
        if result is None or timezone.is_naive(result):
            raise CommandError("--now must be a timezone-aware ISO datetime.")
        return result
