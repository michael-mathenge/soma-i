import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from content.models import Skill
from learners.models import LearnerProfile
from pathways.constants import CANONICAL_PATHWAYS
from pathways.models import Checkpoint, CheckpointRecord, Pathway, PathwaySkill

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    call_command("seed_demo", verbosity=0)
    return {path.title: path for path in Pathway.objects.all()}


def test_onboard_complete_checkpoint_and_get_whats_next(seeded):
    client = APIClient()
    pathway = seeded["Data Analyst"]
    response = client.post(
        "/api/me/",
        {
            "display_name": "Test learner",
            "preferred_language": "en",
            "pathway_id": pathway.pk,
        },
        format="json",
    )
    assert response.status_code == 201
    first = pathway.steps.select_related("checkpoint").first().checkpoint
    response = client.post(
        f"/api/checkpoints/{first.pk}/complete/",
        {"self_attested": True, "quiz_answers": [0, 0, 0]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["unlocked_skill"] == "Spreadsheets"
    assert response.data["next_checkpoint"]["skill"] == "SQL"
    assert len(response.data["items"]) in (2, 3)
    assert response.data["opportunities"]
    record = CheckpointRecord.objects.get(
        learner__display_name="Test learner", checkpoint=first
    )
    assert record.quiz_answers == [0, 0, 0]


def test_direct_next_returns_latest_checkpoint_opportunities(seeded):
    client = APIClient()
    client.post("/api/demo/")

    response = client.get("/api/next/")

    assert response.status_code == 200
    assert response.data["unlocked_skill"] == "Spreadsheets"
    assert response.data["next_checkpoint"]["skill"] == "SQL"
    assert response.data["opportunities"]
    assert all(opportunity["sample"] for opportunity in response.data["opportunities"])
    assert all(
        opportunity["match_percent"] > 0
        for opportunity in response.data["opportunities"]
    )


def test_direct_next_without_learner_returns_empty_state(seeded):
    response = APIClient().get("/api/next/")

    assert response.status_code == 200
    assert response.data == {"available": False, "reason": "no_learner"}


def test_direct_next_without_pathway_returns_empty_state():
    learner = LearnerProfile.objects.create(display_name="No pathway")
    client = APIClient()
    session = client.session
    session["learner_id"] = learner.pk
    session.save()

    response = client.get("/api/next/")

    assert response.status_code == 200
    assert response.data == {"available": False, "reason": "no_pathway"}


def test_seed_demo_is_repeatable_and_opts_amina_into_english_weekly_reminders():
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    pathway_titles = [pathway["title"] for pathway in CANONICAL_PATHWAYS]
    assert LearnerProfile.objects.filter(display_name="Amina Demo").count() == 1
    assert {
        title: Pathway.objects.filter(title=title).count() for title in pathway_titles
    } == {title: 1 for title in pathway_titles}

    amina = LearnerProfile.objects.get(display_name="Amina Demo")
    assert amina.chosen_pathway.title == "Data Analyst"
    assert amina.preferred_language == "en"
    assert amina.reminder_opt_in is True
    assert amina.reminder_frequency == "weekly"
    assert amina.phone == ""


def test_seed_demo_upgrades_old_seed_without_losing_amina_progress():
    old_pathways = {
        "Data Analyst": ["Spreadsheets", "SQL", "Data Visualisation", "Statistics"],
        "Web Developer": ["HTML", "CSS", "JavaScript", "Accessibility"],
        "Digital Marketing Assistant": [
            "Content Strategy",
            "Social Media",
            "SEO",
            "Marketing Analytics",
        ],
    }
    paths = {}
    first_checkpoint = None
    for title, names in old_pathways.items():
        pathway = Pathway.objects.create(
            title=title, description="Old seeded path", target_outcome=title
        )
        paths[title] = pathway
        for order, name in enumerate(names, start=1):
            skill, _ = Skill.objects.get_or_create(
                slug=name.lower().replace(" ", "-"), defaults={"name": name}
            )
            step = PathwaySkill.objects.create(
                pathway=pathway, skill=skill, order=order
            )
            checkpoint = Checkpoint.objects.create(
                pathway_skill=step,
                title=f"{name} checkpoint",
                criteria="Practice",
                unlocks_text="Next",
            )
            if title == "Data Analyst" and order == 1:
                first_checkpoint = checkpoint

    amina = LearnerProfile.objects.create(
        display_name="Amina Demo", chosen_pathway=paths["Data Analyst"]
    )
    progress = CheckpointRecord.objects.create(
        learner=amina,
        checkpoint=first_checkpoint,
        status="done",
        self_attested=True,
        quiz_answers={"demo": True},
    )

    call_command("seed_demo", verbosity=0)

    amina.refresh_from_db()
    progress.refresh_from_db()
    assert amina.chosen_pathway_id == paths["Data Analyst"].pk
    assert progress.checkpoint_id == first_checkpoint.pk
    assert progress.status == "done"
    assert Pathway.objects.filter(pk=paths["Digital Marketing Assistant"].pk).exists()
    frontend = Pathway.objects.get(pk=paths["Web Developer"].pk)
    assert frontend.title == CANONICAL_PATHWAYS[1]["title"]
    assert list(
        frontend.steps.order_by("order").values_list("skill__name", flat=True)
    ) == list(CANONICAL_PATHWAYS[1]["skills"])

    response = APIClient().get("/api/pathways/")
    assert response.status_code == 200
    assert [path["title"] for path in response.data] == [
        pathway["title"] for pathway in CANONICAL_PATHWAYS
    ]


def test_seed_demo_fixture_picks_are_offline_low_data_and_labeled():
    from datetime import UTC, datetime

    from content.models import Item

    call_command("seed_demo", verbosity=0)

    fixed_date = datetime(2026, 1, 1, tzinfo=UTC)
    data_item = Item.objects.get(
        url="https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content"
    )
    assert data_item.title == "Spreadsheet skills for clear data (demo)"
    assert data_item.published_at == fixed_date

    for pathway in CANONICAL_PATHWAYS[1:]:
        for skill_name in pathway["skills"]:
            minimum = 1 if skill_name in {"API Development", "Testing"} else 2
            picks = Item.objects.filter(
                skills__name=skill_name,
                is_low_data=True,
                title__endswith="(sample content)",
            ).distinct()
            assert (
                sum(pathway["title"] in item.pathway_keys for item in picks) >= minimum
            ), (
                f"{pathway['title']} / {skill_name} should have at least "
                f"{minimum} picks"
            )


def test_seed_demo_leaves_live_normalized_match_unchanged_and_adds_missing_skill():
    import json
    from datetime import UTC, datetime
    from pathlib import Path
    from urllib.parse import urlsplit, urlunsplit

    from content.ingestion import ingest_entries, normalize_link
    from content.matching import load_config
    from content.models import Item, Source

    config = load_config()
    feed = next(feed for feed in config["feeds"] if feed["key"] == "fcc_html")
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "content"
        / "tests"
        / "fixtures"
        / "feeds"
        / "fcc_html.json"
    )
    entry = json.loads(fixture_path.read_text(encoding="utf-8"))[0]
    original = urlsplit(entry["link"])
    entry_variant = {
        **entry,
        "link": urlunsplit(
            (
                "http",
                original.netloc,
                original.path.rstrip("/") + "/",
                "utm_source=legacy-seed-test",
                "",
            )
        ),
    }
    source = Source.objects.create(
        name=feed["name"],
        url=feed["url"],
        credibility_note="Test fixture source.",
        attribution=feed["attribution"],
        rights=feed.get("rights", "not stated"),
        level=feed.get("level", "mixed"),
    )
    ingest_entries(source, feed, [entry_variant], datetime(2025, 1, 1, tzinfo=UTC), config)
    live_item = Item.objects.get(normalized_link=normalize_link(entry["link"]))
    live_item.title = "Live title must stay unchanged"
    live_item.published_at = datetime(2020, 5, 4, tzinfo=UTC)
    live_item.is_low_data = False
    live_item.save(update_fields=["title", "published_at", "is_low_data"])
    live_item.skills.clear()
    original_fields = (
        live_item.title,
        live_item.published_at,
        live_item.is_low_data,
    )

    call_command("seed_demo", verbosity=0)
    live_item.refresh_from_db()
    first_seed_fields = (
        live_item.title,
        live_item.published_at,
        live_item.is_low_data,
    )
    assert first_seed_fields == original_fields
    assert live_item.skills.filter(name="HTML").exists()
    assert Item.objects.filter(normalized_link=normalize_link(entry["link"])).count() == 1

    call_command("seed_demo", verbosity=0)
    live_item.refresh_from_db()
    assert (
        live_item.title,
        live_item.published_at,
        live_item.is_low_data,
    ) == first_seed_fields
    assert live_item.skills.filter(name="HTML").exists()
    assert Item.objects.filter(normalized_link=normalize_link(entry["link"])).count() == 1


def test_fresh_fixture_seed_label_is_idempotent_and_live_ingest_dedupes():
    import json
    from pathlib import Path

    from content.ingestion import ingest_entries, normalize_link
    from content.matching import load_config
    from content.models import Item, Source

    config = load_config()
    feed = next(feed for feed in config["feeds"] if feed["key"] == "fcc_html")
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "content"
        / "tests"
        / "fixtures"
        / "feeds"
        / "fcc_html.json"
    )
    entry = json.loads(fixture_path.read_text(encoding="utf-8"))[0]
    normalized_link = normalize_link(entry["link"])

    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    item = Item.objects.get(normalized_link=normalized_link)
    assert item.title.count("(sample content)") == 1
    assert Item.objects.filter(normalized_link=normalized_link).count() == 1
    item_id = item.pk

    result = ingest_entries(
        Source.objects.get(url=feed["url"]),
        feed,
        [entry],
        item.fetched_at,
        config,
    )

    assert result["created"] == 0
    assert result["duplicates_merged"] == 1
    assert Item.objects.filter(normalized_link=normalized_link).count() == 1
    assert Item.objects.get(normalized_link=normalized_link).pk == item_id


