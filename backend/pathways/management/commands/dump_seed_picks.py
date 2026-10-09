import json

from django.core.management.base import BaseCommand
from django.db.models import Q

from content.models import Item
from pathways.constants import CANONICAL_PATHWAYS


class Command(BaseCommand):
    help = "Test-support command; read-only; not used by the application."

    def handle(self, *args, **options):
        pathway_skills = {
            pathway["title"]: pathway["skills"] for pathway in CANONICAL_PATHWAYS
        }
        canonical_skills = {
            skill_name
            for skills in pathway_skills.values()
            for skill_name in skills
        }
        items = (
            Item.objects.filter(
                Q(title__endswith=" (demo)")
                | Q(title__endswith=" (sample content)"),
                skills__name__in=canonical_skills,
            )
            .distinct()
            .prefetch_related("skills")
            .order_by("pk")
        )

        picks = {
            pathway_title: {skill_name: [] for skill_name in skills}
            for pathway_title, skills in pathway_skills.items()
        }
        for item in items:
            item_skills = {
                skill.name
                for skill in item.skills.all()
                if skill.name in canonical_skills
            }
            declared_skills = sorted(item_skills)
            for pathway_title, skills in pathway_skills.items():
                for skill_name in skills:
                    if skill_name in item_skills:
                        picks[pathway_title][skill_name].append(
                            {
                                "id": item.pk,
                                "title": item.title,
                                "skills": declared_skills,
                            }
                        )

        self.stdout.write(json.dumps(picks, ensure_ascii=False))
