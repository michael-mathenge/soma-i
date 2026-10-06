from django.db import models

from content.models import Skill


class Pathway(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField()
    target_outcome = models.CharField(max_length=160)
    locale = models.CharField(max_length=8, default="KE")
    skills = models.ManyToManyField(
        Skill, through="PathwaySkill", related_name="pathways"
    )

    def __str__(self):
        return self.title


class PathwaySkill(models.Model):
    pathway = models.ForeignKey(Pathway, on_delete=models.CASCADE, related_name="steps")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = [("pathway", "skill"), ("pathway", "order")]


class Checkpoint(models.Model):
    pathway_skill = models.OneToOneField(
        PathwaySkill, on_delete=models.CASCADE, related_name="checkpoint"
    )
    title = models.CharField(max_length=160)
    criteria = models.TextField()
    unlocks_text = models.TextField()
    quiz_json = models.JSONField(default=list)

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
