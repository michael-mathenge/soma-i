from datetime import UTC, datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_old_feed_rows_receive_only_safe_metadata_backfill():
    latest_targets = MigrationExecutor(connection).loader.graph.leaf_nodes()
    old_target = [("content", "0001_initial")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    old_apps = executor.loader.project_state(old_target).apps
    OldSource = old_apps.get_model("content", "Source")
    OldItem = old_apps.get_model("content", "Item")
    old_date = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    old_sources = [
        OldSource.objects.create(
            name=name,
            url=f"https://{slug}.example.test/feed.xml",
            credibility_note="Legacy source",
        )
        for name, slug in (
            ("MIT News Research", "mit-news"),
            ("MDN Blog", "mdn"),
            ("freeCodeCamp React", "fcc-react"),
        )
    ]
    old_items = [
        OldItem.objects.create(
            title=f"Legacy item from {source.name}",
            url=f"https://EXAMPLE.test/{slug}/?utm_source=old#section",
            summary="Legacy summary",
            published_at=old_date,
            source=source,
        )
        for source, slug in zip(old_sources, ("mit", "mdn", "fcc"), strict=True)
    ]
    collision_items = [
        OldItem.objects.create(
            pk=20,
            title="Inserted first tracking collision",
            url="https://example.test/tracking?utm_source=first",
            summary="Legacy summary",
            published_at=old_date,
            source=old_sources[0],
        ),
        OldItem.objects.create(
            pk=10,
            title="Lowest id tracking collision",
            url="https://example.test/tracking?utm_source=second",
            summary="Legacy summary",
            published_at=old_date,
            source=old_sources[0],
        ),
        OldItem.objects.create(
            pk=40,
            title="Inserted first slash collision",
            url="https://example.test/trailing/",
            summary="Legacy summary",
            published_at=old_date,
            source=old_sources[1],
        ),
        OldItem.objects.create(
            pk=30,
            title="Lowest id slash collision",
            url="https://example.test/trailing",
            summary="Legacy summary",
            published_at=old_date,
            source=old_sources[1],
        ),
    ]

    try:
        latest_executor = MigrationExecutor(connection)
        latest_executor.migrate(latest_targets)
        latest_apps = latest_executor.loader.project_state(latest_targets).apps
        Item = latest_apps.get_model("content", "Item")

        expected_links = (
            "https://example.test/mit",
            "https://example.test/mdn",
            "https://example.test/fcc",
        )
        for old_item, expected_link in zip(old_items, expected_links, strict=True):
            item = Item.objects.get(pk=old_item.pk)
            assert item.date_source is None
            assert item.fetched_at is None
            assert item.word_count is None
            assert item.pathway_keys == []
            assert item.url.endswith("?utm_source=old#section")
            assert item.normalized_link == expected_link

        assert Item.objects.count() == len(old_items) + len(collision_items)
        expected_collisions = {
            10: "https://example.test/tracking",
            20: None,
            30: "https://example.test/trailing",
            40: None,
        }
        for item_id, expected_link in expected_collisions.items():
            assert Item.objects.get(pk=item_id).normalized_link == expected_link

        from content.ingestion import ingest_entries
        from content.models import Source as CurrentSource

        before_ingest = Item.objects.count()
        ingest_entries(
            CurrentSource.objects.get(pk=old_sources[0].pk),
            {
                "name": "MIT News Research",
                "url": "https://mit-news.example.test/feed.xml",
                "source_type": "nonprofit",
                "pathways": ["Data Analyst"],
            },
            [
                {
                    "title": "SQL basics",
                    "link": "https://example.test/tracking/?utm_medium=later",
                    "summary": "Learn SQL basics",
                }
            ],
            old_date,
        )
        assert Item.objects.count() == before_ingest
    finally:
        MigrationExecutor(connection).migrate(latest_targets)
