import hashlib
import re
import runpy
import socket
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from learners.models import Account, AccountToken

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-original-otter-638!"
NEW_PASSWORD = "Synthetic-replaced-badger-291!"


@pytest.fixture(autouse=True)
def offline_memory(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Network is forbidden in recovery tests")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    with override_settings(SOMA_ENV="test", SOMA_ACCOUNT_EMAIL_MODE="memory"):
        yield


def client():
    result = APIClient(enforce_csrf_checks=True)
    result.credentials(HTTP_X_CSRFTOKEN=result.get("/api/csrf/").data["csrf_token"])
    return result


@pytest.fixture
def identity():
    user = get_user_model().objects.create_user(
        username="synthetic-owner", email="owner@example.test", password=PASSWORD
    )
    return Account.objects.create(user=user, email=user.email)


def signed_in(identity):
    result = client()
    result.force_login(identity.user)
    return result


def token_from_message():
    return re.search(r"#token=([a-f0-9]{64})", mail.outbox[-1].body).group(1)


def verification(identity):
    result = signed_in(identity)
    assert (
        result.post("/api/account/verify/request/", {}, format="json").status_code
        == 202
    )
    return token_from_message()


def reset_token(identity):
    if not identity.email_verified_at:
        identity.email_verified_at = timezone.now()
        identity.save(update_fields=["email_verified_at"])
    assert (
        client()
        .post("/api/account/reset/request/", {"email": identity.email}, format="json")
        .status_code
        == 202
    )
    return token_from_message()


def test_verification_stores_only_hash_and_requires_explicit_post(identity):
    raw = verification(identity)
    record = AccountToken.objects.get()
    assert record.digest == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in str(record.__dict__)
    assert record.purpose == "verify"
    assert 86390 < (record.expires_at - record.created_at).total_seconds() <= 86400
    result = client()
    assert result.get("/api/account/verify/confirm/", {"token": raw}).status_code == 405
    identity.refresh_from_db()
    assert identity.email_verified_at is None
    response = result.post(
        "/api/account/verify/confirm/", {"token": raw}, format="json"
    )
    assert response.status_code == 200
    identity.refresh_from_db()
    assert identity.email_verified_at is not None
    assert result.get("/api/account/").data == {"authenticated": False}
    assert (
        result.post(
            "/api/account/verify/confirm/", {"token": raw}, format="json"
        ).status_code
        == 400
    )
    assert signed_in(identity).get("/api/account/").data["email_verified"] is True


def test_preview_uses_fixed_fragment_link_and_explicit_memory_backend(identity, capsys):
    with override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"):
        raw = verification(identity)
    message = mail.outbox[-1]
    assert message.to == [identity.email]
    assert "http://127.0.0.1:4177/account/verify#token=" + raw in message.body
    assert PASSWORD not in message.body
    assert raw not in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["disabled", "smtp", "brevo", "console"])
def test_unsupported_delivery_modes_never_issue_tokens(identity, mode):
    with override_settings(SOMA_ACCOUNT_EMAIL_MODE=mode):
        result = signed_in(identity)
        assert result.get("/api/account/recovery/options/").data["available"] is False
        assert result.post("/api/account/verify/request/").status_code == 503
        assert (
            result.post("/api/account/reset/confirm/", {"token": "a" * 64}).status_code
            == 503
        )
    assert not AccountToken.objects.exists()


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_deployed_runtime_never_enables_memory_delivery(identity, mode):
    with override_settings(SOMA_ENV=mode):
        result = signed_in(identity)
        assert result.get("/api/account/recovery/options/").data == {
            "available": False,
            "mode": "disabled",
            "live_delivery": False,
        }
        assert result.post("/api/account/verify/request/").status_code == 503
    assert not AccountToken.objects.exists()


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_settings_reject_deployed_preview_without_database_connection(
    mode, monkeypatch
):
    import os

    import soma.configuration

    values = {"SOMA_ACCOUNT_EMAIL_MODE": "memory"}
    with (
        patch.object(soma.configuration, "load_local_environment", return_value=values),
        patch.object(
            soma.configuration, "load_configuration", return_value={"SOMA_ENV": mode}
        ),
        patch.object(os, "environ", {}),
    ):
        with pytest.raises(ImproperlyConfigured, match="SOMA_ACCOUNT_EMAIL_MODE"):
            runpy.run_path(str(settings.BASE_DIR / "soma/settings.py"))


