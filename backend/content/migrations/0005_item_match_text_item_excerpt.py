"""Publish content as title, publisher and date instead of stored excerpts.

The stored summary becomes internal matching text that the API never
returns. Excerpts become a separate field that stays empty until a
review confirms permission to republish the text, so no unverified
publisher text is carried or shown by default.
"""

from django.db import migrations, models


def clear_stored_excerpts(apps, schema_editor):
    """Move stored feed text into internal matching text and drop it."""
    Item = apps.get_model("content", "Item")
    for item in Item.objects.all().iterator(chunk_size=500):
        item.match_text = item.summary
        item.excerpt = ""
        item.save(update_fields=["match_text", "excerpt"])


def restore_summary_column(apps, schema_editor):
    """Restore the previous column name for an in-place rollback."""
    Item = apps.get_model("content", "Item")
    for item in Item.objects.all().iterator(chunk_size=500):
        item.summary = item.match_text
        item.save(update_fields=["summary"])


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0004_item_topic_tags_resource_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="match_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="item",
            name="excerpt",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(clear_stored_excerpts, restore_summary_column),
        migrations.RemoveField(
            model_name="item",
            name="summary",
        ),
    ]
