"""Publish curated curricula from a reviewed file of reading links.

This is the hand-checked route to a live pathway. It exists because the
automatic route needs two independent publishers whose reuse permission
is verified, and a small learning site often has one publisher with
generous terms rather than two with narrow ones.

The reviewed file holds the owner's decisions, so it lives outside the
repository. The learning sequence, the checkpoint criteria and the
check-in questions come from the reviewed discovery rules.
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from pathways.curated import (
    load_curated_file,
    publish_curated_topic,
    validate_curated_topics,
)


class Command(BaseCommand):
    help = (
        "Publish curated curricula from a reviewed file of hand-checked "
        "reading links. Writes pathway revisions only; it never approves a "
        "publisher or a feed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            help=(
                "Path to the reviewed curricula file. It must be outside the "
                "repository, because it records the owner's decisions."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and report what would be published.",
        )

    def handle(self, *args, **options):
        from pathways.discovery import load_rules

        try:
            topics = load_curated_file(options["path"])
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
                raise CommandError(
                    f"Curated curricula were not published: {exc}"
                )
            self.stdout.write(
                f"{slug}: {result['action']} (version {result['version']})"
            )