def test_seed_demo_repairs_only_seed_owned_data_analyst_demo_dates():
    from datetime import UTC, datetime

    from django.utils import timezone

    from content.models import Item, Source

    live_url = "https://news.mit.edu/rss/research"
    source = Source.objects.create(
        name="Existing live source",
        url="https://example.test/live-source",
        credibility_note="Existing live item for seed-key collision test.",
    )
    live_date = datetime(2020, 5, 4, tzinfo=UTC)
    live_item = Item.objects.create(
        title="Live item at a seed URL",
        url=live_url,
        published_at=live_date,
        source=source,
        is_low_data=False,
    )

    call_command("seed_demo", verbosity=0)

    old_seed_items = [
        Item.objects.get(
            url="https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content"
        ),
        Item.objects.get(url="https://www.freecodecamp.org/news/sql-tutorial/"),
    ]
    old_date = timezone.now()
    Item.objects.filter(pk__in=[item.pk for item in old_seed_items]).update(
        published_at=old_date
    )

    call_command("seed_demo", verbosity=0)

    fixed_date = datetime(2026, 1, 1, tzinfo=UTC)
    for item in old_seed_items:
        item.refresh_from_db()
        assert item.published_at == fixed_date
    live_item.refresh_from_db()
    assert live_item.title == "Live item at a seed URL"
    assert live_item.published_at == live_date
    assert live_item.is_low_data is False


