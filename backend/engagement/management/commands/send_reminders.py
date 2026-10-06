from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from engagement.models import ReminderLog
from engagement.senders import AfricasTalkingSender, ConsoleSender, message_for
from learners.models import LearnerProfile
from pathways.logic import progress_for


class Command(BaseCommand):
    help = "Print due weekly reminders for opted-in learners."

    def handle(self, *args, **options):
        sender = (
            AfricasTalkingSender()
            if __import__("os").getenv("SOMA_SENDER") == "africastalking"
            else ConsoleSender()
        )
        cutoff = timezone.now() - timedelta(days=7)
        count = 0
        for learner in LearnerProfile.objects.filter(
            reminder_opt_in=True, chosen_pathway__isnull=False
        ):
            last = learner.reminders.order_by("-sent_at").first()
            if last and last.sent_at > cutoff:
                continue
            state = progress_for(learner)
            if state["next_checkpoint"] is None:
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
        self.stdout.write(f"Sent {count} reminder(s).")
