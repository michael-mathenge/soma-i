"""Catalogue operations. Live coverage approval is implemented by pathways.discovery.

Pathway IDs remain revision IDs, so chosen_pathway and checkpoint records need
no reassignment. Supported writes use ordinary saves; bulk mutations are blocked.
Raw SQL can bypass model safeguards and is not a publication interface.
"""

from copy import deepcopy
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.text import slugify

from content.models import Skill
from pathways.models import Catalogue, Checkpoint, Pathway, PathwaySkill


def enrollable_pathways():
    return (
        Pathway.objects.filter(
            catalogue__isnull=False,
            status="published",
            enrollment_open=True,
        )
        .filter(
            Q(is_demo=True)
            | Q(
                discovery_managed=True,
                coverage_checked_at__gte=timezone.now() - timedelta(days=1),
                coverage_checked_at__lte=timezone.now(),
            )
            # A curated pathway publishes links the owner checked by hand.
            | Q(is_curated=True)
        )
        .order_by("catalogue_id", "pk")
    )


def catalogue_skill_ids():
    return PathwaySkill.objects.filter(
        pathway__catalogue__isnull=False,
        pathway__status__in=["published", "retired"],
    ).values_list("skill_id", flat=True)


def validate_steps(steps):
    if not isinstance(steps, list) or not 3 <= len(steps) <= 8:
        raise ValidationError("A curriculum needs 3-8 ordered skills.")
    names = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValidationError("Each step needs skill and original checkpoint data.")
        for field in ("skill", "title", "criteria", "unlocks_text"):
            if not isinstance(step.get(field), str) or not step[field].strip():
                raise ValidationError(f"Missing step {field}.")
        if len(step["skill"]) > 80 or len(step["title"]) > 160:
            raise ValidationError("Skill or checkpoint title exceeds its field limit.")
        quiz = step.get("quiz_json")
        if not isinstance(quiz, list) or len(quiz) != 3:
            raise ValidationError("Each checkpoint needs three check-in questions.")
        for question in quiz:
            if (
                not isinstance(question, dict)
                or not isinstance(question.get("question"), str)
                or not question["question"].strip()
            ):
                raise ValidationError("Each check-in needs a question.")
            options = question.get("options")
            answer = question.get("answer")
            if (
                not isinstance(options, list)
                or len(options) < 2
                or any(
                    not isinstance(option, str) or not option.strip()
                    for option in options
                )
                or type(answer) is not int
                or not 0 <= answer < len(options)
            ):
                raise ValidationError("Invalid check-in options or answer.")
        names.append(step["skill"])
    if len(set(names)) != len(names):
        raise ValidationError("A curriculum cannot repeat a skill.")


@transaction.atomic
def create_revision(
    catalogue, *, title, description, target_outcome, steps, locale="KE", is_demo=False
):
    """Create a fresh draft; never change previous curriculum or enroll learners."""
    validate_steps(steps)
    catalogue = Catalogue.objects.select_for_update().get(pk=catalogue.pk)
    version = (catalogue.versions.aggregate(latest=Max("version"))["latest"] or 0) + 1
    pathway = Pathway(
        catalogue=catalogue,
        version=version,
        title=title,
        description=description,
        target_outcome=target_outcome,
        locale=locale,
        is_demo=is_demo,
    )
    pathway.full_clean()
    pathway.save()
    for order, data in enumerate(steps, 1):
        slug = slugify(data["skill"])
        if not slug:
            raise ValidationError("Skill needs a usable slug.")
        skill = Skill.objects.filter(name=data["skill"]).first()
        if skill is None:
            skill = Skill(name=data["skill"], slug=slug)
            skill.full_clean()
            skill.save()
        step = PathwaySkill.objects.create(pathway=pathway, skill=skill, order=order)
        Checkpoint.objects.create(
            pathway_skill=step,
            title=data["title"],
            criteria=data["criteria"],
            unlocks_text=data["unlocks_text"],
            quiz_json=deepcopy(data["quiz_json"]),
        )
    return pathway