def test_seed_demo_provides_picks_for_each_data_analyst_skill():
    from content.models import Item
    from pathways.management.commands.seed_demo import DATA_ANALYST_DEMO_KEYS

    call_command("seed_demo", verbosity=0)

    seeded_items = [
        Item.objects.get(url=url, title=title)
        for url, title in DATA_ANALYST_DEMO_KEYS
    ]
    seeded_item_ids = [item.pk for item in seeded_items]
    expected_counts = {
        "Spreadsheets": 3,
        "SQL": 3,
        "Data Visualisation": 1,
        "Statistics": 2,
    }
    for skill_name, expected_count in expected_counts.items():
        assert (
            Item.objects.filter(
                pk__in=seeded_item_ids, skills__name=skill_name
            ).distinct().count()
            == expected_count
        )


def test_pathways_list_omits_seeded_picks_and_stays_under_1500_bytes(seeded):
    response = APIClient().get("/api/pathways/")

    assert response.status_code == 200
    assert len(response.content) < 1500
    assert all(
        set(pathway)
        == {"id", "title", "description", "target_outcome", "locale"}
        for pathway in response.data
    )


def test_clean_seed_omits_search_visibility_demo():
    from content.models import Item

    call_command("seed_demo", verbosity=0)

    assert not Item.objects.filter(title="Search visibility basics (demo)").exists()


