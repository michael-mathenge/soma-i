import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from content.ingestion import (
    _matched_skills,
    clean_summary,
    ingest_entries,
    normalize_link,
    pathway_matches,
    safe_http_link,
)
from content.matching import load_config, plain_text
from content.models import Item, Skill, Source
from learners.models import LearnerProfile
from opportunities.models import Opportunity
from pathways.constants import CANONICAL_PATHWAYS, FIXTURE_FEEDS
from pathways.models import Checkpoint, CheckpointRecord, Pathway, PathwaySkill

FIXED_SAMPLE_DATE = datetime(2026, 1, 1, tzinfo=UTC)
LEGACY_FRONTEND_TITLE = "Web Developer"
SAMPLE_CONTENT_LABEL = " (sample content)"
DATA_ANALYST_DEMO_KEYS = {
    (
        "https://github.com/michael-mathenge/soma-i#demo-spreadsheet-skills",
        "Spreadsheet skills for clear data (demo)",
    ),
    (
        "https://github.com/michael-mathenge/soma-i#demo-spreadsheet-formulas",
        "Practice spreadsheet formulas (demo)",
    ),
    (
        "https://github.com/michael-mathenge/soma-i#demo-small-dataset",
        "Organize a small dataset (demo)",
    ),
}
SAMPLE_SOURCE_URL = "https://github.com/michael-mathenge/soma-i"
LEGACY_DEMO_URLS = {
    "Spreadsheet skills for clear data (demo)": "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content",
    "Practice spreadsheet formulas (demo)": "https://www.freecodecamp.org/news/sql-tutorial/",
    "Organize a small dataset (demo)": "https://news.mit.edu/rss/research",
    "CSS layout foundations (demo)": "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics",
    "JavaScript essentials (demo)": "https://www.freecodecamp.org/news/learn-javascript-full-course/",
}
EXCLUDED_SEED_FIXTURE_SKILLS = {
    (
        "https://www.freecodecamp.org/news/how-to-build-a-reading-focused-blog-with-python-markdown-and-github-pages-for-free/",
        "Data Visualisation",
    ),
}
QUIZ = [
    {
        "question": "Which action best shows this skill?",
        "options": ["Apply it to a small task", "Skip all practice"],
        "answer": 0,
    },
    {
        "question": "What should you do when a result looks wrong?",
        "options": ["Check your steps", "Ignore the result"],
        "answer": 0,
    },
    {
        "question": "How can you keep improving?",
        "options": ["Practice and reflect", "Stop after one try"],
        "answer": 0,
    },
]


def _update_first_or_create(model, *, lookup, defaults):
    """Update the lowest-ID match, without deleting legacy duplicate rows."""
    existing = model.objects.filter(**lookup).order_by("pk").first()
    if existing is not None:
        return model.objects.update_or_create(pk=existing.pk, defaults=defaults)
    return model.objects.update_or_create(**lookup, defaults=defaults)


