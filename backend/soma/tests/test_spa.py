"""The single page application fallback must never swallow the API."""

import warnings

import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db

# A directory that does not exist, so the shell cannot be served.
MISSING_BUNDLE = "frontend/dist-missing"


def test_api_routes_are_not_handled_by_the_application_shell():
    response = Client().get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_api_path_is_not_the_application_shell():
    response = Client().get("/api/does-not-exist/")

    # The API answers with its own error, not the frontend shell.
    assert response.status_code == 404
    assert "The application bundle is not built." not in response.content.decode()


def test_client_route_returns_a_not_found_when_the_bundle_is_not_built(settings):
    missing = settings.BASE_DIR.parent / MISSING_BUNDLE
    with warnings.catch_warnings():
        # WhiteNoise warns that the overridden directory is absent, which is
        # exactly the condition this case exercises.
        warnings.simplefilter("ignore", UserWarning)
        with override_settings(WHITENOISE_ROOT=missing):
            response = Client().get("/catalogue")

    assert response.status_code == 404
    assert "The application bundle is not built." in response.content.decode()