def test_demo_items_have_only_canonical_pathway_skills():
    from content.models import Item

    call_command("seed_demo", verbosity=0)
    canonical_skills = {
        skill_name
        for pathway in CANONICAL_PATHWAYS
        for skill_name in pathway["skills"]
    }

    for item in Item.objects.filter(title__endswith="(demo)"):
        assert set(item.skills.values_list("name", flat=True)) <= canonical_skills


def test_seed_demo_preserves_existing_search_visibility_row():
    from django.utils import timezone

    from content.models import Item, Skill, Source

    source = Source.objects.create(
        name="Existing seed source",
        url="https://developers.google.com/search/feed",
        credibility_note="Existing seed row",
    )
    seo, _ = Skill.objects.get_or_create(slug="seo", defaults={"name": "SEO"})
    item = Item.objects.create(
        title="Search visibility basics (demo)",
        url="https://developers.google.com/search/docs/fundamentals/seo-starter-guide",
        published_at=timezone.now(),
        source=source,
    )
    item.skills.add(seo)

    call_command("seed_demo", verbosity=0)

    item.refresh_from_db()
    assert Item.objects.filter(pk=item.pk).exists()
    assert list(item.skills.values_list("name", flat=True)) == ["SEO"]


def test_seed_demo_does_not_strip_live_item_skills():
    from django.utils import timezone

    from content.models import Item, Skill, Source

    source = Source.objects.create(
        name="Live research feed",
        url="https://news.mit.edu/rss/research",
        credibility_note="Live ingested source",
    )
    marketing, _ = Skill.objects.get_or_create(
        slug="marketing-analytics", defaults={"name": "Marketing Analytics"}
    )
    seo, _ = Skill.objects.get_or_create(slug="seo", defaults={"name": "SEO"})
    live_date = timezone.now()
    item = Item.objects.create(
        title="Live research item",
        url="https://news.mit.edu/rss/research",
        published_at=live_date,
        is_low_data=False,
        source=source,
    )
    item.skills.add(marketing, seo)

    call_command("seed_demo", verbosity=0)

    item.refresh_from_db()
    assert item.title == "Live research item"
    assert item.published_at == live_date
    assert item.is_low_data is False
    assert {"Marketing Analytics", "SEO"} <= set(
        item.skills.values_list("name", flat=True)
    )


def test_noncanonical_item_skills_are_filtered_without_changing_recommendations(
    seeded,
):
    from django.utils import timezone

    from content.models import Item, Skill
    from pathways.logic import recommendations

    sql_skill = Skill.objects.get(name="SQL")
    seo, _ = Skill.objects.get_or_create(slug="seo", defaults={"name": "SEO"})
    marketing, _ = Skill.objects.get_or_create(
        slug="marketing-analytics", defaults={"name": "Marketing Analytics"}
    )
    item = Item.objects.create(
        title="A canonical pick with noncanonical tags",
        url="https://api-skills.example.test/pick",
        summary="A test pick for canonical skill filtering.",
        published_at=timezone.now(),
        source=Item.objects.first().source,
    )
    item.skills.add(sql_skill, seo, marketing)
    ranked_ids = [recommended.pk for recommended in recommendations(sql_skill, 3)]
    client = APIClient()
    client.post("/api/demo/")

    dashboard = client.get("/api/dashboard/")
    next_response = client.get("/api/next/")

    assert dashboard.status_code == next_response.status_code == 200
    assert dashboard.data["items"][0]["id"] == item.pk
    assert next_response.data["items"][0]["id"] == item.pk
    for response in (dashboard, next_response):
        payload = next(
            item_json for item_json in response.data["items"] if item_json["id"] == item.pk
        )
        assert payload["skills"] == ["SQL"]
        assert "SEO" not in payload["skills"]
        assert "Marketing Analytics" not in payload["skills"]
    assert [recommended.pk for recommended in recommendations(sql_skill, 3)] == ranked_ids
    assert {"SEO", "Marketing Analytics"} <= set(
        item.skills.values_list("name", flat=True)
    )


