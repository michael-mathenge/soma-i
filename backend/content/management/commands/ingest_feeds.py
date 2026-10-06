from django.core.management.base import BaseCommand
from django.utils import timezone

from content.ingestion import ingest_entries
from content.models import Source
from content.sources import SOURCES


class Command(BaseCommand):
    help = "Fetch and deduplicate items from the configured educational RSS feeds."

    def handle(self, *args, **options):
        import feedparser

        total = 0
        for config in SOURCES:
            source, _ = Source.objects.get_or_create(url=config["url"], defaults=config)
            try:
                feed = feedparser.parse(source.url)
                if getattr(feed, "bozo", False) and not feed.entries:
                    raise ValueError(str(feed.bozo_exception))
                created = ingest_entries(source, feed.entries)
                source.last_fetched_at = timezone.now()
                source.save(update_fields=["last_fetched_at"])
                total += created
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{source.name}: {created} new item(s), {len(feed.entries)} parsed"
                    )
                )
            except (
                Exception
            ) as exc:  # Keep other sources ingesting if one host is unavailable.
                self.stderr.write(
                    self.style.WARNING(f"{source.name}: feed unavailable ({exc})")
                )
        self.stdout.write(f"Ingestion complete: {total} new item(s).")
