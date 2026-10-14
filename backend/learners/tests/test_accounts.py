import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework.test import APIClient

from learners.models import Account, LearnerProfile
from pathways.models import CheckpointRecord, ItemRecord, Pathway

pytestmark = pytest.mark.django_db
PASSWORD = "Independent-synthetic-otter-729!"


def client():
    result = APIClient(enforce_csrf_checks=True)
    token = result.get("/api/csrf/").data["csrf_token"]
    result.credentials(HTTP_X_CSRFTOKEN=token)
    return result


def rotate(result, response):
    if "csrf_token" in response.data:
        result.credentials(HTTP_X_CSRFTOKEN=response.data["csrf_token"])
    return response


def register(result, email="one@example.test", attach=False):
    return rotate(
        result,
        result.post(
            "/api/account/",
            {"email": email, "password": PASSWORD, "attach_guest": attach},
            format="json",
        ),
    )


def logout(result):
    return rotate(result, result.post("/api/account/logout/"))


def login(result, email="one@example.test", password=PASSWORD):
    return rotate(
        result,
        result.post(
            "/api/account/login/", {"email": email, "password": password}, format="json"
        ),
    )


@pytest.fixture
def guest():
    call_command("seed_demo", verbosity=0)
    result = client()
    response = result.post(
        "/api/me/",
        {
            "display_name": "Private guest",
            "pathway_id": Pathway.objects.get(title="Data Analyst").pk,
        },
        format="json",
    )
    assert response.status_code == 201
    return result, LearnerProfile.objects.get(pk=response.data["id"])


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/account/", "post"),
        ("/api/account/login/", "post"),
        ("/api/account/logout/", "post"),
        ("/api/account/", "delete"),
        ("/api/me/", "post"),
        ("/api/me/", "patch"),
        ("/api/me/", "delete"),
        ("/api/demo/", "post"),
        ("/api/items/1/done/", "post"),
        ("/api/checkpoints/1/skip/", "post"),
        ("/api/pathway/restart/", "post"),
    ],
)
def test_anonymous_unsafe_routes_require_csrf(path, method):
    response = getattr(APIClient(enforce_csrf_checks=True), method)(
        path, {}, format="json"
    )
    assert response.status_code == 403


def test_wrong_token_and_cross_origin_rejected(guest):
    result, profile = guest
    result.credentials(HTTP_X_CSRFTOKEN="x" * 64)
    assert result.patch("/api/me/", {"phone": "bad"}).status_code == 403
    result = client()
    assert (
        result.post(
            "/api/account/login/", {}, HTTP_ORIGIN="https://evil.example"
        ).status_code
        == 403
    )
    profile.refresh_from_db()
    assert profile.phone == ""


def test_registration_hashes_password_normalizes_email_and_rotates_session(guest):
    result, profile = guest
    old_key = result.session.session_key
    old_token = result.cookies["csrftoken"].value
    response = register(result, "  One@EXAMPLE.test  ", True)
    assert response.status_code == 201
    identity = Account.objects.get()
    assert identity.email == "one@example.test"
    assert identity.user.password != PASSWORD
    assert identity.user.check_password(PASSWORD)
    profile.refresh_from_db()
    assert profile.owner == identity.user
    assert result.session.session_key != old_key
    assert result.cookies["csrftoken"].value != old_token
    assert "learner_id" not in result.session
    assert result.get("/api/me/").data["id"] == profile.pk


def test_explicit_attachment_preserves_progress_ids(guest):
    result, profile = guest
    checkpoint = profile.chosen_pathway.steps.first().checkpoint
    record = CheckpointRecord.objects.create(
        learner=profile, checkpoint=checkpoint, status="done", quiz_answers=[1, 1, 1]
    )
    assert register(result, attach=True).status_code == 201
    assert CheckpointRecord.objects.get(pk=record.pk).learner_id == profile.pk
    assert result.get("/api/dashboard/").data["done"]


def test_registration_without_attachment_preserves_unowned_guest(guest):
    result, profile = guest
    assert register(result).status_code == 201
    profile.refresh_from_db()
    assert profile.owner is None
    assert result.get("/api/me/").status_code == 401
    response = result.post(
        "/api/me/", {"pathway_id": profile.chosen_pathway_id}, format="json"
    )
    assert response.status_code == 201
    assert response.data["id"] != profile.pk
    assert (
        LearnerProfile.objects.get(pk=response.data["id"]).owner_id
        == Account.objects.get().user_id
    )


