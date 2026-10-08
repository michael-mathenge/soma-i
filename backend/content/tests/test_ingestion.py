import json
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import feedparser
import pytest
from rest_framework.test import APIClient

from content.fetching import MAX_FEED_BYTES, FetchResponse, fetch_feed
from content.ingestion import (
    clean_summary,
    entry_date,
    feed_staleness,
    ingest_entries,
    items_for_pathway,
    normalize_link,
    staleness_for,
    word_count_for_entry,
)
from content.matching import exclusion_reason, load_config
from content.models import Item, Skill, Source
from learners.models import LearnerProfile
from pathways.models import Checkpoint, Pathway, PathwaySkill

pytestmark = pytest.mark.django_db

FETCHED_AT = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
REFERENCE_DATE = date(2026, 10, 8)

DATA_FEED = {
    "key": "test_data",
    "name": "Test Data feed",
    "url": "https://data.example.test/feed.xml",
    "source_type": "nonprofit",
    "pathways": ["Data Analyst"],
    "stale_after_days": 60,
    "attribution": "Test Data",
    "rights": "not stated",
    "level": "mixed",
}
FRONTEND_FEED = {
    "key": "test_frontend",
    "name": "Test Frontend feed",
    "url": "https://frontend.example.test/feed.xml",
    "source_type": "publisher",
    "pathways": ["Frontend Developer"],
    "stale_after_days": 60,
    "attribution": "Test Frontend",
    "rights": "not stated",
    "level": "mixed",
}


def make_source(feed=DATA_FEED, **overrides):
    values = {
        "name": feed["name"],
        "url": feed["url"],
        "credibility_note": f"RSS feed attributed to {feed['attribution']}.",
        "attribution": feed["attribution"],
        "rights": feed["rights"],
        "level": feed["level"],
    }
    values.update(overrides)
    return Source.objects.create(**values)


def make_entry(
    title="SQL basics",
    link="https://example.test/sql-basics",
    summary="An introduction to SQL queries.",
    guid="",
    published_parsed=None,
    updated_parsed=None,
    **extra,
):
    entry = {"title": title, "link": link, "summary": summary}
    if guid:
        entry["id"] = guid
    if published_parsed:
        entry["published_parsed"] = published_parsed
    if updated_parsed:
        entry["updated_parsed"] = updated_parsed
    entry.update(extra)
    return entry


def test_fixture_ingestion_deduplicates_links_and_keeps_skill_tags():
    fixture = Path(__file__).parent / "fixtures" / "feed.xml"
    parsed = feedparser.parse(fixture.read_bytes())
    feed = {**DATA_FEED, "pathways": ["Data Analyst", "Frontend Developer"]}
    source = make_source(feed)

    result = ingest_entries(source, feed, parsed.entries, FETCHED_AT)
    repeated = ingest_entries(source, feed, parsed.entries, FETCHED_AT)

    assert result["created"] == 2
    assert result["duplicates_merged"] == 1
    assert repeated["created"] == 0
    assert repeated["duplicates_merged"] == 3
    items = list(source.items.order_by("title"))
    assert len(items) == 2
    assert all(item.source_id == source.pk and item.fetched_at for item in items)
    sql = next(item for item in items if "SQL" in item.title)
    assert sql.date_source == "published"
    assert "SQL" in list(sql.skills.values_list("name", flat=True))
    assert "Statistics" in list(sql.skills.values_list("name", flat=True))
    html = next(item for item in items if "HTML" in item.title)
    assert "HTML" in list(html.skills.values_list("name", flat=True))


def test_entry_date_prefers_published_then_updated_then_injected_fetch_time():
    published = (2026, 9, 1, 10, 0, 0, 1, 244, 0)
    updated = (2026, 9, 3, 10, 0, 0, 3, 246, 0)
    value, source = entry_date(
        {"published_parsed": published, "updated_parsed": updated}, FETCHED_AT
    )
    assert value == datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    assert source == "published"

    value, source = entry_date({"updated_parsed": updated}, FETCHED_AT)
    assert value == datetime(2026, 9, 3, 10, 0, tzinfo=UTC)
    assert source == "updated"

    value, source = entry_date({}, FETCHED_AT)
    assert value == FETCHED_AT
    assert source == "fetched"