class Command(BaseCommand):
    help = "Seed pathways, sample content, opportunities, and an offline demo learner."

    def handle(self, *args, **options):
        skill_by_name = {}
        for pathway_config in CANONICAL_PATHWAYS:
            for name in pathway_config["skills"]:
                slug = name.lower().replace(" ", "-")
                skill_by_name[name], _ = Skill.objects.get_or_create(
                    slug=slug, defaults={"name": name}
                )
        self._rename_legacy_frontend_pathway()

        seeded = {}
        for pathway_config in CANONICAL_PATHWAYS:
            title = pathway_config["title"]
            pathway, _ = _update_first_or_create(
                Pathway,
                lookup={"title": title},
                defaults={
                    "description": pathway_config["description"],
                    "target_outcome": pathway_config["target_outcome"],
                    "locale": "KE",
                },
            )
            seeded[title] = pathway
            for order, name in enumerate(pathway_config["skills"], start=1):
                step, _ = PathwaySkill.objects.update_or_create(
                    pathway=pathway,
                    order=order,
                    defaults={"skill": skill_by_name[name]},
                )
                Checkpoint.objects.update_or_create(
                    pathway_skill=step,
                    defaults={
                        "title": f"{name} checkpoint",
                        "criteria": f"Complete a short practice task using {name} and reflect on what you learned.",
                        "unlocks_text": (
                            f"You can now use {name} as part of your "
                            f"{pathway_config['target_outcome']} journey."
                        ),
                        "quiz_json": QUIZ,
                    },
                )

        sample_source, _ = Source.objects.update_or_create(
            url=SAMPLE_SOURCE_URL,
            defaults={
                "name": "SOMA.i sample content",
                "credibility_note": "Hand-written sample content for the SOMA.i demo; not from an external feed.",
                "attribution": "SOMA.i",
                "rights": "not stated",
                "level": "beginner",
                "language": "en",
                "active": True,
            },
        )
        examples = [
            (
                "Spreadsheet skills for clear data",
                "Work with rows, columns, formulas, and summaries.",
                ["Spreadsheets", "SQL"],
                "https://github.com/michael-mathenge/soma-i#demo-spreadsheet-skills",
            ),
            (
                "Practice spreadsheet formulas",
                "Use formulas to summarize a small dataset.",
                ["Spreadsheets", "SQL", "Data Visualisation", "Statistics"],
                "https://github.com/michael-mathenge/soma-i#demo-spreadsheet-formulas",
            ),
            (
                "Organize a small dataset",
                "Sort and filter example records before analysis.",
                ["Spreadsheets", "SQL", "Statistics"],
                "https://github.com/michael-mathenge/soma-i#demo-small-dataset",
            ),
            (
                "CSS layout foundations",
                "Use CSS to style and arrange a simple page.",
                ["CSS", "HTML"],
                "https://github.com/michael-mathenge/soma-i#demo-css-layout",
            ),
            (
                "JavaScript essentials",
                "Add interaction with beginner JavaScript concepts.",
                ["JavaScript", "HTML"],
                "https://github.com/michael-mathenge/soma-i#demo-javascript-essentials",
            ),
        ]
        for title, summary, names, url in examples:
            sample_title = f"{title} (demo)"
            item = Item.objects.filter(url=url, title=sample_title).order_by("pk").first()
            if item is None:
                legacy_url = LEGACY_DEMO_URLS[sample_title]
                item = (
                    Item.objects.filter(url=legacy_url, title=sample_title)
                    .order_by("pk")
                    .first()
                )
            created = item is None
            if created:
                if Item.objects.filter(url=url).exists():
                    continue
                item = Item(
                    url=url,
                    title=sample_title,
                    summary=summary,
                    published_at=FIXED_SAMPLE_DATE,
                    source=sample_source,
                    estimated_minutes=8,
                    is_low_data=True,
                )
            else:
                item.url = url
                item.title = sample_title
                item.summary = summary
                item.source = sample_source
                item.estimated_minutes = 8
                item.is_low_data = True
            item.normalized_link = None
            item.save()
            for name in names:
                if name not in skill_by_name:
                    slug = name.lower().replace(" ", "-")
                    skill_by_name[name], _ = Skill.objects.get_or_create(
                        slug=slug, defaults={"name": name}
                    )
            assigned_skills = [skill_by_name[name] for name in names]
            if created or item.title == sample_title:
                # Replace legacy marketing tags on seed-owned demos with their pathway skills.
                item.skills.set(assigned_skills)
            if (url, item.title) in DATA_ANALYST_DEMO_KEYS:
                if item.published_at != FIXED_SAMPLE_DATE:
                    item.published_at = FIXED_SAMPLE_DATE
                    item.save(update_fields=["published_at"])

        self._seed_fixture_items()

        opportunity_seeds = [
            (
                "Junior Data Analyst (sample)",
                "job",
                "Sample Kenya employer",
                "sql",
                "Junior data role",
                "https://www.brightermonday.co.ke/",
            ),
            (
                "Data Intern (sample)",
                "internship",
                "Sample Nairobi placement",
                "spreadsheets",
                "Entry-level internship",
                "https://www.fuzu.com/kenya",
            ),
            (
                "Open Data Scholarship (sample)",
                "scholarship",
                "Sample learning fund",
                "statistics",
                "Training scholarship",
                "https://www.helb.co.ke/",
            ),
            (
                "Web Developer Trainee (sample)",
                "internship",
                "Sample digital studio",
                "html",
                "Junior web placement",
                "https://www.brightermonday.co.ke/",
            ),
            (
                "Frontend Developer (sample)",
                "job",
                "Sample Kenya technology team",
                "javascript",
                "Entry-level web role",
                "https://www.fuzu.com/kenya",
            ),
            (
                "Web Accessibility Course (sample)",
                "course",
                "Sample open course",
                "accessibility",
                "Skills course",
                "https://developer.mozilla.org/en-US/docs/Learn_web_development",
            ),
            (
                "Digital Content Assistant (sample)",
                "job",
                "Sample local agency",
                "content-strategy",
                "Junior marketing role",
                "https://www.brightermonday.co.ke/",
            ),
            (
                "Marketing Assistant Internship (sample)",
                "internship",
                "Sample Nairobi agency",
                "social-media",
                "Entry-level placement",
                "https://www.fuzu.com/kenya",
            ),
            (
                "Digital Marketing Certificate (sample)",
                "certification",
                "Sample training provider",
                "seo",
                "Introductory certification",
                "https://learndigital.withgoogle.com/digitalgarage",
            ),
            (
                "Youth Digital Skills Course (sample)",
                "course",
                "Sample Kenya training hub",
                "css",
                "Digital skills course",
                "https://ajiradigital.go.ke/",
            ),
        ]
        for title, kind, provider, skill_slug, note, url in opportunity_seeds:
            skill = Skill.objects.filter(slug=skill_slug).first()
            opportunity, _ = Opportunity.objects.update_or_create(
                title=title,
                defaults={
                    "type": kind,
                    "provider": provider,
                    "url": url,
                    "location": "Kenya",
                    "source_note": note,
                },
            )
            opportunity.skills.set([skill] if skill else [])

        pathway = seeded["Data Analyst"]
        demo, _ = _update_first_or_create(
            LearnerProfile,
            lookup={"display_name": "Amina Demo"},
            defaults={
                "preferred_language": "en",
                "reminder_opt_in": True,
                "reminder_frequency": "weekly",
                "chosen_pathway": pathway,
            },
        )
        first_checkpoint = pathway.steps.select_related("checkpoint").first().checkpoint
        CheckpointRecord.objects.update_or_create(
            learner=demo,
            checkpoint=first_checkpoint,
            defaults={
                "status": "done",
                "self_attested": True,
                "quiz_answers": {"demo": True},
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded pathways, demo items, 10 sample opportunities, and Amina Demo."
            )
        )

    def _rename_legacy_frontend_pathway(self):
        if Pathway.objects.filter(title=CANONICAL_PATHWAYS[1]["title"]).exists():
            return
        legacy = (
            Pathway.objects.filter(title=LEGACY_FRONTEND_TITLE).order_by("pk").first()
        )
        if legacy is None:
            return

        expected = list(CANONICAL_PATHWAYS[1]["skills"][:4])
        actual = list(
            legacy.steps.select_related("skill")
            .order_by("order")
            .values_list("skill__name", flat=True)
        )
        if actual != expected:
            raise CommandError(
                "Cannot rename Web Developer: expected the existing four steps "
                f"{expected}, found {actual}."
            )

        legacy.title = CANONICAL_PATHWAYS[1]["title"]
        legacy.description = CANONICAL_PATHWAYS[1]["description"]
        legacy.target_outcome = CANONICAL_PATHWAYS[1]["target_outcome"]
        legacy.save(update_fields=["title", "description", "target_outcome"])

    def _seed_fixture_items(self):
        config = load_config()
        feeds_by_key = {feed["key"]: feed for feed in config["feeds"]}
        fixture_dir = (
            Path(__file__).resolve().parents[3]
            / "content"
            / "tests"
            / "fixtures"
            / "feeds"
        )

        for feed_key in FIXTURE_FEEDS:
            feed = feeds_by_key[feed_key]
            source, _ = Source.objects.get_or_create(
                url=feed["url"],
                defaults={
                    "name": feed["name"],
                    "credibility_note": (
                        f"RSS feed attributed to {feed['attribution']}."
                    ),
                    "attribution": feed["attribution"],
                    "rights": feed.get("rights", "not stated"),
                    "level": feed.get("level", "mixed"),
                },
            )
            entries = json.loads(
                (fixture_dir / f"{feed_key}.json").read_text(encoding="utf-8")
            )
            entries_to_ingest = []
            new_normalized_links = set()
            for entry in entries:
                original_link = safe_http_link(entry.get("link", ""))
                if original_link is None:
                    entries_to_ingest.append(entry)
                    continue
                title = plain_text(entry.get("title", "")).strip()[:300]
                summary = clean_summary(
                    entry.get(
                        "summary", entry.get("description", entry.get("excerpt", ""))
                    )
                )
                if not title or not pathway_matches(feed, title, summary, config):
                    continue

                normalized_link = normalize_link(original_link)
                item = (
                    Item.objects.filter(normalized_link=normalized_link)
                    .order_by("pk")
                    .first()
                )
                if item is None:
                    item = Item.objects.filter(url=original_link).order_by("pk").first()
                guid = str(entry.get("id", entry.get("guid", ""))).strip()
                if item is None and guid:
                    item = (
                        Item.objects.filter(source=source, guid=guid)
                        .order_by("pk")
                        .first()
                    )
                if item is not None:
                    item.skills.add(*_matched_skills(title, summary))
                    continue

                entries_to_ingest.append(entry)
                new_normalized_links.add(normalized_link)

            ingest_entries(source, feed, entries_to_ingest, FIXED_SAMPLE_DATE, config)
            for normalized_link in new_normalized_links:
                item = (
                    Item.objects.filter(normalized_link=normalized_link)
                    .order_by("pk")
                    .first()
                )
                if item is None:
                    continue
                if not item.title.endswith(SAMPLE_CONTENT_LABEL):
                    item.title = f"{item.title}{SAMPLE_CONTENT_LABEL}"
                item.is_low_data = True
                item.save(update_fields=["title", "is_low_data"])

            for link, skill_name in EXCLUDED_SEED_FIXTURE_SKILLS:
                if not any(
                    normalize_link(entry.get("link", "")) == normalize_link(link)
                    for entry in entries
                ):
                    continue
                item = (
                    Item.objects.filter(normalized_link=normalize_link(link))
                    .order_by("pk")
                    .first()
                )
                if item is not None and item.title.endswith(SAMPLE_CONTENT_LABEL):
                    skill = Skill.objects.get(name=skill_name)
                    item.skills.remove(skill)
