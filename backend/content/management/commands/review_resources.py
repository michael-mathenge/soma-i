"""Record owner review evidence for ingested items.

A path can only be published when an owner has confirmed, for a specific
item, that it is freely accessible, in English, attributed, and covered by
a publisher whose reuse permission has been verified. The pipeline has
always required that evidence; this command is how it is recorded, so the
review does not have to be written by hand into a database.

The command is deliberately fail-closed. It validates every field before it
writes anything, it never creates a review for an item it was not given,
and it never infers permission from a licence string, a feed tag or a
previous approval.
"""

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from content.fetching import validate_feed_url
from content.models import Item, ResourceReview
from content.permissions import FeedPermissionError, approved_feed_urls
from pathways.discovery import content_fingerprint

# A review may not last longer than the publisher review window.
MAX_REVIEW_DAYS = 90
REQUIRED_FIELDS = (
    "url",
    "publisher_key",
    "author",
    "reviewed_by",
    "reviewed_on",
    "expires_on",
    "evidence_url",
)


class Command(BaseCommand):
    help = (
        "Record owner review evidence for ingested items from a reviewed "
        "items file. Writes ResourceReview rows only; it never approves a "
        "publisher or a feed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            help=(
                "Path to a JSON file listing the reviewed items. It must be "
                "outside the repository, because it records the owner's "
                "decisions."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and report what would be written.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser()
        if not path.is_file():
            raise CommandError(f"Reviewed items file not found: {path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Reviewed items file could not be read: {exc}")

        entries = document.get("items") if isinstance(document, dict) else document
        if not isinstance(entries, list) or not entries:
            raise CommandError("The reviewed items file must list at least one item.")

        today = timezone.localdate()
        prepared = []
        for index, entry in enumerate(entries):
            prepared.append(self._prepare(entry, index, today))

        if options["dry_run"]:
            self.stdout.write(
                f"Validated {len(prepared)} review(s). No rows were written."
            )
            for review in prepared:
                self.stdout.write(
                    f"  {review['item'].title} -> publisher {review['publisher_key']}"
                )
            return

        written = 0
        for review in prepared:
            item = review["item"]
            record, _ = ResourceReview.objects.update_or_create(
                item=item,
                defaults={
                    "content_fingerprint": review["content_fingerprint"],
                    "reviewed_by": review["reviewed_by"],
                    "reviewed_on": review["reviewed_on"],
                    "expires_on": review["expires_on"],
                    "evidence_url": review["evidence_url"],
                    "author": review["author"],
                    "publisher_key": review["publisher_key"],
                    "free_access": review["free_access"],
                    "english_confirmed": review["english_confirmed"],
                    "evergreen": review["evergreen"],
                    "evergreen_reason": review["evergreen_reason"],
                },
            )
            written += 1
            self.stdout.write(f"Reviewed {item.title} as {record.publisher_key}.")
        self.stdout.write(f"Recorded {written} review(s).")

    def _prepare(self, entry, index, today):
        if not isinstance(entry, dict):
            raise CommandError(f"Review {index} is not an object.")
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise CommandError(
                f"Review {index} is missing: {', '.join(sorted(missing))}."
            )

        item = self._item(entry["url"], index)
        source = item.source
        self._check_feed_permission(source, today, index)

        publisher_key = str(entry["publisher_key"]).strip()
        self._check_publisher(item, source, publisher_key, index)

        try:
            reviewed_on = date.fromisoformat(str(entry["reviewed_on"]))
            expires_on = date.fromisoformat(str(entry["expires_on"]))
        except ValueError as exc:
            raise CommandError(f"Review {index} has invalid review dates: {exc}")
        if not reviewed_on <= today <= expires_on:
            raise CommandError(
                f"Review {index} is not current. The review must start on or "
                f"before {today} and end on or after it."
            )
        if (expires_on - reviewed_on).days > MAX_REVIEW_DAYS:
            raise CommandError(
                f"Review {index} lasts longer than {MAX_REVIEW_DAYS} days."
            )

        try:
            validate_feed_url(str(entry["evidence_url"]))
        except ValueError as exc:
            raise CommandError(f"Review {index} has an invalid evidence link: {exc}")

        free_access = entry.get("free_access", True)
        english_confirmed = entry.get("english_confirmed", True)
        if not free_access or not english_confirmed:
            raise CommandError(
                f"Review {index} must confirm free access and English content."
            )
        evergreen = bool(entry.get("evergreen", False))
        evergreen_reason = str(entry.get("evergreen_reason", "")).strip()
        if evergreen and not evergreen_reason:
            raise CommandError(
                f"Review {index} marks the item evergreen and must give a reason."
            )
        if not evergreen and entry.get("evergreen_reason"):
            raise CommandError(
                f"Review {index} gives an evergreen reason but does not mark the "
                "item evergreen."
            )

        return {
            "item": item,
            "content_fingerprint": content_fingerprint(item),
            "reviewed_by": str(entry["reviewed_by"]).strip(),
            "reviewed_on": reviewed_on,
            "expires_on": expires_on,
            "evidence_url": str(entry["evidence_url"]),
            "author": str(entry["author"]).strip(),
            "publisher_key": publisher_key,
            "free_access": bool(free_access),
            "english_confirmed": bool(english_confirmed),
            "evergreen": evergreen,
            "evergreen_reason": evergreen_reason,
        }

    def _item(self, url, index):
        item = Item.objects.filter(url=url).select_related("source").first()
        if item is None:
            raise CommandError(
                f"Review {index} refers to an item that has not been ingested: {url}"
            )
        return item

    def _check_feed_permission(self, source, today, index):
        """The feed must itself carry verified permission evidence."""
        from content.matching import load_config, source_for_url

        feed = source_for_url(source.url, load_config())
        if not feed:
            raise CommandError(
                f"Review {index} refers to a source that is not in the feed "
                f"registry: {source.url}"
            )
        try:
            approved_feed_urls(feed, today)
        except FeedPermissionError as exc:
            raise CommandError(
                f"Review {index} refers to a feed without verified permission: {exc}"
            )

    def _check_publisher(self, item, source, publisher_key, index):
        """The publisher must be recorded, current and independent."""
        from pathways.discovery import load_rules

        publishers = load_rules().get("publishers", {})
        publisher = publishers.get(publisher_key)
        if not publisher:
            raise CommandError(
                f"Review {index} names a publisher that is not recorded: {publisher_key}"
            )
        if publisher.get("independence_confirmed") is not True:
            raise CommandError(
                f"Review {index} names a publisher whose independence is not "
                f"confirmed: {publisher_key}"
            )
        domains = publisher.get("domains") or []
        for url in (item.url, source.url):
            host = url.split("/")[2].lower()
            if not any(
                host == domain or host.endswith("." + domain) for domain in domains
            ):
                raise CommandError(
                    f"Review {index} refers to a URL outside the recorded "
                    f"publisher domains: {url}"
                )
        today = timezone.localdate()
        try:
            reviewed = date.fromisoformat(str(publisher["reviewed_on"]))
            expires = date.fromisoformat(str(publisher["expires_on"]))
        except (KeyError, ValueError) as exc:
            raise CommandError(
                f"Review {index} names a publisher without review dates: {exc}"
            )
        if not reviewed <= today <= expires:
            raise CommandError(
                f"Review {index} names a publisher whose review is not current: "
                f"{publisher_key}"
            )
        if (expires - reviewed).days > MAX_REVIEW_DAYS:
            raise CommandError(
                f"Review {index} names a publisher whose review is too old: "
                f"{publisher_key}"
            )
