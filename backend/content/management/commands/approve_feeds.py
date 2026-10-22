"""Record feed access and reuse permission evidence in the feed registry.

A feed may only be fetched, and only its material may be reused, after an
owner has confirmed permission for that exact endpoint. The feed registry
is reviewed content rather than application data, so this command edits
that file from a reviewed feeds file.

The command is fail-closed. It refuses a feed without a dated review, it
refuses an approval that does not cover the registry endpoint, and it
never treats a rights string as permission.
"""

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from content.fetching import validate_feed_url

MAX_PERMISSION_DAYS = 90
REQUIRED_FIELDS = (
    "key",
    "reviewed_by",
    "scope",
    "reviewed_on",
    "expires_on",
    "evidence_url",
    "allowed_urls",
)


class Command(BaseCommand):
    help = (
        "Record feed access and reuse permission evidence in the feed "
        "registry from a reviewed feeds file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            help=(
                "Path to a JSON file listing the approved feeds. It must be "
                "outside the repository, because it records the owner's "
                "decisions."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and report what would change.",
        )
        parser.add_argument(
            "--output",
            default=None,
            help=(
                "Path of the feed registry to update. It defaults to the "
                "file in the repository, which is the reviewed source of the "
                "feed permissions."
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser()
        if not path.is_file():
            raise CommandError(f"Reviewed feeds file not found: {path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Reviewed feeds file could not be read: {exc}")

        entries = document.get("feeds") if isinstance(document, dict) else document
        if not isinstance(entries, list) or not entries:
            raise CommandError("The reviewed feeds file must list at least one feed.")

        today = timezone.localdate()
        prepared = [
            self._prepare(entry, index, today) for index, entry in enumerate(entries)
        ]

        registry = self._registry()
        feeds = {feed["key"]: feed for feed in registry.get("feeds", [])}
        for approval in prepared:
            feed = feeds.get(approval["key"])
            if feed is None:
                raise CommandError(
                    f"Approval names a feed that is not in the registry: "
                    f"{approval['key']}"
                )
            if feed["url"] not in approval["allowed_urls"]:
                raise CommandError(
                    f"Approval for {approval['key']} does not cover the "
                    f"registry endpoint: {feed['url']}"
                )
            approval["publisher_key"] = approval.get("publisher_key")
            feed["permissions"] = approval["permissions"]
            if approval["publisher_key"]:
                feed["publisher_key"] = approval["publisher_key"]
            if approval.get("rights"):
                feed["rights"] = approval["rights"]

        if options["dry_run"]:
            self.stdout.write(
                f"Validated {len(prepared)} feed approval(s). No file was written."
            )
            for approval in prepared:
                self.stdout.write(f"  {approval['key']}")
            return

        registry_path = (
            Path(options["output"]) if options["output"] else self._registry_path()
        )
        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(
            f"Recorded {len(prepared)} feed approval(s) in {registry_path}."
        )

    def _registry_path(self):
        return Path(__file__).resolve().parents[2] / "feeds.json"

    def _registry(self):
        return json.loads(self._registry_path().read_text(encoding="utf-8"))

    def _prepare(self, entry, index, today):
        if not isinstance(entry, dict):
            raise CommandError(f"Approval {index} is not an object.")
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise CommandError(
                f"Approval {index} is missing: {', '.join(sorted(missing))}."
            )

        try:
            reviewed_on = date.fromisoformat(str(entry["reviewed_on"]))
            expires_on = date.fromisoformat(str(entry["expires_on"]))
        except ValueError as exc:
            raise CommandError(f"Approval {index} has invalid review dates: {exc}")
        if not reviewed_on <= today <= expires_on:
            raise CommandError(
                f"Approval {index} is not current. It must start on or before "
                f"{today} and end on or after it."
            )
        if (expires_on - reviewed_on).days > MAX_PERMISSION_DAYS:
            raise CommandError(
                f"Approval {index} lasts longer than {MAX_PERMISSION_DAYS} days."
            )

        try:
            validate_feed_url(str(entry["evidence_url"]))
        except ValueError as exc:
            raise CommandError(f"Approval {index} has an invalid evidence link: {exc}")

        allowed = entry["allowed_urls"]
        if not isinstance(allowed, list) or not 1 <= len(allowed) <= 6:
            raise CommandError(
                f"Approval {index} must approve one to six exact endpoints."
            )
        for url in allowed:
            try:
                validate_feed_url(str(url))
            except ValueError as exc:
                raise CommandError(
                    f"Approval {index} has an invalid approved endpoint: {url} ({exc})"
                )

        permissions = {
            "reviewed_by": str(entry["reviewed_by"]).strip(),
            "scope": str(entry["scope"]).strip(),
            "reviewed_on": reviewed_on.isoformat(),
            "expires_on": expires_on.isoformat(),
            "evidence_url": str(entry["evidence_url"]),
            "allowed_urls": [str(url) for url in allowed],
            "feed_access": entry.get("feed_access", True) is True,
            "metadata_reuse": entry.get("metadata_reuse", True) is True,
            # Excerpt reuse is separate and is not granted by default.
            "excerpt_reuse": entry.get("excerpt_reuse", False) is True,
        }
        if not permissions["feed_access"] or not permissions["metadata_reuse"]:
            raise CommandError(
                f"Approval {index} must grant feed access and metadata reuse."
            )

        return {
            "key": str(entry["key"]).strip(),
            "allowed_urls": [str(url) for url in allowed],
            "permissions": permissions,
            "publisher_key": str(entry.get("publisher_key", "")).strip() or None,
            "rights": str(entry.get("rights", "")).strip() or None,
        }
