import json
import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from content.management.commands.ingest_feeds import _offline_database_allowed
from pathways.discovery import discover_pathways


class Command(BaseCommand):
    help = "Report discovery coverage; --apply updates only an isolated local/test catalogue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply reviewed rules to isolated local/test data.",
        )

    def handle(self, *args, **options):
        # Hosted target allowlists/workflows belong to later reviewed operations.
        if not os.environ.get("DATABASE_URL") or not _offline_database_allowed(
            connection.settings_dict
        ):
            raise CommandError(
                "Discovery requires an explicit OS-temp/in-memory SQLite target; hosted execution is not enabled."
            )
        try:
            results = discover_pathways(apply=options["apply"])
        except (ValidationError, ValueError, TypeError, KeyError, OSError) as exc:
            raise CommandError(
                "Discovery stopped: invalid rules or changed coverage; no source permission is inferred."
            ) from exc
        self.stdout.write(
            json.dumps(
                dict(mode="apply" if options["apply"] else "dry-run", results=results),
                sort_keys=True,
            )
        )