def test_offline_fixture_date_source_is_honoured():
    updated_at, source = entry_date(
        {"date": "2026-10-01T12:00:00+00:00", "date_source": "updated"},
        FETCHED_AT,
    )
    assert updated_at == datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    assert source == "updated"

    fetched_at, source = entry_date(
        {"date": None, "date_source": "fetched"}, FETCHED_AT
    )
    assert fetched_at == FETCHED_AT
    assert source == "fetched"


def test_rfc822_and_iso_fixture_dates_parse_without_clock_reads():
    rss_fixture = Path(__file__).parent / "fixtures" / "feed.xml"
    rfc_entry = feedparser.parse(rss_fixture.read_bytes()).entries[0]
    rfc_value, rfc_source = entry_date(rfc_entry, FETCHED_AT)
    assert rfc_value == datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    assert rfc_source == "published"
    fixture_rfc_value, fixture_rfc_source = entry_date(
        {"date": "Tue, 01 Sep 2026 10:00:00 GMT"}, FETCHED_AT
    )
    assert fixture_rfc_value == rfc_value
    assert fixture_rfc_source == "published"

    iso_value, iso_source = entry_date(
        {"date": "2026-10-08T12:00:00+00:00"}, FETCHED_AT
    )
    assert iso_value == datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    assert iso_source == "published"


def test_summary_only_entries_store_null_word_count_and_plain_excerpt():
    source = make_source()
    entry = make_entry(summary="<p>SQL basics and a short guide.</p>")
    result = ingest_entries(source, DATA_FEED, [entry], FETCHED_AT)
    item = source.items.get()

    assert result["created"] == 1
    assert item.word_count is None
    assert item.summary == "SQL basics and a short guide."
    assert clean_summary("<b>plain</b> text") == "plain text"


def test_full_content_sets_word_count_without_storing_article_text():
    source = make_source()
    entry = make_entry(
        summary="Short SQL summary.",
        content=[{"type": "text/html", "value": "<p>alpha beta SQL delta</p>"}],
    )
    ingest_entries(source, DATA_FEED, [entry], FETCHED_AT)
    item = source.items.get()

    assert item.word_count == 4
    assert item.summary == "Short SQL summary."
    assert not hasattr(item, "content")
    assert word_count_for_entry(entry) == 4


def test_same_guid_in_different_feeds_does_not_merge_unrelated_items():
    source_a = make_source(DATA_FEED)
    source_b = make_source(FRONTEND_FEED)
    first_link = "https://EXAMPLE.test/article/?utm_source=one#intro"
    first = make_entry(title="SQL basics", link=first_link, guid="shared-guid")
    same_feed_guid = make_entry(
        title="SQL query guide",
        link="https://example.test/different-link",
        guid="shared-guid",
    )
    unrelated_cross_feed_guid = make_entry(
        title="CSS layout fundamentals",
        link="https://example.test/another-item",
        guid="shared-guid",
        summary="A CSS layout overview.",
    )
    cross_feed_same_link = make_entry(
        title="CSS layout fundamentals",
        link="https://example.test/article/",
        guid="different-guid",
        summary="A CSS layout overview.",
    )
    registry = {**load_config(), "feeds": [DATA_FEED, FRONTEND_FEED]}

    first_result = ingest_entries(
        source_a, DATA_FEED, [first, same_feed_guid], FETCHED_AT, registry
    )
    second_result = ingest_entries(
        source_b,
        FRONTEND_FEED,
        [unrelated_cross_feed_guid, cross_feed_same_link],
        FETCHED_AT,
        registry,
    )

    items = list(Item.objects.order_by("pk"))
    assert first_result["created"] == 1
    assert first_result["duplicates_merged"] == 1
    assert second_result["created"] == 1
    assert second_result["duplicates_merged"] == 1
    assert len(items) == 2
    shared = Item.objects.get(normalized_link=normalize_link(first_link))
    assert shared.source_id == source_a.pk
    assert shared.url == first_link
    assert shared.pathway_keys == ["Data Analyst", "Frontend Developer"]
    assert Item.objects.filter(guid="shared-guid").count() == 2