def test_dashboard_round_robin_covers_four_skills_deduplicates_and_is_deterministic(
    seeded, monkeypatch
):
    from django.utils import timezone

    from content.models import Item
    from learners import api as learners_api

    pathway = seeded["Data Analyst"]
    skills = [step.skill for step in pathway.steps.select_related("skill").order_by("order")]
    source = Item.objects.first().source
    learner = LearnerProfile.objects.create(
        display_name="Round robin learner", chosen_pathway=pathway
    )
    client = APIClient()
    session = client.session
    session["learner_id"] = learner.pk
    session.save()

    item_lists = {}
    for skill in skills:
        item_lists[skill.name] = []
        for index in range(3):
            item = Item.objects.create(
                title=f"Round robin {skill.name} {index}",
                url=f"https://round-robin.example/{skill.slug}-{index}",
                summary="A deterministic dashboard pick.",
                published_at=timezone.now(),
                source=source,
            )
            item.skills.add(skill)
            item_lists[skill.name].append(item)

    shared = item_lists[skills[0].name][0]
    shared.skills.add(skills[1])
    item_lists[skills[1].name][0] = shared
    monkeypatch.setattr(
        learners_api,
        "recommendations",
        lambda skill, limit=5: item_lists[skill.name][:limit],
    )

    first = client.get("/api/dashboard/")
    second = client.get("/api/dashboard/")

    assert first.status_code == second.status_code == 200
    assert first.data["remaining"] == [skill.name for skill in skills]
    item_ids = [item["id"] for item in first.data["items"]]
    assert len(item_ids) == 8
    assert item_ids == [item["id"] for item in second.data["items"]]
    assert item_ids == [
        shared.pk,
        item_lists[skills[2].name][0].pk,
        item_lists[skills[3].name][0].pk,
        item_lists[skills[0].name][1].pk,
        item_lists[skills[1].name][1].pk,
        item_lists[skills[2].name][1].pk,
        item_lists[skills[3].name][1].pk,
        item_lists[skills[0].name][2].pk,
    ]
    assert len(item_ids) == len(set(item_ids))
    returned_skills = {
        skill_name
        for item in first.data["items"]
        for skill_name in item["skills"]
    }
    assert set(first.data["remaining"]) <= returned_skills
    shared_pick = next(item for item in first.data["items"] if item["id"] == shared.pk)
    assert shared_pick["skills"] == [skills[0].name, skills[1].name]


def test_seed_demo_keeps_existing_duplicate_rows_and_updates_lowest_id_match():
    call_command("seed_demo", verbosity=0)
    pathway = Pathway.objects.get(title="Data Analyst")
    duplicate_pathway = Pathway.objects.create(
        title="Data Analyst",
        description="Leave this duplicate pathway untouched.",
        target_outcome="Legacy outcome",
    )
    duplicate_learner = LearnerProfile.objects.create(
        display_name="Amina Demo",
        preferred_language="sw",
        reminder_opt_in=False,
        chosen_pathway=duplicate_pathway,
    )

    call_command("seed_demo", verbosity=0)

    assert Pathway.objects.filter(title="Data Analyst").count() == 2
    assert LearnerProfile.objects.filter(display_name="Amina Demo").count() == 2
    assert Pathway.objects.get(pk=duplicate_pathway.pk).description == (
        "Leave this duplicate pathway untouched."
    )
    assert (
        LearnerProfile.objects.get(pk=duplicate_learner.pk).preferred_language == "sw"
    )
    canonical_amina = (
        LearnerProfile.objects.filter(display_name="Amina Demo").order_by("pk").first()
    )
    assert canonical_amina is not None
    amina = canonical_amina
    assert amina.chosen_pathway_id == pathway.pk
    assert amina.preferred_language == "en"
    assert amina.reminder_opt_in is True