def test_csrf_required_on_all_recovery_writes(identity):
    result = APIClient(enforce_csrf_checks=True)
    for path in ["verify/request", "reset/request", "verify/confirm", "reset/confirm"]:
        assert (
            result.post(f"/api/account/{path}/", {}, format="json").status_code == 403
        )


def test_verification_request_uses_current_owner_not_supplied_email(identity):
    other_user = get_user_model().objects.create_user(
        username="other", password=PASSWORD
    )
    other = Account.objects.create(user=other_user, email="other@example.test")
    result = signed_in(identity)
    response = result.post(
        "/api/account/verify/request/",
        {"email": other.email, "account_id": other.pk},
        format="json",
    )
    assert response.status_code == 202
    assert mail.outbox[-1].to == [identity.email]
    assert AccountToken.objects.get().account_id == identity.pk
    assert client().post("/api/account/verify/request/").status_code == 401


def test_recovery_request_is_generic_for_unknown_unverified_inactive_and_malformed(
    identity,
):
    result = client()
    responses = []
    for email in [identity.email, "unknown@example.test", "invalid", [], None]:
        response = result.post(
            "/api/account/reset/request/", {"email": email}, format="json"
        )
        responses.append(response.data)
        assert response.status_code == 202
    identity.email_verified_at = timezone.now()
    identity.save()
    identity.user.is_active = False
    identity.user.save()
    responses.append(
        result.post(
            "/api/account/reset/request/", {"email": identity.email}, format="json"
        ).data
    )
    assert all(response == responses[0] for response in responses)
    assert not AccountToken.objects.exists()
    assert len(mail.outbox) == 0


