import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from pathways.constants import CANONICAL_PATHWAYS
from pathways.models import Pathway

pytestmark = pytest.mark.django_db


def test_seeded_dashboard_top_three_preview_and_amina_order():
    call_command("seed_demo", verbosity=0)
    client = APIClient()
    assert client.post("/api/demo/").status_code == 200

    pathways = {
        pathway.title: pathway
        for pathway in Pathway.objects.filter(
            title__in=[config["title"] for config in CANONICAL_PATHWAYS]
        )
    }
    previews = {}
    for config in CANONICAL_PATHWAYS:
        title = config["title"]
        if title != "Data Analyst":
            response = client.post(
                "/api/me/",
                {
                    "display_name": "Ranking preview learner",
                    "preferred_language": "en",
                    "pathway_id": pathways[title].pk,
                },
                format="json",
            )
            assert response.status_code in {200, 201}
        response = client.get("/api/dashboard/")
        assert response.status_code == 200
        previews[title] = [item["title"] for item in response.data["items"][:3]]
        print(f"{title}: {previews[title]}")

    assert previews["Data Analyst"] == [
        "Organize a small dataset (demo)",
        "Practice spreadsheet formulas (demo)",
        "Spreadsheet skills for clear data (demo)",
    ]
    assert "GraphRAG" not in previews["Backend/Python Developer"][0]