def test_login_restores_owner_ignores_foreign_guest_and_session_id(guest):
    first, profile = guest
    register(first, attach=True)
    logout(first)
    other = client()
    other.post(
        "/api/me/",
        {"pathway_id": profile.chosen_pathway_id, "display_name": "Other"},
        format="json",
    )
    other_id = other.get("/api/me/").data["id"]
    old_key = other.session.session_key
    assert login(other).status_code == 200
    assert other.session.session_key != old_key
    assert other.get("/api/me/").data["id"] == profile.pk
    assert LearnerProfile.objects.get(pk=other_id).owner is None
    session = other.session
    session["learner_id"] = other_id
    session.save()
    assert other.get("/api/me/").data["id"] == profile.pk


def test_guest_cannot_reuse_attached_profile(guest):
    result, profile = guest
    stolen_guest = client()
    session = stolen_guest.session
    session["learner_id"] = profile.pk
    session.save()
    assert register(result, attach=True).status_code == 201
    assert stolen_guest.get("/api/me/").status_code == 401
    assert stolen_guest.patch("/api/me/", {"phone": "forged"}).status_code == 401
    assert register(stolen_guest, "two@example.test", True).status_code == 400


def test_two_accounts_isolate_profile_writes_and_deletion(guest):
    first, profile = guest
    register(first, attach=True)
    second = client()
    register(second, "two@example.test")
    response = second.post(
        "/api/me/",
        {
            "pathway_id": profile.chosen_pathway_id,
            "owner": profile.owner_id,
            "id": profile.pk,
        },
        format="json",
    )
    second_id = response.data["id"]
    assert second_id != profile.pk
    second.patch("/api/me/", {"phone": "second"}, format="json")
    profile.refresh_from_db()
    assert profile.phone == ""
    assert second.delete("/api/me/").status_code == 400
    assert (
        second.delete(
            "/api/account/", {"password": "incorrect"}, format="json"
        ).status_code
        == 400
    )
    assert (
        second.delete(
            "/api/account/", {"password": PASSWORD}, format="json"
        ).status_code
        == 200
    )
    assert not LearnerProfile.objects.filter(pk=second_id).exists()
    assert LearnerProfile.objects.filter(pk=profile.pk).exists()
    assert Account.objects.count() == 1
    assert second.get("/api/account/").data == {"authenticated": False}


def test_logout_flushes_session_and_owner_remains_durable(guest):
    result, profile = guest
    register(result, attach=True)
    key = result.session.session_key
    assert logout(result).status_code == 200
    assert result.get("/api/me/").status_code == 401
    assert result.session.session_key != key
    assert LearnerProfile.objects.filter(pk=profile.pk, owner__isnull=False).exists()
    assert login(result).status_code == 200
    assert result.get("/api/me/").data["id"] == profile.pk


def test_progress_writes_restart_and_cascade_deletion_resolve_current_owner(guest):
    from content.models import Item

    first, profile = guest
    register(first, attach=True)
    checkpoint = profile.chosen_pathway.steps.first().checkpoint
    item = Item.objects.filter(skills=checkpoint.pathway_skill.skill).first()
    first_record = CheckpointRecord.objects.create(
        learner=profile, checkpoint=checkpoint, status="done"
    )
    ItemRecord.objects.create(learner=profile, item=item)
    second = client()
    register(second, "two@example.test")
    response = second.post(
        "/api/me/", {"pathway_id": profile.chosen_pathway_id}, format="json"
    )
    second_profile = LearnerProfile.objects.get(pk=response.data["id"])
    assert (
        second.post(
            f"/api/checkpoints/{checkpoint.pk}/skip/",
            {"learner_id": profile.pk},
            format="json",
        ).status_code
        == 200
    )
    assert (
        second.post(
            f"/api/items/{item.pk}/done/", {"learner_id": profile.pk}, format="json"
        ).status_code
        == 200
    )
    assert CheckpointRecord.objects.filter(
        learner=second_profile, status="skipped"
    ).exists()
    assert ItemRecord.objects.filter(learner=second_profile, item=item).exists()
    assert (
        second.post(
            "/api/pathway/restart/", {"learner_id": profile.pk}, format="json"
        ).status_code
        == 200
    )
    first_record.refresh_from_db()
    assert first_record.status == "done"
    assert ItemRecord.objects.filter(learner=profile, item=item).exists()
    assert not CheckpointRecord.objects.filter(learner=second_profile).exists()
    other_session = client()
    login(other_session)
    assert (
        first.delete("/api/account/", {"password": PASSWORD}, format="json").status_code
        == 200
    )
    assert not CheckpointRecord.objects.filter(pk=first_record.pk).exists()
    assert not ItemRecord.objects.filter(learner_id=profile.pk).exists()
    assert LearnerProfile.objects.filter(pk=second_profile.pk).exists()
    assert other_session.get("/api/me/").status_code == 401


