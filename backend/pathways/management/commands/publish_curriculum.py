"""Publish curated curricula from a reviewed file of reading links.

This is the hand-checked route to a live pathway. It exists because the
automatic route needs two independent publishers whose reuse permission
is verified, and a small learning site often has one publisher with
generous terms rather than two with narrow ones.

The reviewed curricula live beside the reviewed discovery rules, so the
whole curriculum is reviewed in one place. The learning sequence, the
checkpoint criteria and the check-in questions come from the discovery
rules; only the reading list comes from the curricula file.
"""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from pathways.curated import (
    load_curated_file,
    publish_curated_topic,
    validate_curated_topics,
)

# The reviewed curricula live beside the discovery rules, so the whole
# curriculum is reviewed in the same place.
DEFAULT_CURRICULA_PATH = Path(__file__).resolve().parents[2] / "curricula.json"


class Command(BaseCommand):
    help = (
        "Publish curated curricula from a reviewed file of hand-checked "
        "reading links. Writes pathway revisions only; it never approves a "
        "publisher or a feed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=None,
            help=(
                "Path to the reviewed curricula file. It defaults to the "
                "reviewed file in the repository."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and report what would be published.",
        )

    def handle(self, *args, **options):
        from pathways.discovery import load_rules

        path = options["path"] or DEFAULT_CURRICULA_PATH
        try:
            topics = load_curated_file(path)
            validate_curated_topics(topics, load_rules(), timezone.localdate())
        except ValidationError as exc:
            raise CommandError(f"Curated curricula were not published: {exc}")

        if options["dry_run"]:
            self.stdout.write(
                f"Validated {len(topics)} curated topic(s). Nothing was published."
            )
            for slug, steps in topics.items():
                links = sum(len(entries) for entries in steps.values())
                self.stdout.write(f"  {slug}: {len(steps)} steps, {links} links")
            return

        for slug, steps in topics.items():
            try:
                result = publish_curated_topic(slug, steps)
            except ValidationError as exc:
                raise CommandError(f"Curated curricula were not published: {exc}")
            self.stdout.write(
                f"{slug}: {result['action']} (version {result['version']})"
            )
