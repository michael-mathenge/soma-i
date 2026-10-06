from django.db import models


class Skill(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Source(models.Model):
    name = models.CharField(max_length=120)
    url = models.URLField(unique=True)
    credibility_note = models.TextField()
    language = models.CharField(max_length=8, default="en")
    active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    title = models.CharField(max_length=300)
    url = models.URLField(unique=True)
    summary = models.TextField(blank=True)
    published_at = models.DateTimeField()
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="items")
    language = models.CharField(max_length=8, default="en")
    skills = models.ManyToManyField(Skill, related_name="items", blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=10)
    is_low_data = models.BooleanField(default=True)

    def __str__(self):
        return self.title
