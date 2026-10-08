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


def test_css_media_queries_are_not_data_analyst_content():
    title = "CSS Media Queries for Beginners: How to Make a Website Responsive"
    summary = "CSS media queries help adapt a site to different screen sizes."
    assert not topic_matches("Data Analyst", title, summary)
    assert topic_matches("Frontend Developer", title, summary)


@pytest.mark.parametrize(
    "title,summary",
    [
        (
            "How To Create Professional Presentation Slides Using AI In 5 Minutes",
            "A presentation layout can be made in just a few minutes.",
        ),
        (
            "Your first HTTPS certificate renewal: issue, install, check",
            "Browsers rely on a valid certificate when connecting to a website.",
        ),
    ],
)
def test_reported_frontend_false_positives_do_not_pass(title, summary):
    assert not topic_matches("Frontend Developer", title, summary)


@pytest.mark.parametrize(
    "title",
    [
        "The Gamepad API Lies to You: A Practical Guide to Reading Controller Input in JavaScript",
        "How to Use the Fullscreen API in JavaScript (and Keep the Screen Awake with the Wake Lock API)",
    ],
)
def test_browser_apis_do_not_pass_backend_pathway_without_backend_context(title):
    assert not topic_matches("Backend/Python Developer", title)


@pytest.mark.parametrize(
    "title",
    [
        "How to Choose the Best React JS Development Company in the UK",
        "A free SEO audit API for developers: score any URL with one request",
        "DEV! Breaking my lurking streak to introduce myself",
    ],
)
def test_community_promo_titles_are_excluded(title):
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


def test_fcc_git_feed_has_no_frontend_keyword_match():
    config = load_config()
    frontend_terms = config["pathways"]["Frontend Developer"]["keywords"]
    assert "git" not in frontend_terms
    assert "github" not in frontend_terms
    assert not topic_matches("Frontend Developer", "Learn Git and GitHub")


def test_html_is_removed_before_matching():
    assert plain_text("<script>sql</script><p>Useful <b>Python</b> guide</p>") == (
        "sql Useful Python guide"
    )
    assert topic_matches(
        "Backend/Python Developer",
        "A guide",
        "<p>Useful <b>Python</b> basics</p>",
    )


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
