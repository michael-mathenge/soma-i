from django.db import models


class LearnerProfile(models.Model):
    display_name = models.CharField(max_length=80, default="Learner")
    preferred_language = models.CharField(
        max_length=2, choices=[("en", "English"), ("sw", "Kiswahili")], default="en"
    )
    phone = models.CharField(max_length=30, blank=True)
    reminder_opt_in = models.BooleanField(default=False)
    reminder_frequency = models.CharField(max_length=12, default="weekly")
    chosen_pathway = models.ForeignKey(
        "pathways.Pathway",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="learners",
    )
    created_at = models.DateTimeField(auto_now_add=True)