@pytest.mark.parametrize("email", [None, [], "invalid", "a" * 255 + "@example.test"])
def test_invalid_email_never_creates_account(email):
    result = client()
    assert register(result, email).status_code == 400
    assert Account.objects.count() == 0


@pytest.mark.parametrize(
    "password", [None, [], "short", "1" * 20, "a" * 129, "password1234"]
)
def test_weak_or_malformed_password_rejected(password):
    result = client()
    response = result.post(
        "/api/account/",
        {"email": "one@example.test", "password": password},
        format="json",
    )
    assert response.status_code == 400
    assert get_user_model().objects.count() == 0


def test_duplicate_email_rejected_atomically_and_database_enforces_case_uniqueness():
    result = client()
    assert register(result).status_code == 201
    assert register(client(), "ONE@EXAMPLE.TEST").status_code == 400
    assert Account.objects.count() == get_user_model().objects.count() == 1
    with pytest.raises(IntegrityError), transaction.atomic():
        user = get_user_model().objects.create(username="other")
        Account.objects.create(user=user, email="ONE@EXAMPLE.TEST")
    assert get_user_model().objects.count() == 1


def test_login_failure_generic_and_inactive_user_rejected():
    result = client()
    register(result)
    logout(result)
    wrong = login(result, password="incorrect")
    missing = login(result, "unknown@example.test")
    assert wrong.status_code == missing.status_code == 400
    assert wrong.data == missing.data
    get_user_model().objects.update(is_active=False)
    assert login(result).status_code == 400


def test_attach_requires_existing_guest_and_boolean():
    result = client()
    assert register(result, attach=True).status_code == 400
    assert register(result, attach="yes").status_code == 400
    assert Account.objects.count() == 0


def test_shared_demo_cannot_attach_or_be_used_by_account():
    call_command("seed_demo", verbosity=0)
    result = client()
    assert result.post("/api/demo/").status_code == 200
    assert register(result, attach=True).status_code == 400
    assert register(result).status_code == 201
    assert result.post("/api/demo/").status_code == 404


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_demo_disabled_outside_local_modes(mode):
    with override_settings(SOMA_ENV=mode):
        assert client().post("/api/demo/").status_code == 404


def test_private_api_never_cacheable_and_identity_excludes_credentials(guest):
    result, _ = guest
    register(result, attach=True)
    for path in [
        "/api/account/",
        "/api/csrf/",
        "/api/me/",
        "/api/dashboard/",
        "/api/items/",
        "/api/next/",
        "/api/opportunities/",
    ]:
        response = result.get(path)
        assert response["Cache-Control"] == "private, no-store"
        assert PASSWORD not in str(response.data)
    assert result.get("/api/account/").data == {
        "authenticated": True,
        "email": "one@example.test",
        "email_verified": False,
    }


def test_authenticated_csrf_required_and_old_token_rejected():
    result = client()
    old = result.cookies["csrftoken"].value
    register(result)
    result.credentials(HTTP_X_CSRFTOKEN=old)
    assert result.post("/api/account/logout/").status_code == 403
    result.credentials()
    assert result.post("/api/account/logout/").status_code == 403


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/account/", "post"),
        ("/api/account/", "delete"),
        ("/api/account/login/", "post"),
    ],
)
def test_account_endpoints_reject_non_object_json(path, method):
    result = client()
    assert getattr(result, method)(path, [], format="json").status_code == 400


def test_login_does_not_authenticate_non_account_user_by_fallback_username():
    get_user_model().objects.create_user(username="missing-account", password=PASSWORD)
    result = client()
    assert login(result, "unknown@example.test").status_code == 400
    assert result.get("/api/account/").data == {"authenticated": False}


@pytest.mark.django_db(transaction=True)
def test_migration_preserves_guest_profile_and_progress(guest):
    # Exercise migration state both before and after the nullable owner addition.
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    _, profile = guest
    profile_id = profile.pk
    checkpoint = profile.chosen_pathway.steps.first().checkpoint
    record = CheckpointRecord.objects.create(
        learner=profile, checkpoint=checkpoint, status="done", quiz_answers=[0, 1, 2]
    )
    record_id = record.pk
    executor = MigrationExecutor(connection)
    executor.migrate([("learners", "0002_initial")])
    try:
        old = executor.loader.project_state([("learners", "0002_initial")]).apps
        assert (
            old.get_model("learners", "LearnerProfile")
            .objects.get(pk=profile_id)
            .display_name
            == "Private guest"
        )
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
    assert LearnerProfile.objects.get(pk=profile_id).owner is None
    assert CheckpointRecord.objects.get(pk=record_id).quiz_answers == [0, 1, 2]
