from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from content.ingestion import feed_staleness, safe_http_link
from content.matching import load_config, source_for_url
from content.models import Item
from learners.models import LearnerProfile
from opportunities.matching import match_score
from opportunities.models import Opportunity
from pathways.catalogue import catalogue_skill_ids, enrollable_pathways
from pathways.discovery import load_rules
from pathways.logic import (
    completed_items,
    progress_for,
    recommendations,
    reviewed_pathway_recommendations,
)
from pathways.models import Checkpoint, CheckpointRecord, ItemRecord


def item_json(item, done_ids=None, reference_date=None):
    if reference_date is None:
        reference_date = timezone.localdate()
    config = load_config()
    feed = source_for_url(item.source.url, config)
    stale = feed_staleness(item.source, feed or {}, reference_date, config)
    age_days = (
        (reference_date - item.published_at.date()).days
        if item.date_source in {"published", "updated"}
        else None
    )
    return {
        "id": item.pk,
        "title": item.title,
        "url": safe_http_link(item.url) or "",
        # Only publisher-cleared text is returned. Everything else is
        # published as title, publisher and date with a link to the original.
        "excerpt": item.excerpt,
        "published_at": item.published_at.isoformat(),
        "source": item.source.name,
        "skills": list(
            item.skills.filter(pk__in=catalogue_skill_ids())
            .order_by("pk")
            .values_list("name", flat=True)
        ),
        "estimated_minutes": item.estimated_minutes,
        "is_low_data": item.is_low_data,
        "done": item.pk in (done_ids or set()),
        "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        "date_source": item.date_source,
        "age_days": age_days,
        "pathway_keys": item.pathway_keys,
        "content_date": (
            item.published_at.date().isoformat()
            if age_days is not None and age_days >= 0
            else None
        ),
        "source_url": safe_http_link(item.source.url) or "",
        # A reported licence string is not verified public-reuse permission.
        "source_reuse_verified": False,
        "source_attribution": item.source.attribution,
        "source_rights": item.source.rights,
        "source_stale": stale["stale"],
        "source_stale_reason": stale["reason"],
    }


def checkpoint_json(checkpoint):
    step = checkpoint.pathway_skill
    return {
        "id": checkpoint.pk,
        "title": checkpoint.title,
        "criteria": checkpoint.criteria,
        "unlocks_text": checkpoint.unlocks_text,
        "skill": step.skill.name,
        "skill_id": step.skill_id,
        "order": step.order,
        "quiz": [
            {"question": question["question"], "options": question["options"]}
            for question in checkpoint.quiz_json
        ],
    }


def pathway_picks(learner, skill, limit):
    if learner.chosen_pathway and learner.chosen_pathway.is_demo:
        return recommendations(skill, limit)
    picks = list(reviewed_pathway_recommendations(learner.chosen_pathway, skill, limit))
    # A curated pathway publishes links the owner checked by hand. They are
    # the reading list for the step, and they come first.
    curated = curated_picks(learner, skill, limit)
    return curated + picks[: max(0, limit - len(curated))]


def curated_picks(learner, skill, limit):
    """Return the curated reading links for a step of the chosen pathway.

    A curated pathway publishes links an owner checked by hand, so they
    are not stored reading material and carry their own review evidence.
    """
    pathway = learner.chosen_pathway
    if pathway is None:
        return []
    from pathways.curated import curated_links

    links = []
    for step in pathway.steps.filter(skill=skill):
        links.extend(curated_links(step))
    return links[:limit]


def reading_key(reading):
    """A unique key for a reading, so feed items and curated links never collide."""
    if isinstance(reading, Item):
        return f"item-{reading.pk}"
    return f"curated-{reading.pk}"


def reading_json(reading, done_ids=None):
    """Serialize a feed item or a curated link for the learner.

    A curated link is published as its title, its publisher and its
    address, with the review that cleared it. No publisher text is
    reproduced, so there is no excerpt to return.
    """
    if isinstance(reading, Item):
        return item_json(reading, done_ids)
    return curated_json(reading)


def curated_json(link):
    return {
        "id": f"curated-{link.pk}",
        "kind": "curated",
        "title": link.title,
        "url": link.url,
        "publisher": link.publisher,
        "rationale": link.rationale,
        "reviewed_on": link.reviewed_on.isoformat(),
        "expires_on": link.expires_on.isoformat(),
        "evidence_url": link.evidence_url,
    }


def current_learner(request):
    if request.user.is_authenticated:
        return LearnerProfile.objects.filter(owner=request.user).first()
    learner_id = request.session.get("learner_id")
    return (
        LearnerProfile.objects.filter(pk=learner_id, owner__isnull=True).first()
        if learner_id
        else None
    )


