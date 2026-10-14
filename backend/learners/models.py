from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField(max_length=254, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="account_email_case_unique")
        ]


class AccountToken(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="tokens"
    )
    digest = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(
        max_length=12, choices=[("verify", "Verify email"), ("reset", "Reset password")]
    )
    state_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class LearnerProfile(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="learner_profile",
    )
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