@pytest.mark.parametrize(
    ("first_link", "second_link"),
    [
        ("http://EXAMPLE.test/article", "https://example.test/article/"),
        ("https://EXAMPLE.test/article/", "http://example.test/article"),
    ],
)
def test_link_normalization_only_changes_dedupe_key_and_preserves_original_url(
    first_link, second_link
):
    source_a = make_source(DATA_FEED)
    source_b = make_source(FRONTEND_FEED)
    registry = {**load_config(), "feeds": [DATA_FEED, FRONTEND_FEED]}
    title = "SQL and CSS basics"
    summary = "A beginner guide to SQL and CSS."

    ingest_entries(
        source_a,
        DATA_FEED,
        [
            make_entry(
                title=title,
                link=first_link,
                summary=summary,
                published_parsed=(2026, 9, 1, 10, 0, 0, 1, 244, 0),
            )
        ],
        FETCHED_AT,
        registry,
    )
    result = ingest_entries(
        source_b,
        FRONTEND_FEED,
        [
            make_entry(
                title=title,
                link=second_link,
                summary=summary,
                updated_parsed=(2026, 9, 2, 10, 0, 0, 2, 245, 0),
            )
        ],
        FETCHED_AT,
        registry,
    )

    assert result["created"] == 0
    assert result["duplicates_merged"] == 1
    assert Item.objects.count() == 1
    item = Item.objects.get()
    assert item.url == first_link
    assert item.source_id == source_a.pk
    assert item.date_source == "published"
    assert item.normalized_link == normalize_link(second_link)


def test_normalize_link_strips_default_http_and_https_ports():
    assert normalize_link("http://example.test:80/path") == "https://example.test/path"
    assert (
        normalize_link("https://example.test:443/path") == "https://example.test/path"
    )


def test_reparsing_same_feed_content_is_idempotent():
    source = make_source()
    entry = make_entry(title="SQL analysis basics", guid="stable-guid")

    first = ingest_entries(source, DATA_FEED, [entry], FETCHED_AT)
    second = ingest_entries(source, DATA_FEED, [entry], FETCHED_AT + timedelta(hours=1))

    assert first["created"] == 1
    assert second["created"] == 0
    assert second["duplicates_merged"] == 1
    assert Item.objects.count() == 1


def test_pathway_items_are_queryable_on_sqlite_without_json_contains():
    source = make_source()
    ingest_entries(
        source,
        DATA_FEED,
        [make_entry(title="SQL analysis basics")],
        FETCHED_AT,
    )
    item = source.items.get()

    assert items_for_pathway("Data Analyst") == [item]
    assert items_for_pathway("Frontend Developer") == []


def test_undated_source_is_stale_with_no_dates_reason():
    source = make_source()

    result = staleness_for(source, REFERENCE_DATE, 60)

    assert result == {"stale": True, "reason": "no dates", "age_days": None}


def test_feed_uses_its_own_stale_after_days_value():
    source = make_source(latest_item_at=FETCHED_AT - timedelta(days=10))
    short_threshold = {**DATA_FEED, "stale_after_days": 5}
    long_threshold = {**DATA_FEED, "stale_after_days": 60}

    assert feed_staleness(source, short_threshold, REFERENCE_DATE)["reason"] == "age"
    assert not feed_staleness(source, long_threshold, REFERENCE_DATE)["stale"]


def test_staleness_uses_content_date_not_fetch_time():
    source = make_source(latest_item_at=FETCHED_AT - timedelta(days=61))
    result = staleness_for(source, REFERENCE_DATE, 60)
    assert result == {"stale": True, "reason": "age", "age_days": 61}


def test_api_computes_staleness_on_read_with_injected_reference_date():
    from learners.api import item_json

    source = make_source(latest_item_at=FETCHED_AT - timedelta(days=61))
    item = Item.objects.create(
        title="SQL basics",
        url="https://example.test/sql-read-stale",
        normalized_link="https://example.test/sql-read-stale",
        published_at=FETCHED_AT - timedelta(days=61),
        date_source="published",
        pathway_keys=["Data Analyst"],
        source=source,
    )

    response = item_json(item, reference_date=REFERENCE_DATE)

    assert response["source_stale"] is True
    assert response["source_stale_reason"] == "age"
    assert response["age_days"] == 61


def test_bozo_feed_with_partial_entries_is_usable_and_empty_malformed_feed_fails(
    monkeypatch,
):
    import content.management.commands.ingest_feeds as command_module

    partial = SimpleNamespace(
        bozo=True,
        entries=[make_entry()],
        bozo_exception=ValueError("malformed tail"),
    )
    monkeypatch.setattr(command_module.feedparser, "parse", lambda _: partial)
    response = FetchResponse(200, {"Content-Type": "application/rss+xml"}, b"bad feed")

    entries, warning = command_module.parse_feed_response(response)
    assert entries == partial.entries
    assert warning == "malformed tail"

    malformed = SimpleNamespace(bozo=True, entries=[], bozo_exception=ValueError("bad"))
    monkeypatch.setattr(command_module.feedparser, "parse", lambda _: malformed)
    with pytest.raises(command_module.FeedResponseError, match="Malformed feed"):
        command_module.parse_feed_response(response)


