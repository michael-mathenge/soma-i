"""Publish a curated curriculum from hand-checked reading links.

A curated curriculum is a pathway whose reading list an owner checked by
hand, one link at a time. It exists because the automatic route needs two
independent publishers whose reuse permission is verified, and a small
learning site often has one publisher with generous terms rather than two
with narrow ones.

The rules are deliberately strict even though the owner selects the links:

- Every link is reviewed, dated and expires. A stale review removes the
  link from the published revision.
- A link is published as its title, its publisher and its address. No
  publisher text is reproduced, so the review records the publisher's own
  terms page rather than a republication permission.
- A step needs at least three links and a topic needs at least two
  independent publishers, so no single publisher can carry a curriculum.
- Publication creates a new revision. A published curriculum is frozen, so
  a later change creates a new version and leaves the old one intact for
  the learners who selected it.
"""

import json
from datetime import date
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from content.fetching import validate_feed_url
from pathways.catalogue import create_revision, validate_steps
from pathways.discovery import digest
from pathways.models import Catalogue, CuratedResource, Pathway

# A step needs enough reading to be a course rather than a pointer.
MINIMUM_LINKS_PER_STEP = 3
# A topic needs more than one publisher, so no single site carries it.
MINIMUM_PUBLISHERS_PER_TOPIC = 2
# A review is refreshed at least this often, and never runs longer.
MAXIMUM_REVIEW_DAYS = 90


