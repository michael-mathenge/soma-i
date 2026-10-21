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
    # Feed text used only to decide which pathway an item belongs to. It is
    # never published, and the API never returns it.
    match_text = models.TextField(blank=True)
    # Publisher text cleared for republication. Empty unless a review
    # confirmed explicit reuse permission, so the default is to publish
    # title, publisher and date only and link out to the original.
    excerpt = models.TextField(blank=True)
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
    topic_tags = models.JSONField(default=list, blank=True)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="items")
    language = models.CharField(max_length=8, default="en")
    skills = models.ManyToManyField(Skill, related_name="items", blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=10)
    is_low_data = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class ResourceReview(models.Model):
    """Owner-reviewed evidence; feed text cannot grant itself release eligibility."""

    item = models.OneToOneField(
        Item, on_delete=models.CASCADE, related_name="release_review"
    )
    content_fingerprint = models.CharField(max_length=64)
    reviewed_by = models.CharField(max_length=120)
    reviewed_on = models.DateField()
    expires_on = models.DateField()
    evidence_url = models.URLField(max_length=2048)
    author = models.CharField(max_length=255)
    publisher_key = models.SlugField(max_length=120)
    free_access = models.BooleanField(default=False)
    english_confirmed = models.BooleanField(default=False)
    evergreen = models.BooleanField(default=False)
    evergreen_reason = models.TextField(blank=True)