def test_seed_demo_renames_only_lowest_duplicate_web_developer_pathway():
    legacy_steps = ("HTML", "CSS", "JavaScript", "Accessibility")
    legacy_rows = []
    for description in ("Lowest legacy row", "Later legacy duplicate"):
        pathway = Pathway.objects.create(
            title="Web Developer",
            description=description,
            target_outcome="Old web outcome",
        )
        legacy_rows.append(pathway)
        for order, name in enumerate(legacy_steps, start=1):
            skill, _ = Skill.objects.get_or_create(
                slug=name.lower().replace(" ", "-"), defaults={"name": name}
            )
            PathwaySkill.objects.create(pathway=pathway, skill=skill, order=order)

    call_command("seed_demo", verbosity=0)

    lowest, later = legacy_rows
    lowest.refresh_from_db()
    later.refresh_from_db()
    assert lowest.title == CANONICAL_PATHWAYS[1]["title"]
    assert later.title == "Web Developer"
    assert Pathway.objects.filter(title="Web Developer").count() == 1
    response = APIClient().get("/api/pathways/")
    assert response.status_code == 200
    assert [path["title"] for path in response.data] == [
        pathway["title"] for pathway in CANONICAL_PATHWAYS
    ]


def test_health_endpoint_is_public():
    response = APIClient().get("/api/health/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


def test_skip_restart_switch_and_delete_are_available(seeded):
    client = APIClient()
    data_path = seeded["Data Analyst"]
    web_path = seeded["Frontend Developer"]
    client.post("/api/me/", {"pathway_id": data_path.pk}, format="json")
    first = data_path.steps.first().checkpoint
    assert (
        client.post(f"/api/checkpoints/{first.pk}/skip/", {}, format="json").status_code
        == 200
    )
    assert CheckpointRecord.objects.filter(status="skipped").exists()
    assert client.get("/api/dashboard/").data["next_checkpoint"]["skill"] == "SQL"
    assert client.post("/api/pathway/restart/", {}, format="json").data["restarted"]
    assert not CheckpointRecord.objects.filter(status="skipped").exists()
    assert (
        client.post(
            "/api/pathway/switch/", {"pathway_id": web_path.pk}, format="json"
        ).data["pathway_id"]
        == web_path.pk
    )
    assert client.delete("/api/me/").data["deleted"]
    assert LearnerProfile.objects.filter(chosen_pathway=web_path).count() == 0


def test_quiz_must_have_three_answers_and_due_reminders_are_opt_in_and_bilingual(
    seeded, capsys
):
    from datetime import timedelta

    from django.utils import timezone

    from engagement.models import ReminderLog

    client = APIClient()
    pathway = seeded["Data Analyst"]
    client.post("/api/me/", {"pathway_id": pathway.pk}, format="json")
    checkpoint = pathway.steps.first().checkpoint
    assert (
        client.post(
            f"/api/checkpoints/{checkpoint.pk}/complete/",
            {"self_attested": True, "quiz_answers": [0]},
            format="json",
        ).status_code
        == 400
    )

    learner = LearnerProfile.objects.get(display_name="Learner")
    learner.reminder_opt_in = True
    learner.preferred_language = "sw"
    learner.save()
    recent = ReminderLog.objects.create(learner=learner, message="recent")
    recent.sent_at = timezone.now() - timedelta(days=1)
    recent.save(update_fields=["sent_at"])
    LearnerProfile.objects.create(chosen_pathway=pathway, display_name="No reminders")
    english_learner = LearnerProfile.objects.create(
        chosen_pathway=pathway,
        display_name="English reminders",
        preferred_language="en",
        reminder_opt_in=True,
    )
    call_command("send_reminders")
    output = capsys.readouterr().out
    assert "No reminders" not in output
    assert "English reminders" in output
    assert "lessons to your next checkpoint" in output
    english_message = ReminderLog.objects.get(learner=english_learner).message
    assert len(english_message) <= 160
    assert ReminderLog.objects.filter(learner=learner).count() == 1

    recent.sent_at = timezone.now() - timedelta(days=8)
    recent.save(update_fields=["sent_at"])
    call_command("send_reminders")
    output = capsys.readouterr().out
    message = [line for line in output.splitlines() if "SOMA.i:" in line][0].split(
        "SOMA.i: ", 1
    )[1]
    assert "Masomo" in message
    assert len("SOMA.i: " + message) <= 160
    assert ReminderLog.objects.filter(learner=learner).count() == 2
