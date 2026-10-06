from django.db import models


class ReminderLog(models.Model):
    learner = models.ForeignKey(
        "learners.LearnerProfile", on_delete=models.CASCADE, related_name="reminders"
    )
    message = models.CharField(max_length=160)
    sent_at = models.DateTimeField(auto_now_add=True)
    sender = models.CharField(max_length=30, default="console")
