import pytest

from content.models import Skill
from opportunities.matching import match_score
from opportunities.models import Opportunity

pytestmark = pytest.mark.django_db


def test_opportunity_score_is_skill_overlap_percentage():
    sql = Skill.objects.create(name="SQL", slug="sql")
    html = Skill.objects.create(name="HTML", slug="html")
    opportunity = Opportunity.objects.create(
        title="Sample",
        type="job",
        provider="Sample provider",
        url="https://example.test/job",
    )
    opportunity.skills.add(sql, html)
    assert match_score(sql, opportunity) == 50
    assert match_score(html, opportunity) == 50
