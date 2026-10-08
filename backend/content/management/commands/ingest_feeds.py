import json
from datetime import date, timedelta
from pathlib import Path

import feedparser
from django.core.management.base import BaseCommand
from django.utils import timezone

from content.fetching import FetchResponse, fetch_feed
from content.ingestion import feed_staleness, ingest_entries, items_for_pathway
from content.matching import load_config
from content.models import Source


class FeedResponseError(ValueError):
    pass


def parse_feed_response(response):
    if response.status == 304:
        return None
    if response.status < 200 or response.status >= 300:
        raise FeedResponseError(f"Unexpected HTTP status {response.status}")
    content_type = next(
        (
            value.lower()
            for key, value in response.headers.items()
            if key.lower() == "content-type"
        ),
        "",
    )
    sample = response.body.lstrip()[:512].lower()
    if "html" in content_type or sample.startswith((b"<!doctype html", b"<html")):
        raise FeedResponseError("Response is HTML, not an XML feed")
    parsed = feedparser.parse(response.body)
    if parsed.bozo:
        if not parsed.entries:
            raise FeedResponseError(
                f"Malformed feed: {parsed.bozo_exception or 'parser error'}"
            )
        return parsed.entries, str(parsed.bozo_exception)
    return parsed.entries, ""


def _validator_headers(source):
    headers = {}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified
    return headers


def _update_validators(source, headers):
    for name, field in (("etag", "etag"), ("last-modified", "last_modified")):
        value = next(
            (value for key, value in headers.items() if key.lower() == name), None
        )
        if value:
            setattr(source, field, value)


def _source_defaults(feed):
    return {
        "name": feed["name"],
        "credibility_note": f"RSS feed attributed to {feed['attribution']}.",
        "attribution": feed["attribution"],
        "rights": feed.get("rights", "not stated"),
        "level": feed.get("level", "mixed"),
    }


def _offline_entries(feed_key):
    fixture = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "feeds"
        / f"{feed_key}.json"
    )
    values = json.loads(fixture.read_text(encoding="utf-8"))
    if len(values) > 12:
        raise FeedResponseError(f"Offline fixture {fixture.name} exceeds 12 entries")
    return values


class Command(BaseCommand):
    help = "Fetch configured RSS feeds and store pathway-matched items."
    clock = staticmethod(timezone.now)
    fetcher = staticmethod(fetch_feed)

    def add_arguments(self, parser):
        parser.add_argument(
            "--offline", action="store_true", help="Use local JSON fixtures only."
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Bypass the one-hour minimum interval between live fetches; "
                "conditional ETag/Last-Modified validators are still sent."
            ),
        )
        parser.add_argument(
            "--reference-date",
            type=date.fromisoformat,
            help="Use this ISO date for source-staleness calculations.",
        )

    def handle(self, *args, **options):
        config = load_config()
        now = self.clock()
        reference_date = options.get("reference_date") or timezone.localdate(now)
        minimum_interval = timedelta(
            seconds=config["defaults"].get("fetch_min_interval_seconds", 3600)
        )
        pathway_duplicates = {key: 0 for key in config["pathways"]}
        feed_failures = []
        total_created = 0
        total_duplicates = 0

        for feed in config["feeds"]:
            defaults = _source_defaults(feed)
            source, _ = Source.objects.get_or_create(url=feed["url"], defaults=defaults)
            for name, value in defaults.items():
                setattr(source, name, value)
            if options["offline"]:
                source.save(update_fields=list(defaults))

            try:
                if options["offline"]:
                    entries = _offline_entries(feed["key"])
                    fetched_at = now
                else:
                    if (
                        not options["force"]
                        and source.last_fetched_at
                        and now - source.last_fetched_at < minimum_interval
                    ):
                        self.stdout.write(
                            f"{source.name}: skipped (minimum interval not elapsed)"
                        )
                        continue
                    source.last_fetched_at = now
                    source.save(
                        update_fields=[
                            "name",
                            "credibility_note",
                            "attribution",
                            "rights",
                            "level",
                            "last_fetched_at",
                        ]
                    )
                    response = self.fetcher(feed["url"], _validator_headers(source))
                    if not isinstance(response, FetchResponse):
                        response = FetchResponse(
                            response.status,
                            dict(response.headers),
                            response.body,
                        )
                    if response.status == 304:
                        _update_validators(source, response.headers)
                        source.save(update_fields=["etag", "last_modified"])
                        self.stdout.write(
                            f"{source.name}: unchanged (304 Not Modified)"
                        )
                        continue
                    parsed = parse_feed_response(response)
                    if parsed is None:
                        continue
                    entries, warning = parsed
                    if warning:
                        self.stderr.write(
                            self.style.WARNING(f"{source.name}: bozo feed ({warning})")
                        )
                    _update_validators(source, response.headers)
                    fetched_at = now

                stats = ingest_entries(source, feed, entries, fetched_at, config)
                source.latest_item_at = stats["latest_item_at"]
                source.save(update_fields=["etag", "last_modified", "latest_item_at"])
                total_created += stats["created"]
                total_duplicates += stats["duplicates_merged"]
                for pathway, count in stats["duplicate_pathway_counts"].items():
                    pathway_duplicates[pathway] += count
                self.stdout.write(
                    f"{source.name}: {stats['created']} new, "
                    f"{stats['duplicates_merged']} duplicate(s) merged, "
                    f"rejected: unsafe link: {stats['rejected_unsafe_link']}, "
                    f"{len(entries)} parsed"
                )
            except Exception as exc:  # Keep the remaining registry feeds running.
                feed_failures.append(feed["name"])
                self.stderr.write(
                    self.style.WARNING(f"{feed['name']}: feed failed ({exc})")
                )

        stale_feeds = []
        stale_by_pathway = {key: [] for key in config["pathways"]}
        for feed in config["feeds"]:
            source = Source.objects.filter(url=feed["url"]).first()
            if source is None:
                continue
            stale = feed_staleness(source, feed, reference_date, config)
            if stale["stale"]:
                age = (
                    "no dates"
                    if stale["age_days"] is None
                    else f"{stale['age_days']} days"
                )
                detail = f"{source.name} ({stale['reason']}: {age})"
                stale_feeds.append(detail)
                for pathway in feed["pathways"]:
                    stale_by_pathway[pathway].append(source.name)

        self.stdout.write("Pathway totals:")
        for pathway in config["pathways"]:
            items = items_for_pathway(pathway)
            date_counts = {"published": 0, "updated": 0, "fetched": 0, "unknown": 0}
            for item in items:
                key = item.date_source if item.date_source in date_counts else "unknown"
                date_counts[key] += 1
            self.stdout.write(
                f"{pathway}: {len(items)} stored; "
                f"{pathway_duplicates[pathway]} duplicate(s) merged; "
                f"stale feeds={', '.join(stale_by_pathway[pathway]) or 'none'}; "
                f"date_source published={date_counts['published']}, "
                f"updated={date_counts['updated']}, fetched={date_counts['fetched']}, "
                f"unknown={date_counts['unknown']}"
            )
        self.stdout.write(
            "Stale feeds: " + ("; ".join(stale_feeds) if stale_feeds else "none")
        )
        self.stdout.write(
            f"Ingestion complete: {total_created} new item(s), "
            f"{total_duplicates} duplicate merge(s), {len(feed_failures)} failed feed(s)."
        )
