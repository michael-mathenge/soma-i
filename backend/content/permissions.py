"""Fail-closed approval evidence for live feed access and public excerpt reuse."""

from datetime import date, timedelta

from content.fetching import validate_feed_url

MAX_PERMISSION_AGE = timedelta(days=90)


class FeedPermissionError(ValueError):
    pass


def approved_feed_urls(feed, today):
    """Return reviewed exact endpoints, never infer permission from a rights string."""
    permission = feed.get("permissions")
    if not isinstance(permission, dict):
        raise FeedPermissionError("missing live-feed permission evidence")
    for field in ("feed_access", "metadata_reuse"):
        if permission.get(field) is not True:
            raise FeedPermissionError(
                "feed access and reuse must be explicitly approved"
            )
    # Excerpt reuse is a separate decision. A publisher may permit linking and
    # attribution without permitting republication, and content is published
    # as title, publisher and date unless this is explicitly granted.
    if not isinstance(permission.get("excerpt_reuse"), bool):
        raise FeedPermissionError("excerpt reuse must be recorded as a decision")
    for field in ("reviewed_by", "scope", "evidence_url"):
        value = permission.get(field)
        if not isinstance(value, str) or not value.strip():
            raise FeedPermissionError(
                "permission evidence lacks reviewer, scope or link"
            )
    try:
        validate_feed_url(permission["evidence_url"])
        reviewed = date.fromisoformat(permission["reviewed_on"])
        expires = date.fromisoformat(permission["expires_on"])
    except (ValueError, TypeError, KeyError) as exc:
        raise FeedPermissionError("invalid permission link or review dates") from exc
    if not reviewed <= today <= expires or expires - reviewed > MAX_PERMISSION_AGE:
        raise FeedPermissionError(
            "permission review is future-dated, expired or too old"
        )
    urls = permission.get("allowed_urls")
    if not isinstance(urls, list) or not 1 <= len(urls) <= 6:
        raise FeedPermissionError(
            "permission needs one to six exact approved endpoints"
        )
    try:
        for url in urls:
            validate_feed_url(url)
        if feed["url"] not in urls:
            raise FeedPermissionError("registry endpoint is not approved")
    except (ValueError, TypeError, KeyError) as exc:
        raise FeedPermissionError("invalid approved endpoint list") from exc
    return frozenset(urls)