def test_normalized_link_lowercases_host_strips_fragment_and_tracking_and_slash():
    actual = normalize_link(
        "HTTPS://EXAMPLE.TEST/Guide/?utm_source=feed&ref=home#section"
    )
    assert actual == "https://example.test/Guide?ref=home"
    assert normalize_link("HTTP://EXAMPLE.TEST/Guide/") == "https://example.test/Guide"


def test_command_offline_ingests_fixtures_without_calling_fetcher(monkeypatch):
    import content.management.commands.ingest_feeds as command_module

    command = command_module.Command()
    command.clock = lambda: FETCHED_AT
    command.fetcher = lambda *_args, **_kwargs: pytest.fail("offline called fetcher")
    command.stdout = StringIO()
    command.stderr = StringIO()

    command.handle(offline=True, force=False, reference_date=REFERENCE_DATE)

    output = command.stdout.getvalue()
    for pathway in load_config()["pathways"]:
        assert f"{pathway}: " in output
        assert items_for_pathway(pathway)
    assert "date_source published=" in output
    assert "Stale feeds:" in output
    realpython_url = next(
        feed["url"] for feed in load_config()["feeds"] if feed["key"] == "realpython"
    )
    assert (
        Item.objects.filter(source__url=realpython_url, date_source="updated").count()
        == 10
    )
    fixture_paths = list((Path(__file__).parent / "fixtures" / "feeds").glob("*.json"))
    assert len(fixture_paths) == len(load_config()["feeds"])
    for fixture_path in fixture_paths:
        rows = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert 10 <= len(rows) <= 12
        assert all(
            set(row)
            == {"title", "link", "date", "date_source", "excerpt", "attribution"}
            for row in rows
        )
        assert all(
            row["date_source"] in {"published", "updated", "fetched"} for row in rows
        )


def test_offline_fixture_excerpts_are_limited_to_200_characters():
    fixture_paths = (Path(__file__).parent / "fixtures" / "feeds").glob("*.json")
    for fixture_path in fixture_paths:
        rows = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert all(len(row["excerpt"]) <= 200 for row in rows), fixture_path.name


def test_fixtures_keep_ten_nonexcluded_items_and_two_real_quiz_examples():
    config = load_config()
    feeds = {feed["key"]: feed for feed in config["feeds"]}
    fixture_dir = Path(__file__).parent / "fixtures" / "feeds"

    for key, feed in feeds.items():
        rows = json.loads((fixture_dir / f"{key}.json").read_text(encoding="utf-8"))
        excluded = [
            row
            for row in rows
            if exclusion_reason(row["title"], feed["source_type"], config)
        ]
        assert len(rows) - len(excluded) == 10
        assert len(excluded) == (2 if key == "realpython" else 0)
        if key == "realpython":
            assert all(row["title"].startswith("Quiz:") for row in excluded)


def test_live_failure_does_not_prevent_later_feed_ingestion(monkeypatch):
    import content.management.commands.ingest_feeds as command_module

    feeds = [{**DATA_FEED}, {**FRONTEND_FEED}]
    config = {**load_config(), "feeds": feeds}
    monkeypatch.setattr(command_module, "load_config", lambda: config)
    valid_fixture = (Path(__file__).parent / "fixtures" / "feed.xml").read_bytes()
    calls = []

    def fetcher(url, headers):
        calls.append(url)
        if url == feeds[0]["url"]:
            raise TimeoutError("request timed out")
        return FetchResponse(
            200, {"Content-Type": "application/rss+xml"}, valid_fixture
        )

    command = command_module.Command()
    command.clock = lambda: FETCHED_AT
    command.fetcher = fetcher
    command.stdout = StringIO()
    command.stderr = StringIO()
    command.handle(offline=False, force=True, reference_date=REFERENCE_DATE)

    assert calls == [feed["url"] for feed in feeds]
    assert "feed failed" in command.stderr.getvalue()
    assert "request timed out" in command.stderr.getvalue()
    assert Source.objects.get(url=feeds[1]["url"]).items.exists()


