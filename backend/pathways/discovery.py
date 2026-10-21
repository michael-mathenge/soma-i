"""Deterministic, network-free discovery over reviewed RSS metadata.

Only owner-controlled rules and dated reviews authorize eligibility. Feed text
is matching data. Provider/release authorization and hosted scheduling are
separate gates; this module never fetches a destination or approves a source.
"""

import calendar
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from content.fetching import validate_feed_url
from content.ingestion import normalize_link
from content.matching import (
    exclusion_reason,
    load_config,
    matches_terms,
    plain_text,
    source_for_url,
)
from content.models import Item
from content.permissions import FeedPermissionError, approved_feed_urls
from pathways.catalogue import create_revision, validate_steps
from pathways.models import Catalogue, CoverageObservation, Pathway, PathwayResource

REVIEW_DAYS = 90
COVERAGE_GRACE = timedelta(days=7)
CHECK_MAX_AGE = timedelta(days=1)


@lru_cache(maxsize=1)
def load_rules():
    return json.loads(
        Path(__file__).with_name("discovery_rules.json").read_text(encoding="utf-8")
    )


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def content_fingerprint(item):
    return digest(
        dict(
            title=item.title,
            match_text=item.match_text,
            url=item.url,
            source_url=item.source.url,
            language=item.language,
            published_at=item.published_at.isoformat(),
            date_source=item.date_source,
            topic_tags=sorted(item.topic_tags)
            if isinstance(item.topic_tags, list)
            else [],
        )
    )


def matching_topic_slugs(tags, rules=None):
    if not isinstance(tags, list):
        return []
    text = " ".join(plain_text(tag)[:120] for tag in tags[:32] if isinstance(tag, str))
    return [
        topic["slug"]
        for topic in (rules or load_rules())["topics"]
        if matches_terms(text, topic["aliases"])
    ]


def _review_current(record, today):
    try:
        reviewed = date.fromisoformat(str(record["reviewed_on"]))
        expires = date.fromisoformat(str(record["expires_on"]))
        validate_feed_url(record["evidence_url"])
        return bool(
            isinstance(record.get("reviewed_by"), str)
            and record["reviewed_by"].strip()
            and reviewed <= today <= expires
            and (expires - reviewed).days <= REVIEW_DAYS
        )
    except (TypeError, KeyError, ValueError):
        return False


def validate_rules(rules):
    if not isinstance(rules, dict) or rules.get("version") != 1:
        raise ValidationError("Unsupported discovery rule version.")
    topics = rules.get("topics")
    publishers = rules.get("publishers")
    if not isinstance(topics, list) or not isinstance(publishers, dict):
        raise ValidationError("Rules need topic definitions and publisher evidence.")
    slugs = set()
    for topic in topics:
        if not isinstance(topic, dict):
            raise ValidationError("Invalid topic definition.")
        for field in ("slug", "title", "description", "target_outcome"):
            if not isinstance(topic.get(field), str) or not topic[field].strip():
                raise ValidationError("Topic metadata must be explicit.")
        if (
            not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic["slug"])
            or len(topic["slug"]) > 120
        ):
            raise ValidationError("Topic identity must be a bounded lowercase slug.")
        if topic["slug"] in slugs:
            raise ValidationError("Duplicate topic identity.")
        slugs.add(topic["slug"])
        aliases = topic.get("aliases")
        if (
            not isinstance(aliases, list)
            or not aliases
            or any(not isinstance(a, str) or not a.strip() for a in aliases)
        ):
            raise ValidationError("Topic aliases must be nonempty strings.")
        validate_steps(topic.get("steps"))
        earlier = set()
        for step in topic["steps"]:
            aliases = step.get("aliases")
            requires = step.get("requires")
            if (
                not isinstance(aliases, list)
                or not aliases
                or any(not isinstance(a, str) or not a.strip() for a in aliases)
            ):
                raise ValidationError("Skills need explicit matching aliases.")
            if not isinstance(requires, list) or any(
                not isinstance(name, str) or name not in earlier for name in requires
            ):
                raise ValidationError("Unknown, cyclic or out-of-order prerequisite.")
            earlier.add(step["skill"])
    domains = []
    for key, publisher in publishers.items():
        if not isinstance(key, str) or not key or not isinstance(publisher, dict):
            raise ValidationError("Invalid publisher identity.")
        hosts = publisher.get("domains")
        if not isinstance(hosts, list) or not hosts:
            raise ValidationError("Publisher identity needs reviewed domains.")
        for host in hosts:
            if not isinstance(host, str) or host != host.lower() or host.endswith("."):
                raise ValidationError("Invalid publisher domain.")
            try:
                validate_feed_url("https://" + host + "/")
                if urlsplit("https://" + host + "/").hostname != host:
                    raise ValueError("Domain must not contain URL components")
            except ValueError as exc:
                raise ValidationError("Invalid publisher domain.") from exc
            for other_key, other_host in domains:
                if key != other_key and (
                    host == other_host
                    or host.endswith("." + other_host)
                    or other_host.endswith("." + host)
                ):
                    raise ValidationError(
                        "Overlapping publisher domains cannot count independently."
                    )
            domains.append((key, host))