def load_curated_file(path):
    """Read a curated curricula file and return its topics."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValidationError(f"Curated curricula file could not be read: {exc}")
    topics = document.get("topics") if isinstance(document, dict) else document
    if not isinstance(topics, dict) or not topics:
        raise ValidationError("The curated curricula file must list its topics.")
    return topics


def _publisher_host(url):
    from urllib.parse import urlsplit

    return (urlsplit(url).hostname or "").lower()


def validate_curated_topics(topics, rules, today):
    """Check every link before anything is written.

    The check is fail-closed. A curriculum that would publish with a stale
    review, a link with no evidence, a step with too few links or a topic
    carried by one publisher is rejected rather than published in part.
    """
    for slug, steps in topics.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ValidationError("A curated topic needs a slug.")
        if not isinstance(steps, dict) or not steps:
            raise ValidationError(f"Curated topic {slug} needs its steps.")
        publishers = set()
        for skill, links in steps.items():
            if not isinstance(links, list) or len(links) < MINIMUM_LINKS_PER_STEP:
                raise ValidationError(
                    f"Curated topic {slug} step {skill} needs at least "
                    f"{MINIMUM_LINKS_PER_STEP} links."
                )
            for link in links:
                _validate_link(slug, skill, link, today)
                publishers.add(_publisher_host(link["url"]))
        if len(publishers) < MINIMUM_PUBLISHERS_PER_TOPIC:
            raise ValidationError(
                f"Curated topic {slug} needs links from at least "
                f"{MINIMUM_PUBLISHERS_PER_TOPIC} independent publishers."
            )
    return topics


def _validate_link(slug, skill, link, today):
    if not isinstance(link, dict):
        raise ValidationError(f"Curated link for {slug} {skill} is not an object.")
    for field in ("title", "url", "publisher", "evidence_url", "reviewed_by"):
        value = link.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                f"Curated link for {slug} {skill} is missing {field}."
            )
    for field in ("url", "evidence_url"):
        try:
            validate_feed_url(link[field])
        except ValueError as exc:
            raise ValidationError(
                f"Curated link for {slug} {skill} has an invalid {field}: {exc}"
            )
    try:
        reviewed_on = date.fromisoformat(str(link["reviewed_on"]))
        expires_on = date.fromisoformat(str(link["expires_on"]))
    except (KeyError, ValueError) as exc:
        raise ValidationError(
            f"Curated link for {slug} {skill} has invalid review dates: {exc}"
        )
    if not reviewed_on <= today <= expires_on:
        raise ValidationError(
            f"Curated link for {slug} {skill} is not current. The review must "
            f"start on or before {today} and end on or after it."
        )
    if (expires_on - reviewed_on).days > MAXIMUM_REVIEW_DAYS:
        raise ValidationError(
            f"Curated link for {slug} {skill} lasts longer than "
            f"{MAXIMUM_REVIEW_DAYS} days."
        )


def curated_publication_key(topic, steps):
    """A stable key for the curriculum, so an unchanged file is not republished.

    The key covers every field a learner sees, so a changed title or
    rationale republishes rather than being silently kept.
    """
    return digest(
        dict(
            topic=topic,
            steps={
                skill: [
                    [
                        link["url"],
                        link["title"],
                        link["publisher"],
                        link["rationale"] if "rationale" in link else "",
                        link["reviewed_by"],
                        link["expires_on"],
                    ]
                    for link in links
                ]
                for skill, links in steps.items()
            },
        )
    )


@transaction.atomic
def publish_curated_topic(topic, steps, *, today=None):
    """Publish one curated topic as a new pathway revision.

    A published revision is frozen, so a change creates a new version and
    retires the old one. Learners who selected the old revision keep it.
    """
    from pathways.discovery import load_rules

    if today is None:
        today = timezone.localdate()
    rules = load_rules()
    validate_curated_topics({topic: steps}, rules, today)

    catalogue, _ = Catalogue.objects.get_or_create(slug=topic)
    Catalogue.objects.select_for_update().get(pk=catalogue.pk)
    existing = catalogue.versions.filter(status="published").first()
    key = curated_publication_key(topic, steps)
    if existing and existing.publication_key == key:
        return dict(slug=topic, action="unchanged", version=existing.version)

    pathway = create_revision(
        catalogue,
        title=topic,
        description=steps_description(topic, steps),
        target_outcome=steps_target_outcome(topic, steps),
        steps=steps_from_curated(topic, steps),
    )
    pathway.publication_key = key
    pathway.is_curated = True
    pathway.save(update_fields=["publication_key", "is_curated"])

    ordered_steps = list(pathway.steps.select_related("skill").order_by("order"))
    by_skill = {step.skill.name: step for step in ordered_steps}
    for skill, links in steps.items():
        step = by_skill.get(skill)
        if step is None:
            raise ValidationError(f"Curated topic {topic} has no step for {skill}.")
        for order, link in enumerate(links, 1):
            CuratedResource.objects.create(
                pathway_skill=step,
                title=link["title"],
                url=link["url"],
                publisher=link["publisher"],
                evidence_url=link["evidence_url"],
                reviewed_by=link["reviewed_by"],
                reviewed_on=date.fromisoformat(str(link["reviewed_on"])),
                expires_on=date.fromisoformat(str(link["expires_on"])),
                order=order,
                rationale=str(link.get("rationale", "")),
            )

    if existing:
        existing.status = "retired"
        existing.enrollment_open = False
        existing.save(update_fields=["status", "enrollment_open"])
    pathway.status = "published"
    pathway.enrollment_open = True
    pathway.save(update_fields=["status", "enrollment_open"])
    return dict(slug=topic, action="published", version=pathway.version)


def steps_from_curated(topic, steps):
    """Build the pathway steps for a curated topic.

    The curated file supplies the reading links. The curriculum itself,
    the checkpoint criteria and the check-in questions, come from the
    reviewed discovery rules, so a curated topic is not a thin list of
    links but the same learning sequence as every other pathway.
    """
    from pathways.discovery import load_rules

    rules = load_rules()
    definition = None
    for candidate in rules["topics"]:
        if candidate["slug"] == topic:
            definition = candidate
            break
    if definition is None:
        raise ValidationError(f"Curated topic {topic} is not in the review rules.")
    validate_steps(definition["steps"])
    return definition["steps"]


def steps_description(topic, steps):
    from pathways.discovery import load_rules

    for candidate in load_rules()["topics"]:
        if candidate["slug"] == topic:
            return candidate["description"]
    raise ValidationError(f"Curated topic {topic} is not in the review rules.")


def steps_target_outcome(topic, steps):
    from pathways.discovery import load_rules

    for candidate in load_rules()["topics"]:
        if candidate["slug"] == topic:
            return candidate["target_outcome"]
    raise ValidationError(f"Curated topic {topic} is not in the review rules.")


def curated_links(pathway_skill, today=None):
    """Return the current curated links for a step.

    A link whose review has expired is not returned. The review window is
    what keeps a curated curriculum honest over time.
    """
    if today is None:
        today = timezone.localdate()
    return list(
        CuratedResource.objects.filter(
            pathway_skill=pathway_skill,
            reviewed_on__lte=today,
            expires_on__gte=today,
        ).order_by("order", "pk")
    )