def test_html_instead_of_xml_fails_one_feed_and_continues(monkeypatch):
    import content.management.commands.ingest_feeds as command_module

    feeds = [{**DATA_FEED}, {**FRONTEND_FEED}]
    config = {**load_config(), "feeds": feeds}
    monkeypatch.setattr(command_module, "load_config", lambda: config)
    valid_fixture = (Path(__file__).parent / "fixtures" / "feed.xml").read_bytes()
    calls = []

    def fetcher(url, headers):
        calls.append(url)
        if url == feeds[0]["url"]:
            return FetchResponse(
                200, {"Content-Type": "text/html"}, b"<html>login</html>"
            )
        return FetchResponse(
            200, {"Content-Type": "application/rss+xml"}, valid_fixture
        )

    command = command_module.Command()
    command.clock = lambda: FETCHED_AT
    command.fetcher = fetcher
    command.stdout = StringIO()
    command.stderr = StringIO()
    command.handle(offline=False, force=True, reference_date=REFERENCE_DATE)

    assert calls == [feed["url"] for feed in feeds]
    assert "Response is HTML" in command.stderr.getvalue()
    assert Source.objects.get(url=feeds[1]["url"]).items.exists()


def test_malformed_feed_failure_does_not_prevent_later_feed_ingestion(monkeypatch):
    import content.management.commands.ingest_feeds as command_module

    feeds = [{**DATA_FEED}, {**FRONTEND_FEED}]
    config = {**load_config(), "feeds": feeds}
    monkeypatch.setattr(command_module, "load_config", lambda: config)
    valid_fixture = (Path(__file__).parent / "fixtures" / "feed.xml").read_bytes()
    parser_results = [
        SimpleNamespace(bozo=True, entries=[], bozo_exception=ValueError("bad XML")),
        feedparser.parse(valid_fixture),
    ]
    monkeypatch.setattr(
        command_module.feedparser, "parse", lambda _body: parser_results.pop(0)
    )
    calls = []

    def fetcher(url, _headers):
        calls.append(url)
        return FetchResponse(200, {"Content-Type": "application/rss+xml"}, b"<rss />")

    command = command_module.Command()
    command.clock = lambda: FETCHED_AT
    command.fetcher = fetcher
    command.stdout = StringIO()
    command.stderr = StringIO()
    command.handle(offline=False, force=True, reference_date=REFERENCE_DATE)

    assert calls == [feed["url"] for feed in feeds]
    assert "Malformed feed" in command.stderr.getvalue()
    assert Source.objects.get(url=feeds[1]["url"]).items.exists()


def test_recent_feed_is_skipped_and_force_bypasses_interval(monkeypatch):
    import content.management.commands.ingest_feeds as command_module

    config = {**load_config(), "feeds": [{**DATA_FEED}]}
    monkeypatch.setattr(command_module, "load_config", lambda: config)
    source = make_source(last_fetched_at=FETCHED_AT - timedelta(minutes=10))
    calls = []

    def fetcher(_url, headers):
        calls.append(headers)
        return FetchResponse(200, {"Content-Type": "application/rss+xml"}, b"")

    skipped = command_module.Command()
    skipped.clock = lambda: FETCHED_AT
    skipped.fetcher = fetcher
    skipped.stdout = StringIO()
    skipped.stderr = StringIO()
    skipped.handle(offline=False, force=False, reference_date=REFERENCE_DATE)
    assert not calls
    assert "minimum interval not elapsed" in skipped.stdout.getvalue()

    source.etag = '"v1"'
    source.last_modified = "Wed, 07 Oct 2026 12:00:00 GMT"
    source.save(update_fields=["etag", "last_modified"])
    forced = command_module.Command()
    forced.clock = lambda: FETCHED_AT
    forced.fetcher = fetcher
    forced.stdout = StringIO()
    forced.stderr = StringIO()
    forced.handle(offline=False, force=True, reference_date=REFERENCE_DATE)
    assert calls == [
        {
            "If-None-Match": '"v1"',
            "If-Modified-Since": "Wed, 07 Oct 2026 12:00:00 GMT",
        }
    ]
    assert Source.objects.get(pk=source.pk).last_fetched_at == FETCHED_AT
    parser = forced.create_parser("manage.py", "ingest_feeds")
    help_text = " ".join(parser.format_help().split())
    assert "--force" in help_text
    assert "conditional ETag/Last-Modified validators are still sent" in help_text


