import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learners", "0003_account_ownership")]
    operations = [
        migrations.AddField(
            model_name="account",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="AccountToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("digest", models.CharField(max_length=64, unique=True)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("verify", "Verify email"),
                            ("reset", "Reset password"),
                        ],
                        max_length=12,
                    ),
                ),
                ("state_digest", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tokens",
                        to="learners.account",
                    ),
                ),
            ],
        ),
    ]