def learner_required(request):
    learner = current_learner(request)
    if learner is None:
        return None, Response({"detail": "Complete onboarding first."}, status=401)
    return learner, None


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "soma.i"})


@api_view(["GET"])
def pathways_list(request):
    pathways = enrollable_pathways()
    paginated = "page" in request.query_params
    if paginated:
        try:
            page = int(request.query_params["page"])
        except (ValueError, TypeError):
            return Response({"detail": "Page must be a positive integer."}, status=400)
        if not 1 <= page <= 1000000:
            return Response(
                {"detail": "Page must be between 1 and 1000000."}, status=400
            )
        query = request.query_params.get("q", "").strip()
        if len(query) > 120:
            return Response(
                {"detail": "Search is limited to 120 characters."}, status=400
            )
        if query:
            pathways = pathways.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(target_outcome__icontains=query)
                | Q(steps__skill__name__icontains=query)
            ).distinct()
        count = pathways.count()
        pathways = pathways[(page - 1) * 12 : page * 12]
    results = [
        {
            "id": p.pk,
            "title": p.title,
            "description": p.description,
            "target_outcome": p.target_outcome,
            "locale": p.locale,
            **({"is_demo": p.is_demo, "version": p.version} if paginated else {}),
        }
        for p in pathways
    ]
    if paginated:
        return Response(
            {
                "results": results,
                "count": count,
                "page": page,
                "page_size": 12,
                "has_next": page * 12 < count,
            }
        )
    return Response(results)


@api_view(["GET"])
def roadmaps_list(request):
    try:
        page = int(request.query_params.get("page", "1"))
    except (ValueError, TypeError):
        return Response({"detail": "Page must be a positive integer."}, status=400)
    if not 1 <= page <= 1000000:
        return Response({"detail": "Page must be between 1 and 1000000."}, status=400)
    query = request.query_params.get("q", "").strip()
    if len(query) > 120:
        return Response({"detail": "Search is limited to 120 characters."}, status=400)
    enrollable_by_slug = {
        pathway.catalogue.slug: pathway
        for pathway in enrollable_pathways().select_related("catalogue")
        if pathway.catalogue_id
    }
    roadmaps = []
    for topic in load_rules()["topics"]:
        if query:
            fields = [
                topic["title"],
                topic["description"],
                topic["target_outcome"],
                *topic["aliases"],
                *(step["skill"] for step in topic["steps"]),
            ]
            folded = query.casefold()
            if not any(folded in field.casefold() for field in fields):
                continue
        pathway = enrollable_by_slug.get(topic["slug"])
        roadmaps.append(
            {
                "slug": topic["slug"],
                "title": topic["title"],
                "description": topic["description"],
                "target_outcome": topic["target_outcome"],
                "available_pathway_id": pathway.pk if pathway else None,
                "available": pathway is not None,
                "is_demo": bool(pathway and pathway.is_demo),
                "version": pathway.version if pathway else None,
                "image": topic.get("image", {}),
                "steps": [
                    {
                        "skill": step["skill"],
                        "title": step["title"],
                        "criteria": step["criteria"],
                        "requires": step["requires"],
                    }
                    for step in topic["steps"]
                ],
            }
        )
    count = len(roadmaps)
    paged = roadmaps[(page - 1) * 12 : page * 12]
    return Response(
        {
            "results": paged,
            "count": count,
            "page": page,
            "page_size": 12,
            "has_next": page * 12 < count,
        }
    )


@api_view(["POST"])
def demo_session(request):
    if (
        settings.SOMA_ENV not in {"development", "test"}
        or request.user.is_authenticated
    ):
        return Response({"detail": "Demo session unavailable."}, status=404)
    learner = (
        LearnerProfile.objects.filter(display_name="Amina Demo")
        .select_related("chosen_pathway")
        .first()
    )
    if learner is None:
        return Response({"detail": "Run seed_demo first."}, status=404)
    request.session["learner_id"] = learner.pk
    request.session["demo_session"] = True
    request.session.cycle_key()
    request.session.save()
    return Response(
        {
            "display_name": learner.display_name,
            "chosen_pathway": learner.chosen_pathway_id,
        }
    )


