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
    attribution = models.CharField(max_length=255, blank=True, default="")
    rights = models.CharField(max_length=80, default="not stated")
    level = models.CharField(max_length=20, default="mixed")
    language = models.CharField(max_length=8, default="en")
    active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    etag = models.CharField(max_length=512, blank=True, default="")
    last_modified = models.CharField(max_length=255, blank=True, default="")
    latest_item_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    title = models.CharField(max_length=300)
    url = models.URLField(unique=True)
    normalized_link = models.CharField(
        max_length=2048, unique=True, null=True, blank=True
    )
    guid = models.CharField(max_length=1000, blank=True, default="", db_index=True)
    summary = models.TextField(blank=True)
    published_at = models.DateTimeField()
    fetched_at = models.DateTimeField(null=True, blank=True)
    date_source = models.CharField(
        max_length=10,
        choices=[
            ("published", "Published"),
            ("updated", "Updated"),
            ("fetched", "Fetched"),
        ],
        null=True,
        blank=True,
    )
    word_count = models.PositiveIntegerField(null=True, blank=True)
    pathway_keys = models.JSONField(default=list, blank=True)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="items")
    language = models.CharField(max_length=8, default="en")
    skills = models.ManyToManyField(Skill, related_name="items", blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=10)
    is_low_data = models.BooleanField(default=True)

    def __str__(self):
        return self.title