def _belongs(url, domains):
    host = urlsplit(url).hostname or ""
    return any(host == domain or host.endswith("." + domain) for domain in domains)


@dataclass(frozen=True)
class EligibleResource:
    item: Item
    canonical_url: str
    publisher_key: str
    fingerprint: str


def eligible_resource(item, *, rules, feeds, now):
    """Return verified stored evidence, never infer approval from a licence/tag."""
    today = timezone.localdate(now)
    try:
        review = item.release_review
    except Item.release_review.RelatedObjectDoesNotExist:
        return None
    feed = source_for_url(item.source.url, feeds)
    if not feed or not item.source.active:
        return None
    if exclusion_reason(item.title, feed.get("source_type", "publisher"), feeds):
        return None
    try:
        approved_feed_urls(feed, today)
        validate_feed_url(item.url)
        validate_feed_url(review.evidence_url)
    except (FeedPermissionError, ValueError, TypeError):
        return None
    if (
        not isinstance(item.topic_tags, list)
        or len(item.topic_tags) > 32
        or any(not isinstance(t, str) or len(t) > 120 for t in item.topic_tags)
    ):
        return None
    publisher = rules["publishers"].get(review.publisher_key)
    if not publisher or feed.get("publisher_key") != review.publisher_key:
        return None
    if publisher.get("independence_confirmed") is not True or not _review_current(
        publisher, today
    ):
        return None
    if not _belongs(item.url, publisher["domains"]) or not _belongs(
        item.source.url, publisher["domains"]
    ):
        return None
    if (
        not review.free_access
        or not review.english_confirmed
        or item.language != "en"
        or item.source.language != "en"
    ):
        return None
    if (
        not review.author.strip()
        or not review.reviewed_by.strip()
        or not item.source.attribution.strip()
    ):
        return None
    if (
        not review.reviewed_on <= today <= review.expires_on
        or (review.expires_on - review.reviewed_on).days > REVIEW_DAYS
    ):
        return None
    if item.date_source not in {"published", "updated"} or item.published_at > now:
        return None
    if not item.fetched_at or item.fetched_at > now:
        return None
    cutoff = date(
        today.year - 2,
        today.month,
        min(today.day, calendar.monthrange(today.year - 2, today.month)[1]),
    )
    if item.published_at.date() < cutoff and not (
        review.evergreen and review.evergreen_reason.strip()
    ):
        return None
    fingerprint = content_fingerprint(item)
    if review.content_fingerprint != fingerprint:
        return None
    return EligibleResource(
        item, normalize_link(item.url), review.publisher_key, fingerprint
    )


def eligible_resources(*, rules, feeds, now):
    resources = []
    seen = set()
    for item in Item.objects.select_related("source", "release_review").order_by("pk"):
        resource = eligible_resource(item, rules=rules, feeds=feeds, now=now)
        if resource and resource.canonical_url not in seen:
            resources.append(resource)
            seen.add(resource.canonical_url)
    return sorted(resources, key=lambda r: (r.canonical_url, r.item.pk))