def test_reset_changes_password_invalidates_sessions_and_never_auto_logs_in(identity):
    first = signed_in(identity)
    second = signed_in(identity)
    raw = reset_token(identity)
    record = AccountToken.objects.get()
    assert 1790 < (record.expires_at - record.created_at).total_seconds() <= 1800
    anonymous = client()
    response = anonymous.post(
        "/api/account/reset/confirm/",
        {"token": raw, "password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    identity.user.refresh_from_db()
    assert identity.user.check_password(NEW_PASSWORD)
    assert not identity.user.check_password(PASSWORD)
    assert anonymous.get("/api/account/").data == {"authenticated": False}
    assert first.get("/api/account/").data == {"authenticated": False}
    assert second.get("/api/account/").data == {"authenticated": False}
    assert (
        anonymous.post(
            "/api/account/reset/confirm/",
            {"token": raw, "password": PASSWORD},
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.parametrize("purpose", ["verify", "reset"])
def test_expiry_and_replacement_make_old_tokens_unusable(identity, purpose):
    make = verification if purpose == "verify" else reset_token
    raw = make(identity)
    result = client()
    AccountToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert (
        result.post(
            f"/api/account/{purpose}/confirm/",
            {"token": raw, "password": NEW_PASSWORD},
            format="json",
        ).status_code
        == 400
    )
    previous = make(identity)
    current = make(identity)
    assert previous != current
    assert (
        result.post(
            f"/api/account/{purpose}/confirm/",
            {"token": previous, "password": NEW_PASSWORD},
            format="json",
        ).status_code
        == 400
    )
    assert (
        result.post(
            f"/api/account/{purpose}/confirm/",
            {"token": current, "password": NEW_PASSWORD},
            format="json",
        ).status_code
        == 200
    )


def test_wrong_purpose_foreign_user_and_token_tampering_rejected(identity):
    raw = verification(identity)
    result = client()
    assert (
        result.post(
            "/api/account/reset/confirm/",
            {"token": raw, "password": NEW_PASSWORD},
            format="json",
        ).status_code
        == 400
    )
    other_user = get_user_model().objects.create_user(
        username="other", password=PASSWORD
    )
    other = Account.objects.create(user=other_user, email="other@example.test")
    assert (
        signed_in(other)
        .post("/api/account/verify/confirm/", {"token": raw}, format="json")
        .status_code
        == 400
    )
    changed = ("a" if raw[0] != "a" else "b") + raw[1:]
    assert (
        result.post(
            "/api/account/verify/confirm/", {"token": changed}, format="json"
        ).status_code
        == 400
    )
    assert AccountToken.objects.get().used_at is None


@pytest.mark.parametrize("change", ["email", "password", "inactive", "deleted"])
def test_account_state_changes_invalidate_token(identity, change):
    raw = verification(identity)
    if change == "email":
        identity.email = "changed@example.test"
        identity.save()
    elif change == "password":
        identity.user.set_password(NEW_PASSWORD)
        identity.user.save()
    elif change == "inactive":
        identity.user.is_active = False
        identity.user.save()
    else:
        identity.user.delete()
    assert (
        client()
        .post("/api/account/verify/confirm/", {"token": raw}, format="json")
        .status_code
        == 400
    )


@pytest.mark.parametrize(
    "password", [None, [], "short", "1" * 20, "a" * 129, "password1234"]
)
def test_reset_rejects_weak_password_without_consuming_token(identity, password):
    raw = reset_token(identity)
    result = client()
    assert (
        result.post(
            "/api/account/reset/confirm/",
            {"token": raw, "password": password},
            format="json",
        ).status_code
        == 400
    )
    assert AccountToken.objects.get().used_at is None
    identity.user.refresh_from_db()
    assert identity.user.check_password(PASSWORD)


@pytest.mark.parametrize("value", [None, [], "", "a" * 65, "Z" * 64])
def test_invalid_token_shapes_fail_safely(value):
    response = client().post(
        "/api/account/verify/confirm/", {"token": value}, format="json"
    )
    assert response.status_code == 400


def test_memory_delivery_failure_rolls_back_token_and_never_exposes_secret(
    identity, monkeypatch
):
    import learners.recovery

    def fail(*args):
        raise RuntimeError("private-secret-not-for-response")

    monkeypatch.setattr(learners.recovery, "deliver_preview", fail)
    response = signed_in(identity).post(
        "/api/account/verify/request/", {}, format="json"
    )
    assert response.status_code == 503
    assert "private-secret" not in str(response.data)
    assert not AccountToken.objects.exists()


def test_private_no_store_headers_and_no_tokens_in_api_responses(identity):
    result = signed_in(identity)
    for path in ["/api/account/recovery/options/", "/api/account/verify/request/"]:
        response = result.get(path) if path.endswith("options/") else result.post(path)
        assert response["Cache-Control"] == "private, no-store"
        assert "token" not in response.data


@pytest.mark.django_db(transaction=True)
def test_recovery_migration_preserves_identity_owner_and_profile_data(identity):
    from learners.models import LearnerProfile

    profile = LearnerProfile.objects.create(
        owner=identity.user, display_name="Retained learner"
    )
    identity_id, profile_id, user_id = identity.pk, profile.pk, identity.user_id
    executor = MigrationExecutor(connection)
    executor.migrate([("learners", "0003_account_ownership")])
    try:
        old = executor.loader.project_state(
            [("learners", "0003_account_ownership")]
        ).apps
        assert (
            old.get_model("learners", "Account").objects.get(pk=identity_id).email
            == "owner@example.test"
        )
        assert (
            old.get_model("learners", "LearnerProfile")
            .objects.get(pk=profile_id)
            .owner_id
            == user_id
        )
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
    assert Account.objects.get(pk=identity_id).email_verified_at is None
    assert LearnerProfile.objects.get(pk=profile_id).display_name == "Retained learner"
