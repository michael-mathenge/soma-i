from django.core.exceptions import ValidationError
from django.db import models

from content.models import Skill


def require_draft(pathway_ids):
    if Pathway.objects.filter(pk__in=pathway_ids).exclude(status="draft").exists():
        raise ValidationError("Published curriculum is frozen; create a revision.")


class CurriculumQuerySet(models.QuerySet):
    """Require validated saves; protect frozen rows from ordinary bulk writes."""

    def update(self, **kwargs):
        raise ValidationError("Use curriculum saves or create a new revision.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Bulk curriculum updates are not supported.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Bulk curriculum creation is not supported.")

    def delete(self):
        field = {
            "pathway": "pk",
            "pathwayskill": "pathway_id",
            "checkpoint": "pathway_skill__pathway_id",
            "pathwayresource": "pathway_skill__pathway_id",
        }[self.model._meta.model_name]
        pathways = Pathway.objects.filter(pk__in=self.values_list(field, flat=True))
        if (
            pathways.exclude(status="draft").exists()
            or pathways.filter(learners__isnull=False).exists()
        ):
            raise ValidationError(
                "Preserve published or learner-selected curriculum history."
            )
        return super().delete()


class Catalogue(models.Model):
    """Stable topic identity; each Pathway row is one learner-pinned revision."""

    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.slug


class Pathway(models.Model):
    objects = CurriculumQuerySet.as_manager()

    catalogue = models.ForeignKey(
        Catalogue,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=12,
        default="draft",
        choices=[
            ("draft", "Draft"),
            ("published", "Published"),
            ("retired", "Retired"),
        ],
    )
    enrollment_open = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)
    discovery_managed = models.BooleanField(default=False)
    publication_key = models.CharField(max_length=64, blank=True, default="")
    coverage_checked_at = models.DateTimeField(null=True, blank=True)
    coverage_failed_since = models.DateTimeField(null=True, blank=True)
    coverage_report = models.JSONField(default=dict, blank=True)

    title = models.CharField(max_length=120)
    description = models.TextField()
    target_outcome = models.CharField(max_length=160)
    locale = models.CharField(max_length=8, default="KE")
    skills = models.ManyToManyField(
        Skill, through="PathwaySkill", related_name="pathways"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["catalogue", "version"],
                name="unique_catalogue_version",
            ),
            models.UniqueConstraint(
                fields=["catalogue"],
                condition=models.Q(status="published"),
                name="one_published_catalogue_version",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1), name="positive_pathway_version"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "published", "retired"]),
                name="valid_pathway_status",
            ),
            models.CheckConstraint(
                condition=models.Q(enrollment_open=False)
                | (models.Q(status="published") & models.Q(catalogue__isnull=False)),
                name="enrollment_requires_published_catalogue",
            ),
        ]

    def save(self, *args, **kwargs):
        previous = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        if previous and previous.status != "draft":
            frozen = (
                "catalogue_id",
                "version",
                "title",
                "description",
                "target_outcome",
                "locale",
                "is_demo",
                "discovery_managed",
                "publication_key",
            )
            if any(
                getattr(previous, field) != getattr(self, field) for field in frozen
            ):
                raise ValidationError(
                    "Create a new revision instead of editing a published pathway."
                )
            if self.status == "draft" or (
                previous.status == "retired" and self.status != "retired"
            ):
                raise ValidationError(
                    "Published history cannot become a draft or be republished."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if (
            type(self).objects.exclude(status="draft").filter(pk=self.pk).exists()
            or self.learners.exists()
        ):
            raise ValidationError(
                "Preserve published or learner-selected pathway history."
            )
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.title


class PathwaySkill(models.Model):
    objects = CurriculumQuerySet.as_manager()

    pathway = models.ForeignKey(Pathway, on_delete=models.CASCADE, related_name="steps")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField()

    def save(self, *args, **kwargs):
        previous = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        require_draft([self.pathway_id] + ([previous.pathway_id] if previous else []))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        saved_ids = (
            type(self).objects.filter(pk=self.pk).values_list("pathway_id", flat=True)
        )
        require_draft([self.pathway_id, *saved_ids])
        return super().delete(*args, **kwargs)

    class Meta:
        ordering = ["order"]
        unique_together = [("pathway", "skill"), ("pathway", "order")]


class Checkpoint(models.Model):
    objects = CurriculumQuerySet.as_manager()

    pathway_skill = models.OneToOneField(
        PathwaySkill, on_delete=models.CASCADE, related_name="checkpoint"
    )
    title = models.CharField(max_length=160)
    criteria = models.TextField()
    unlocks_text = models.TextField()
    quiz_json = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        previous = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        step_ids = [self.pathway_skill_id] + (
            [previous.pathway_skill_id] if previous else []
        )
        require_draft(
            PathwaySkill.objects.filter(pk__in=step_ids).values_list(
                "pathway_id", flat=True
            )
        )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        saved_ids = (
            type(self)
            .objects.filter(pk=self.pk)
            .values_list("pathway_skill__pathway_id", flat=True)
        )
        require_draft([self.pathway_skill.pathway_id, *saved_ids])
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.title


class CheckpointRecord(models.Model):
    learner = models.ForeignKey(
        "learners.LearnerProfile",
        on_delete=models.CASCADE,
        related_name="checkpoint_records",
    )
    checkpoint = models.ForeignKey(
        Checkpoint, on_delete=models.CASCADE, related_name="records"
    )
    status = models.CharField(
        max_length=12, choices=[("done", "Done"), ("skipped", "Skipped")]
    )
    self_attested = models.BooleanField(default=False)
    quiz_answers = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("learner", "checkpoint")]


class ItemRecord(models.Model):
    learner = models.ForeignKey(
        "learners.LearnerProfile", on_delete=models.CASCADE, related_name="item_records"
    )
    item = models.ForeignKey("content.Item", on_delete=models.CASCADE)
    done_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("learner", "item")]


class PathwayResource(models.Model):
    objects = CurriculumQuerySet.as_manager()

    pathway_skill = models.ForeignKey(
        PathwaySkill, on_delete=models.CASCADE, related_name="resources"
    )
    item = models.ForeignKey(
        "content.Item", on_delete=models.PROTECT, related_name="curriculum_links"
    )
    content_fingerprint = models.CharField(max_length=64)
    evidence_snapshot = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        saved_ids = (
            type(self)
            .objects.filter(pk=self.pk)
            .values_list("pathway_skill__pathway_id", flat=True)
        )
        require_draft([self.pathway_skill.pathway_id, *saved_ids])
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return type(self).objects.filter(pk=self.pk).delete()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pathway_skill", "item"], name="unique_step_resource"
            )
        ]


class CoverageObservation(models.Model):
    pathway = models.ForeignKey(
        Pathway, on_delete=models.PROTECT, related_name="coverage_observations"
    )
    observed_at = models.DateTimeField()
    healthy = models.BooleanField()
    report = models.JSONField(default=dict)