def topic_coverage(topic, resources):
    candidates = [
        r
        for r in resources
        if topic["slug"] in matching_topic_slugs(r.item.topic_tags, {"topics": [topic]})
    ]
    pools = []
    for step in topic["steps"]:
        pools.append(
            [
                r
                for r in candidates
                if matches_terms(
                    " ".join(
                        [r.item.title, r.item.match_text[:300], *r.item.topic_tags]
                    ),
                    step["aliases"],
                )
            ]
        )
    counts = {
        step["skill"]: len(pool)
        for step, pool in zip(topic["steps"], pools, strict=True)
    }
    publishers = sorted({r.publisher_key for pool in pools for r in pool})
    healthy = all(count >= 3 for count in counts.values()) and len(publishers) >= 2
    report = dict(per_skill=counts, publisher_keys=publishers, healthy=healthy)
    if not healthy:
        return report, []
    selected = [pool[:3] for pool in pools]
    selected_publishers = {r.publisher_key for pool in selected for r in pool}
    if len(selected_publishers) < 2:
        for index, pool in enumerate(pools):
            alternative = next(
                (r for r in pool if r.publisher_key not in selected_publishers), None
            )
            if alternative:
                selected[index][-1] = alternative
                break
    return report, selected


def evidence_snapshot(resource, rules, feeds):
    review = resource.item.release_review
    fields = (
        "reviewed_by",
        "reviewed_on",
        "expires_on",
        "evidence_url",
        "author",
        "publisher_key",
        "free_access",
        "english_confirmed",
        "evergreen",
        "evergreen_reason",
    )
    data = {field: getattr(review, field) for field in fields}
    data["reviewed_on"] = data["reviewed_on"].isoformat()
    data["expires_on"] = data["expires_on"].isoformat()
    feed = source_for_url(resource.item.source.url, feeds)
    return dict(
        resource_review=data,
        publisher_review=rules["publishers"][resource.publisher_key],
        feed_permissions=feed["permissions"],
    )


def publication_key(topic, selected):
    return digest(
        dict(
            topic=topic,
            resources=[
                [(r.canonical_url, r.publisher_key, r.fingerprint) for r in pool]
                for pool in selected
            ],
        )
    )


def _record_coverage(pathway, report, now):
    if pathway.coverage_checked_at and now < pathway.coverage_checked_at:
        raise ValidationError("Coverage clock cannot move backwards.")
    pathway.coverage_checked_at = now
    pathway.coverage_report = report
    if report["healthy"]:
        pathway.coverage_failed_since = None
        pathway.enrollment_open = True
    else:
        pathway.coverage_failed_since = pathway.coverage_failed_since or now
        if now - pathway.coverage_failed_since >= COVERAGE_GRACE:
            pathway.enrollment_open = False
    pathway.save(
        update_fields=[
            "coverage_checked_at",
            "coverage_report",
            "coverage_failed_since",
            "enrollment_open",
        ]
    )
    CoverageObservation.objects.create(
        pathway=pathway, observed_at=now, healthy=report["healthy"], report=report
    )


