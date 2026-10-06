from django.db import models

from content.models import Skill


class Opportunity(models.Model):
    TYPES = [
        (value, value.title())
        for value in ("job", "internship", "scholarship", "course", "certification")
    ]
    title = models.CharField(max_length=180)
    type = models.CharField(max_length=20, choices=TYPES)
    provider = models.CharField(max_length=120)
    url = models.URLField()
    location = models.CharField(max_length=120, default="Kenya")
    skills = models.ManyToManyField(Skill, related_name="opportunities", blank=True)
    deadline = models.DateField(null=True, blank=True)
    source_note = models.CharField(
        max_length=180, default="Sample opportunity for demonstration"
    )

    def __str__(self):
        return self.title