def test_304_sends_validators_and_does_not_reingest(monkeypatch):
    import content.management.commands.ingest_feeds as command_module

    config = {**load_config(), "feeds": [{**DATA_FEED}]}
    monkeypatch.setattr(command_module, "load_config", lambda: config)
    source = make_source(etag='"v1"', last_modified="Wed, 07 Oct 2026 12:00:00 GMT")
    ingest_entries(source, DATA_FEED, [make_entry()], FETCHED_AT)
    original_count = Item.objects.count()
    received_headers = {}

    def fetcher(_url, headers):
        received_headers.update(headers)
        return FetchResponse(304, {}, b"")

    command = command_module.Command()
    command.clock = lambda: FETCHED_AT + timedelta(hours=2)
    command.fetcher = fetcher
    command.stdout = StringIO()
    command.stderr = StringIO()
    command.handle(offline=False, force=False, reference_date=REFERENCE_DATE)

    assert received_headers["If-None-Match"] == '"v1"'
    assert received_headers["If-Modified-Since"] == "Wed, 07 Oct 2026 12:00:00 GMT"
    assert Item.objects.count() == original_count
    assert "304 Not Modified" in command.stdout.getvalue()


def test_html_title_survives_to_api_as_plain_text(monkeypatch):
    import learners.api as learner_api

    monkeypatch.setattr(learner_api.timezone, "localdate", lambda *_: REFERENCE_DATE)
    feed = {**DATA_FEED}
    source = make_source(feed)
    ingest_entries(
        source,
        feed,
        [make_entry(title='<img src=x onerror="alert(1)"> SQL basics')],
        FETCHED_AT,
    )
    sql = Skill.objects.get(slug="sql")
    pathway = Pathway.objects.create(
        title="Data Analyst",
        description="Data pathway",
        target_outcome="Junior Data Analyst",
    )
    step = PathwaySkill.objects.create(pathway=pathway, skill=sql, order=1)
    Checkpoint.objects.create(
        pathway_skill=step,
        title="SQL checkpoint",
        criteria="Use SQL",
        unlocks_text="Next step",
        quiz_json=[],
    )
    learner = LearnerProfile.objects.create(
        display_name="API test", chosen_pathway=pathway
    )
    client = APIClient()
    session = client.session
    session["learner_id"] = learner.pk
    session.save()

    response = client.get("/api/items/")

    assert response.status_code == 200
    assert response.data[0]["title"] == "SQL basics"
    assert response.data[0]["pathway_keys"] == ["Data Analyst"]
    assert response.data[0]["date_source"] == "fetched"
    assert "onerror" not in str(response.data)


def test_fetcher_rejects_http_and_oversize_responses(monkeypatch):
    import content.fetching as fetching

    with pytest.raises(ValueError, match="HTTPS"):
        fetch_feed("http://example.test/feed.xml")

    class FakeResponse:
        status = 200
        headers = {"Content-Length": str(MAX_FEED_BYTES + 1)}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _count):
            pytest.fail("oversize response should fail before reading")

    class FakeOpener:
        def open(self, _request, timeout):
            assert timeout == 10
            return FakeResponse()

    monkeypatch.setattr(fetching, "build_opener", lambda *_: FakeOpener())
    with pytest.raises(ValueError, match="5 MB"):
        fetch_feed("https://example.test/feed.xml")


def test_redirect_handler_limits_redirects_and_requires_https():
    from urllib.error import HTTPError
    from urllib.request import Request

    from content.fetching import LimitedHTTPSRedirectHandler

    assert LimitedHTTPSRedirectHandler.max_redirections == 5
    handler = LimitedHTTPSRedirectHandler()
    request = Request("https://example.test/feed.xml")
    request.redirect_dict = {f"https://example.test/{index}": 1 for index in range(5)}
    with pytest.raises(HTTPError, match="redirect error"):
        handler.http_error_302(
            request,
            None,
            302,
            "Found",
            {"location": "https://example.test/next.xml"},
        )

    with pytest.raises(ValueError, match="remain on HTTPS"):
        handler.redirect_request(
            Request("https://example.test/feed.xml"),
            None,
            301,
            "Moved",
            {},
            "http://example.test/feed.xml",
        )