@transaction.atomic
def _apply_topic(topic, *, rules, feeds):
    catalogue = Catalogue.objects.filter(slug=topic["slug"]).first()
    if catalogue:
        catalogue = Catalogue.objects.select_for_update().get(pk=catalogue.pk)
    now = timezone.now()
    resources = eligible_resources(rules=rules, feeds=feeds, now=now)
    report, selected = topic_coverage(topic, resources)
    current = (
        catalogue.versions.filter(status="published").first() if catalogue else None
    )
    # Observe current resources independently of a changed candidate definition.
    if current and current.discovery_managed:
        old_report = bound_coverage(current, rules=rules, feeds=feeds, now=now)
        _record_coverage(current, old_report, now)
    if not report["healthy"]:
        return dict(slug=topic["slug"], action="blocked", coverage=report)
    key = publication_key(topic, selected)
    if current and current.discovery_managed and current.publication_key == key:
        return dict(slug=topic["slug"], action="reused", coverage=report)
    if current and not current.is_demo and not current.discovery_managed:
        raise ValidationError("Discovery cannot replace an unmanaged live curriculum.")
    if catalogue is None:
        catalogue, _ = Catalogue.objects.get_or_create(slug=topic["slug"])
        catalogue = Catalogue.objects.select_for_update().get(pk=catalogue.pk)
        if catalogue.versions.filter(status="published").exists():
            raise ValidationError("Catalogue changed during discovery; retry the run.")
    revision = create_revision(
        catalogue,
        title=topic["title"],
        description=topic["description"],
        target_outcome=topic["target_outcome"],
        steps=topic["steps"],
    )
    revision.discovery_managed = True
    revision.publication_key = key
    revision.save(update_fields=["discovery_managed", "publication_key"])
    for step, pool in zip(
        revision.steps.select_related("skill"), selected, strict=True
    ):
        for resource in pool:
            PathwayResource.objects.create(
                pathway_skill=step,
                item=resource.item,
                content_fingerprint=resource.fingerprint,
                evidence_snapshot=evidence_snapshot(resource, rules, feeds),
            )
            resource.item.skills.add(step.skill)
    # Permission/date eligibility is checked again at the activation boundary.
    checked_at = timezone.now()
    final = bound_coverage(revision, rules=rules, feeds=feeds, now=checked_at)
    if not final["healthy"]:
        raise ValidationError("Coverage changed before publication.")
    if current:
        current.status = "retired"
        current.enrollment_open = False
        current.save(update_fields=["status", "enrollment_open"])
    revision.status = "published"
    revision.enrollment_open = True
    revision.save(update_fields=["status", "enrollment_open"])
    _record_coverage(revision, final, checked_at)
    return dict(
        slug=topic["slug"], action="published", version=revision.version, coverage=final
    )


def bound_coverage(pathway, *, rules, feeds, now):
    pools = []
    for step in pathway.steps.all():
        pool = []
        seen = set()
        for link in step.resources.select_related(
            "item__source", "item__release_review"
        ):
            resource = eligible_resource(link.item, rules=rules, feeds=feeds, now=now)
            if (
                resource
                and resource.fingerprint == link.content_fingerprint
                and resource.canonical_url not in seen
            ):
                pool.append(resource)
                seen.add(resource.canonical_url)
        pools.append((step.skill_id, pool))
    counts = {str(skill): len(pool) for skill, pool in pools}
    publishers = sorted({r.publisher_key for _, pool in pools for r in pool})
    return dict(
        per_skill=counts,
        publisher_keys=publishers,
        healthy=3 <= len(pools) <= 8
        and all(c >= 3 for c in counts.values())
        and len(publishers) >= 2,
    )


@transaction.atomic
def discover_pathways(*, apply=False, rules=None, feeds=None):
    rules = load_rules() if rules is None else rules
    feeds = load_config() if feeds is None else feeds
    validate_rules(rules)
    results = []
    for topic in sorted(rules["topics"], key=lambda topic: topic["slug"]):
        if apply:
            results.append(_apply_topic(topic, rules=rules, feeds=feeds))
        else:
            report, _ = topic_coverage(
                topic, eligible_resources(rules=rules, feeds=feeds, now=timezone.now())
            )
            results.append(
                dict(
                    slug=topic["slug"],
                    action="eligible" if report["healthy"] else "blocked",
                    coverage=report,
                )
            )
    # A removed rule cannot leave a managed catalogue enrolling indefinitely.
    if apply:
        known = {topic["slug"] for topic in rules["topics"]}
        for pathway in Pathway.objects.filter(
            status="published", discovery_managed=True
        ).exclude(catalogue__slug__in=known):
            with transaction.atomic():
                _record_coverage(
                    pathway,
                    dict(healthy=False, reason="missing curriculum rule"),
                    timezone.now(),
                )
    return results


def reviewed_picks(pathway, skill, limit):
    try:
        rules, feeds = load_rules(), load_config()
        validate_rules(rules)
    except (ValidationError, ValueError, TypeError, KeyError, OSError):
        return []
    now = timezone.now()
    picked = []
    for link in (
        PathwayResource.objects.filter(
            pathway_skill__pathway=pathway, pathway_skill__skill=skill
        )
        .select_related("item__source", "item__release_review")
        .order_by("item_id")
    ):
        resource = eligible_resource(link.item, rules=rules, feeds=feeds, now=now)
        if resource and resource.fingerprint == link.content_fingerprint:
            picked.append(link.item)
    return sorted(
        picked, key=lambda item: (not item.is_low_data, item.title.casefold(), item.pk)
    )[:limit]