@api_view(["POST", "GET", "PATCH", "DELETE"])
def me(request):
    if request.method == "POST":
        pathway = get_object_or_404(
            enrollable_pathways(), pk=request.data.get("pathway_id")
        )
        language = request.data.get("preferred_language", "en")
        if language not in ("en", "sw"):
            return Response({"detail": "Language must be en or sw."}, status=400)
        learner = current_learner(request)
        if learner is None:
            learner = LearnerProfile.objects.create(
                owner=request.user if request.user.is_authenticated else None
            )
            request.session.cycle_key()
        learner.display_name = (
            request.data.get("display_name") or learner.display_name or "Learner"
        )[:80]
        learner.preferred_language = language
        learner.chosen_pathway = pathway
        learner.save(
            update_fields=["display_name", "preferred_language", "chosen_pathway"]
        )
        request.session["learner_id"] = learner.pk
        request.session.save()
    else:
        learner, error = learner_required(request)
        if error:
            return error
        if request.method == "DELETE":
            if request.user.is_authenticated:
                return Response(
                    {"detail": "Use account deletion with password confirmation."},
                    status=400,
                )
            learner.delete()
            request.session.flush()
            return Response({"deleted": True})
        if request.method == "PATCH":
            if "preferred_language" in request.data:
                language = request.data["preferred_language"]
                if language not in ("en", "sw"):
                    return Response(
                        {"detail": "Language must be en or sw."}, status=400
                    )
                learner.preferred_language = language
            if "phone" in request.data:
                learner.phone = str(request.data["phone"])[:30]
            if "reminder_opt_in" in request.data:
                learner.reminder_opt_in = bool(request.data["reminder_opt_in"])
            learner.save()
    return Response(
        {
            "id": learner.pk,
            "display_name": learner.display_name,
            "preferred_language": learner.preferred_language,
            "phone": learner.phone,
            "reminder_opt_in": learner.reminder_opt_in,
            "reminder_frequency": learner.reminder_frequency,
            "chosen_pathway": learner.chosen_pathway_id,
        },
        status=201 if request.method == "POST" else 200,
    )


@api_view(["GET"])
def dashboard(request):
    learner, error = learner_required(request)
    if error:
        return error
    state = progress_for(learner)
    done_ids = completed_items(learner)
    picks_by_skill = [pathway_picks(learner, skill, 3) for skill in state["remaining"]]
    recommended = []
    for index in range(max((len(items) for items in picks_by_skill), default=0)):
        recommended.extend(
            items[index] for items in picks_by_skill if index < len(items)
        )
    seen = set()
    recommended = [
        item
        for item in recommended
        if not (reading_key(item) in seen or seen.add(reading_key(item)))
    ][:8]
    steps = []
    if state["pathway"]:
        for step in state["pathway"].steps.select_related("skill", "checkpoint").all():
            record = CheckpointRecord.objects.filter(
                learner=learner, checkpoint=step.checkpoint
            ).first()
            steps.append(
                {
                    "skill": step.skill.name,
                    "checkpoint": step.checkpoint.title,
                    "status": record.status if record else "remaining",
                }
            )
    return Response(
        {
            "pathway": (
                {
                    "id": state["pathway"].pk,
                    "title": state["pathway"].title,
                    "target_outcome": state["pathway"].target_outcome,
                }
                if state["pathway"]
                else None
            ),
            "done": [skill.name for skill in state["done"]],
            "remaining": [skill.name for skill in state["remaining"]],
            "progress_percent": state["percent"],
            "steps": steps,
            "next_checkpoint": (
                checkpoint_json(state["next_checkpoint"])
                if state["next_checkpoint"]
                else None
            ),
            "items": [reading_json(item, done_ids) for item in recommended],
        }
    )


@api_view(["GET"])
def items_list(request):
    learner, error = learner_required(request)
    if error:
        return error
    state = progress_for(learner)
    done_ids = completed_items(learner)
    items, seen = [], set()
    for skill in state["remaining"]:
        for item in pathway_picks(learner, skill, 10):
            key = reading_key(item)
            if key not in seen:
                items.append(item)
                seen.add(key)
    return Response([reading_json(item, done_ids) for item in items[:40]])


@api_view(["POST"])
def item_done(request, item_id):
    learner, error = learner_required(request)
    if error:
        return error
    item = get_object_or_404(Item, pk=item_id)
    ItemRecord.objects.get_or_create(learner=learner, item=item)
    return Response({"done": True, "item_id": item.pk})


@api_view(["POST"])
def checkpoint_action(request, checkpoint_id, action):
    learner, error = learner_required(request)
    if error:
        return error
    checkpoint = get_object_or_404(
        Checkpoint, pk=checkpoint_id, pathway_skill__pathway=learner.chosen_pathway
    )
    if action not in ("complete", "skip"):
        return Response({"detail": "Unknown checkpoint action."}, status=404)
    if action == "complete" and not request.data.get("self_attested"):
        return Response(
            {"detail": "Confirm the checkpoint criteria before completing."}, status=400
        )
    answers = request.data.get("quiz_answers", {}) if action == "complete" else {}
    if action == "complete" and (
        not isinstance(answers, list) or len(answers) != len(checkpoint.quiz_json)
    ):
        return Response({"detail": "Answer all three check-in questions."}, status=400)
    status = "done" if action == "complete" else "skipped"
    CheckpointRecord.objects.update_or_create(
        learner=learner,
        checkpoint=checkpoint,
        defaults={
            "status": status,
            "self_attested": action == "complete",
            "quiz_answers": answers,
        },
    )
    if action == "skip":
        return Response({"skipped": True, "checkpoint_id": checkpoint.pk})
    return Response(what_next(learner, checkpoint))


