"""Record publisher reuse permission evidence in the discovery rules.

A path can only be published when at least two independent publishers have
verified permission to reuse their material. The publisher identities live
in the discovery rules file, which is reviewed content rather than
application data, so this command edits that file from a reviewed publisher
file rather than writing to a table.

The command is fail-closed. It refuses a publisher without a dated review,
refuses overlapping domains, because two publishers on the same domain are
not independent, and it never treats a licence string as permission.
"""

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from content.fetching import validate_feed_url
from pathways.discovery import REVIEW_DAYS, load_rules, validate_rules

REQUIRED_FIELDS = (
    "key",
    "domains",
    "reviewed_by",
    "reviewed_on",
    "expires_on",
    "evidence_url",
)


class Command(BaseCommand):
    help = (
        "Record publisher reuse permission evidence in the discovery rules "
        "file from a reviewed publishers file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            help=(
                "Path to a JSON file listing the approved publishers. It "
                "must be outside the repository, because it records the "
                "owner's decisions."
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
                "Path of the discovery rules file to update. It defaults to "
                "the file in the repository, which is the reviewed source of "
                "the publisher identities."
            ),
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser()
        if not path.is_file():
            raise CommandError(f"Reviewed publishers file not found: {path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Reviewed publishers file could not be read: {exc}")

        entries = document.get("publishers") if isinstance(document, dict) else document
        if not isinstance(entries, list) or not entries:
            raise CommandError(
                "The reviewed publishers file must list at least one publisher."
            )

        today = timezone.localdate()
        prepared = [
            self._prepare(entry, index, today) for index, entry in enumerate(entries)
        ]
        self._check_independence(prepared)

        rules = load_rules()
        publishers = dict(rules.get("publishers") or {})
        for publisher in prepared:
            # The key is the map key, so it is not repeated in the value.
            publishers[publisher["key"]] = {
                field: value for field, value in publisher.items() if field != "key"
            }
        rules["publishers"] = publishers
        validate_rules(rules)

        if options["dry_run"]:
            self.stdout.write(
                f"Validated {len(prepared)} publisher(s). No file was written."
            )
            for publisher in prepared:
                self.stdout.write(
                    f"  {publisher['key']}: {', '.join(publisher['domains'])}"
                )
            return

        rules_path = (
            Path(options["output"]) if options["output"] else self._rules_path()
        )
        rules_path.write_text(
            json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.stdout.write(f"Recorded {len(prepared)} publisher(s) in {rules_path}.")

    def _rules_path(self):
        return Path(__file__).resolve().parents[3] / "discovery_rules.json"

    def _prepare(self, entry, index, today):
        if not isinstance(entry, dict):
            raise CommandError(f"Publisher {index} is not an object.")
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise CommandError(
                f"Publisher {index} is missing: {', '.join(sorted(missing))}."
            )

        key = str(entry["key"]).strip()
        if not key or key != key.lower():
            raise CommandError(f"Publisher {index} needs a lowercase key: {key!r}.")

        domains = entry["domains"]
        if not isinstance(domains, list) or not domains:
            raise CommandError(f"Publisher {index} needs reviewed domains.")
        for host in domains:
            if not isinstance(host, str) or not host or host != host.lower():
                raise CommandError(f"Publisher {index} has an invalid domain: {host!r}")
            if host.endswith("."):
                raise CommandError(f"Publisher {index} has an invalid domain: {host!r}")
            try:
                validate_feed_url("https://" + host + "/")
            except ValueError as exc:
                raise CommandError(
                    f"Publisher {index} has an invalid domain: {host!r} ({exc})"
                )

        try:
            reviewed_on = date.fromisoformat(str(entry["reviewed_on"]))
            expires_on = date.fromisoformat(str(entry["expires_on"]))
        except ValueError as exc:
            raise CommandError(f"Publisher {index} has invalid review dates: {exc}")
        if not reviewed_on <= today <= expires_on:
            raise CommandError(
                f"Publisher {index} review is not current. It must start on or "
                f"before {today} and end on or after it."
            )
        if (expires_on - reviewed_on).days > REVIEW_DAYS:
            raise CommandError(
                f"Publisher {index} review lasts longer than {REVIEW_DAYS} days."
            )

        try:
            validate_feed_url(str(entry["evidence_url"]))
        except ValueError as exc:
            raise CommandError(f"Publisher {index} has an invalid evidence link: {exc}")

        independence = entry.get("independence_confirmed")
        if independence is not True:
            raise CommandError(
                f"Publisher {index} must confirm that it is independent of the "
                "other publishers."
            )

        return {
            "key": key,
            "domains": list(domains),
            "reviewed_by": str(entry["reviewed_by"]).strip(),
            "reviewed_on": reviewed_on.isoformat(),
            "expires_on": expires_on.isoformat(),
            "evidence_url": str(entry["evidence_url"]),
            "independence_confirmed": True,
        }

    def _check_independence(self, prepared):
        """Two publishers on the same domain are not two publishers."""
        seen = {}
        for publisher in prepared:
            for host in publisher["domains"]:
                for other_host in seen:
                    if (
                        host == other_host
                        or host.endswith("." + other_host)
                        or other_host.endswith("." + host)
                    ):
                        raise CommandError(
                            f"Publisher {publisher['key']} and "
                            f"{seen[other_host]} share a domain and cannot "
                            "count as independent."
                        )
                seen[host] = publisher["key"]
