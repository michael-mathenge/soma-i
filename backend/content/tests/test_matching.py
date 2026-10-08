from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from content.matching import (
    beginner_score,
    exclusion_reason,
    load_config,
    plain_text,
    ranking_key,
    ranking_score,
    topic_matches,
)


def test_css_media_queries_are_frontend_not_data_analyst():
    title = "CSS Media Queries for Beginners: How to Make a Website Responsive"
    summary = "CSS media queries help adapt a site to different screen sizes."
    assert not topic_matches("Data Analyst", title, summary)
    assert topic_matches("Frontend Developer", title, summary)


def test_css_flexbox_and_grid_are_frontend_not_data_analyst():
    title = "CSS Flexbox vs CSS Grid: Which One Should Beginners Learn First?"
    assert not topic_matches("Data Analyst", title)
    assert topic_matches("Frontend Developer", title)


def test_html_css_projects_are_frontend_not_data_analyst():
    title = "10 HTML and CSS Projects for Beginners to Practice in 2026"
    assert not topic_matches("Data Analyst", title)
    assert topic_matches("Frontend Developer", title)


@pytest.mark.parametrize(
    "title",
    [
        "Zakat Calculation Guide for Muslims: Step by Step",
        "GPT-2 is the transformer plus five decisions, and inference is a different program",
        "Your first HTTPS certificate renewal: issue, install, check",
    ],
)
def test_reported_unrelated_titles_pass_no_pathway(title):
    for pathway in load_config()["pathways"]:
        assert not topic_matches(pathway, title, source_type="community")


def test_ai_presentation_slides_pass_no_pathway():
    title = "How To Create Professional Presentation Slides Using AI In 5 Minutes"
    summary = "A presentation layout can be made in just a few minutes."
    for pathway in load_config()["pathways"]:
        assert not topic_matches(pathway, title, summary)


@pytest.mark.parametrize(
    "title",
    [
        "The Gamepad API Lies to You: A Practical Guide to Reading Controller Input in JavaScript",
        "How to Use the Fullscreen API in JavaScript (and Keep the Screen Awake with the Wake Lock API)",
    ],
)
def test_browser_apis_do_not_pass_backend_pathway_without_backend_context(title):
    assert not topic_matches("Backend/Python Developer", title)


def test_best_company_promo_is_excluded():
    title = "How to Choose the Best React JS Development Company in the UK"
    assert exclusion_reason(title, "community")


def test_free_api_promo_is_excluded():
    title = "A free SEO audit API for developers: score any URL with one request"
    assert exclusion_reason(title, "community")


def test_self_introduction_promo_is_excluded():
    title = "DEV! Breaking my lurking streak to introduce myself"
    assert exclusion_reason(title, "community")


def test_quiz_titles_are_excluded_for_every_source_type():
    assert exclusion_reason("Quiz: Python basics", "publisher")
    assert exclusion_reason("Quiz: CSS basics", "community")


def test_community_topic_matching_uses_title_only():
    assert not topic_matches(
        "Data Analyst",
        "A short community post",
        "Learn SQL, query databases, and use pandas.",
        "community",
    )


def test_publisher_matching_uses_only_first_300_plain_text_summary_chars():
    assert not topic_matches(
        "Data Analyst",
        "An unrelated article",
        "x" * 300 + " pandas",
        "publisher",
    )
    assert topic_matches(
        "Data Analyst",
        "An unrelated article",
        "<p>Learn <strong>pandas</strong> basics.</p>",
        "publisher",
    )


def test_data_analyst_uses_sql_query_phrase_but_not_standalone_query():
    assert topic_matches("Data Analyst", "SQL query optimization")
    assert not topic_matches("Data Analyst", "How CSS media queries work")


def test_frontend_requires_css_grid_and_css_layout_phrases():
    assert topic_matches("Frontend Developer", "CSS Grid for beginners")
    assert not topic_matches("Frontend Developer", "Grid-based office planning")
    assert topic_matches("Frontend Developer", "CSS layout fundamentals")
    assert not topic_matches("Frontend Developer", "Presentation layout fundamentals")


def test_backend_api_requires_a_backend_context_term():
    assert not topic_matches("Backend/Python Developer", "The Fullscreen API")
    assert not topic_matches("Backend/Python Developer", "API tools")
    assert not topic_matches("Backend/Python Developer", "REST services")
    assert topic_matches("Backend/Python Developer", "REST API tools")
    assert topic_matches("Backend/Python Developer", "REST API design")
    assert topic_matches("Backend/Python Developer", "Python API design")


def test_frontend_keywords_include_git_and_github():
    config = load_config()
    frontend_terms = config["pathways"]["Frontend Developer"]["keywords"]
    assert "git" in frontend_terms
    assert "github" in frontend_terms
    assert topic_matches("Frontend Developer", "Learn Git and GitHub")


def test_frontend_git_term_uses_token_matching():
    assert topic_matches("Frontend Developer", "Git basics")
    assert topic_matches("Frontend Developer", "GitHub introduction")
    assert not topic_matches("Frontend Developer", "Digital fundamentals")


def test_html_is_removed_before_matching():
    assert plain_text("<script>sql</script><p>Useful <b>Python</b> guide</p>") == (
        "sql Useful Python guide"
    )
    assert topic_matches(
        "Backend/Python Developer",
        "A guide",
        "<p>Useful <b>Python</b> basics</p>",
    )


def test_hostile_title_html_is_stripped_before_topic_matching():
    title = '<img src=x onerror="alert(1)"> Python basics'
    assert plain_text(title) == "Python basics"
    assert topic_matches("Backend/Python Developer", title)


def test_beginner_score_and_community_adjustment():
    assert beginner_score("Python basics tutorial") == 3
    assert beginner_score("Deep dive into Python internals") == -4
    assert ranking_score("Python basics", source_type="community") == 1


def test_recency_breaks_ties_and_fetched_dates_get_no_recency_advantage():
    older = SimpleNamespace(
        title="An article",
        summary="",
        date_source="published",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = SimpleNamespace(
        title="An article",
        summary="",
        date_source="updated",
        published_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    fetched = SimpleNamespace(
        title="An article",
        summary="",
        date_source="fetched",
        published_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    assert ranking_key(newer) < ranking_key(older)
    assert ranking_key(older) < ranking_key(fetched)