@transaction.atomic
def publish_demo_revision(pathway):
    """Offline demo publication only; this is never source-rights clearance."""
    Catalogue.objects.select_for_update().get(pk=pathway.catalogue_id)
    pathway = Pathway.objects.select_for_update().get(pk=pathway.pk)
    if not pathway.is_demo or pathway.status != "draft":
        raise ValidationError("Only a draft demo revision can use demo publication.")
    steps = list(pathway.steps.select_related("skill", "checkpoint"))
    validate_steps(
        [
            dict(
                skill=step.skill.name,
                title=step.checkpoint.title,
                criteria=step.checkpoint.criteria,
                unlocks_text=step.checkpoint.unlocks_text,
                quiz_json=step.checkpoint.quiz_json,
            )
            for step in steps
        ]
    )
    if [step.order for step in steps] != list(range(1, len(steps) + 1)):
        raise ValidationError("Curriculum order must be contiguous from one.")
    # Retire rather than rewrite the previous version; learners retain its ID.
    previous = pathway.catalogue.versions.filter(status="published").first()
    if previous and not previous.is_demo:
        raise ValidationError("Demo publication cannot retire a non-demo version.")
    if previous:
        previous.status = "retired"
        previous.enrollment_open = False
        previous.save(update_fields=["status", "enrollment_open"])
    pathway.status = "published"
    pathway.enrollment_open = True
    pathway.save(update_fields=["status", "enrollment_open"])
    return pathway


@transaction.atomic
def ensure_demo_pathway(config, quiz):
    """Idempotent demo setup; never overwrite a registered curriculum revision."""
    catalogue, _ = Catalogue.objects.get_or_create(slug=slugify(config["title"]))
    Catalogue.objects.select_for_update().get(pk=catalogue.pk)
    existing = catalogue.versions.filter(status="published").first()
    if not existing and catalogue.versions.exists():
        raise ValidationError(
            "Demo seeding cannot reopen retired or unpublished history."
        )
    if existing:
        if not existing.is_demo:
            raise ValidationError("Demo seeding cannot modify a non-demo catalogue.")
        return existing
    # Preserve the lowest matching legacy row and all later duplicates.
    legacy = (
        Pathway.objects.filter(
            title=config["title"],
            catalogue__isnull=True,
        )
        .order_by("pk")
        .first()
    )
    if legacy and legacy.steps.exists():
        for step in legacy.steps.select_related("skill"):
            if not Checkpoint.objects.filter(pathway_skill=step).exists():
                Checkpoint.objects.create(
                    pathway_skill=step,
                    title=f"{step.skill.name} checkpoint",
                    criteria=f"Complete a short practice task using {step.skill.name} and reflect on what you learned.",
                    unlocks_text=f"You can now use {step.skill.name} as part of your {config['target_outcome']} journey.",
                    quiz_json=deepcopy(quiz),
                )
        legacy.catalogue = catalogue
        legacy.is_demo = True
        legacy.save(update_fields=["catalogue", "is_demo"])
        # Grandfather historical demo curricula without rewriting quizzes/steps.
        # Like the migration, this is not validation for public-beta publication.
        legacy.status = "published"
        legacy.enrollment_open = True
        legacy.save(update_fields=["status", "enrollment_open"])
        return legacy
    steps = [
        dict(
            skill=name,
            title=f"{name} checkpoint",
            criteria=f"Complete a short practice task using {name} and reflect on what you learned.",
            unlocks_text=f"You can now use {name} as part of your {config['target_outcome']} journey.",
            quiz_json=quiz,
        )
        for name in config["skills"]
    ]
    if legacy:
        # An empty legacy row still retains its ID and profile references.
        legacy.catalogue = catalogue
        legacy.is_demo = True
        legacy.save(update_fields=["catalogue", "is_demo"])
        for order, data in enumerate(steps, 1):
            skill = Skill.objects.get(name=data["skill"])
            step = PathwaySkill.objects.create(pathway=legacy, skill=skill, order=order)
            Checkpoint.objects.create(
                pathway_skill=step, **{k: v for k, v in data.items() if k != "skill"}
            )
        return publish_demo_revision(legacy)
    revision = create_revision(
        catalogue,
        title=config["title"],
        description=config["description"],
        target_outcome=config["target_outcome"],
        steps=steps,
        is_demo=True,
    )
    return publish_demo_revision(revision)
