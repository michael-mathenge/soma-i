import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from engagement.models import ReminderLog
from engagement.senders import AfricasTalkingSender, ConsoleSender, message_for
from learners.models import LearnerProfile
from pathways.logic import progress_for


class Command(BaseCommand):
    help = "Print due weekly reminders for opted-in learners."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = timezone.now

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview due reminders without sending or writing ReminderLog rows.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print machine-readable JSON; requires --dry-run.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        json_output = options.get("json", False)
        if json_output and not dry_run:
            raise CommandError("--json requires --dry-run.")

        now = self.clock()
        cutoff = now - timedelta(days=7)
        sender = None
        if not dry_run:
            sender = (
                AfricasTalkingSender()
                if __import__("os").getenv("SOMA_SENDER") == "africastalking"
                else ConsoleSender()
            )
        count = 0
        reminders = []
        for learner in LearnerProfile.objects.filter(
            reminder_opt_in=True, chosen_pathway__isnull=False
        ):
            last = learner.reminders.order_by("-sent_at").first()
            if last and last.sent_at > cutoff:
                continue
            state = progress_for(learner)
            if state["next_checkpoint"] is None:
                continue
            if dry_run:
                reminders.append(
                    {
                        "learner_id": learner.pk,
                        "pathway_title": learner.chosen_pathway.title,
                        "next_checkpoint_title": state["next_checkpoint"].title,
                        "completed_count": len(state["done"]),
                        "remaining_count": len(state["remaining"]),
                    }
                )
                continue
            message = message_for(
                learner, len(state["remaining"]), learner.chosen_pathway.title
            )
            if len(message) > 160:
                message = message[:157] + "..."
            sender.send(learner, message)
            ReminderLog.objects.create(
                learner=learner, message=message, sender=sender.name
            )
            count += 1
        if json_output:
            self.stdout.write(
                json.dumps(
                    {"evaluated_at": now.isoformat(), "reminders": reminders},
                    ensure_ascii=False,
                )
            )
        elif dry_run:
            self.stdout.write(f"Would send {len(reminders)} reminder(s).")
        else:
            self.stdout.write(f"Sent {count} reminder(s).")