@api_view(["GET"])
def next_step(request):
    learner = current_learner(request)
    if learner is None:
        return Response({"available": False, "reason": "no_learner"})
    if learner.chosen_pathway is None:
        return Response({"available": False, "reason": "no_pathway"})
    latest = (
        CheckpointRecord.objects.filter(
            learner=learner,
            status="done",
            checkpoint__pathway_skill__pathway=learner.chosen_pathway,
        )
        .select_related("checkpoint__pathway_skill__skill")
        .order_by("-checkpoint__pathway_skill__order")
        .first()
    )
    if latest is None:
        return Response({"available": False, "reason": "no_checkpoint"})
    return Response(what_next(learner, latest.checkpoint))


def what_next(learner, checkpoint):
    unlocked = checkpoint.pathway_skill.skill
    state = progress_for(learner)
    recommended = []
    seen_items = set()
    for skill in state["remaining"]:
        for item in pathway_picks(learner, skill, 3):
            key = reading_key(item)
            if key not in seen_items:
                recommended.append(item)
                seen_items.add(key)
            if len(recommended) == 3:
                break
        if len(recommended) == 3:
            break
    if len(recommended) < 2:
        for item in pathway_picks(learner, unlocked, 3):
            key = reading_key(item)
            if key not in seen_items:
                recommended.append(item)
                seen_items.add(key)
            if len(recommended) == 3:
                break
    matched = []
    for opportunity in Opportunity.objects.prefetch_related("skills").all():
        score = match_score(unlocked, opportunity)
        if score:
            matched.append((score, opportunity))
    matched.sort(key=lambda pair: (-pair[0], pair[1].title))
    return {
        "unlocked_skill": unlocked.name,
        "unlocks_text": checkpoint.unlocks_text,
        "next_checkpoint": (
            checkpoint_json(state["next_checkpoint"])
            if state["next_checkpoint"]
            else None
        ),
        "items": [
            reading_json(item, completed_items(learner)) for item in recommended
        ],
        "opportunities": [
            {
                "id": op.pk,
                "title": op.title,
                "type": op.type,
                "provider": op.provider,
                "url": op.url,
                "location": op.location,
                "deadline": op.deadline.isoformat() if op.deadline else None,
                "match_percent": score,
                "sample": True,
            }
            for score, op in matched[:5]
        ],
    }


@api_view(["POST"])
def pathway_action(request, action):
    learner, error = learner_required(request)
    if error:
        return error
    if action == "switch":
        learner.chosen_pathway = get_object_or_404(
            enrollable_pathways(), pk=request.data.get("pathway_id")
        )
        learner.save(update_fields=["chosen_pathway"])
        return Response({"pathway_id": learner.chosen_pathway_id})
    if action == "restart":
        CheckpointRecord.objects.filter(
            learner=learner, checkpoint__pathway_skill__pathway=learner.chosen_pathway
        ).delete()
        ItemRecord.objects.filter(
            learner=learner, item__skills__pathways=learner.chosen_pathway
        ).delete()
        return Response({"restarted": True})
    if action == "skip":
        current = progress_for(learner)["next_checkpoint"]
        if current is None:
            return Response({"skipped": False, "detail": "No remaining checkpoint."})
        CheckpointRecord.objects.update_or_create(
            learner=learner,
            checkpoint=current,
            defaults={"status": "skipped", "self_attested": False, "quiz_answers": {}},
        )
        return Response({"skipped": True, "checkpoint_id": current.pk})
    return Response({"detail": "Unknown action."}, status=404)


@api_view(["GET"])
def opportunities_list(request):
    learner, error = learner_required(request)
    if error:
        return error
    skill_id = request.query_params.get("skill")
    skill = (
        learner.chosen_pathway.steps.first().skill
        if learner.chosen_pathway and learner.chosen_pathway.steps.exists()
        else None
    )
    if skill_id:
        from content.models import Skill

        skill = Skill.objects.filter(pk=skill_id).first()
    results = []
    for opportunity in Opportunity.objects.prefetch_related("skills"):
        score = match_score(skill, opportunity) if skill else 0
        results.append(
            {
                "id": opportunity.pk,
                "title": opportunity.title,
                "type": opportunity.type,
                "provider": opportunity.provider,
                "url": opportunity.url,
                "location": opportunity.location,
                "deadline": (
                    opportunity.deadline.isoformat() if opportunity.deadline else None
                ),
                "match_percent": score,
                "sample": True,
            }
        )
    return Response(sorted(results, key=lambda op: (-op["match_percent"], op["title"])))
