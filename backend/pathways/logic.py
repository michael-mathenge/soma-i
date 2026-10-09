from content.matching import load_config, ranking_key, source_for_url
from content.models import Item
from pathways.models import CheckpointRecord, ItemRecord


def progress_for(learner):
    pathway = learner.chosen_pathway
    steps = (
        list(pathway.steps.select_related("skill", "checkpoint").all())
        if pathway
        else []
    )
    done = (
        set(
            CheckpointRecord.objects.filter(
                learner=learner,
                status="done",
                checkpoint__pathway_skill__pathway=pathway,
            ).values_list("checkpoint__pathway_skill__skill_id", flat=True)
        )
        if pathway
        else set()
    )
    remaining = [step for step in steps if step.skill_id not in done]
    skipped_ids = (
        set(
            CheckpointRecord.objects.filter(
                learner=learner,
                status="skipped",
                checkpoint__pathway_skill__pathway=pathway,
            ).values_list("checkpoint_id", flat=True)
        )
        if pathway
        else set()
    )
    next_step = next(
        (step for step in remaining if step.checkpoint.pk not in skipped_ids), None
    )
    return {
        "pathway": pathway,
        "done": [step.skill for step in steps if step.skill_id in done],
        "remaining": [step.skill for step in remaining],
        "percent": round(len(done) * 100 / len(steps)) if steps else 0,
        "next_checkpoint": next_step.checkpoint if next_step else None,
    }


def recommendations(skill, limit=5):
    items = list(Item.objects.filter(skills=skill).select_related("source").distinct())
    items.sort(key=lambda item: (not item.is_low_data, item.title.lower()))

    config = load_config()
    fixture_slots = [
        index
        for index, item in enumerate(items)
        if source_for_url(item.source.url, config) is not None
    ]
    ranked_fixtures = sorted(
        (items[index] for index in fixture_slots),
        key=lambda item: (
            not item.is_low_data,
            ranking_key(
                item,
                source_for_url(item.source.url, config)["source_type"],
                config,
            ),
        ),
    )
    for index, item in zip(fixture_slots, ranked_fixtures):
        items[index] = item
    return items[:limit]


def completed_items(learner):
    return set(
        ItemRecord.objects.filter(learner=learner).values_list("item_id", flat=True)
    )
