"""Offline configuration probes: synthetic URLs, never a PostgreSQL connection."""

import os
import runpy
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.checks import Tags, run_checks
from django.core.exceptions import DisallowedHost, ImproperlyConfigured
from django.http import HttpResponse
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.middleware.csrf import CsrfViewMiddleware
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory, override_settings

from soma.configuration import LOCAL_SECRET, load_configuration, load_local_environment

BASE = Path(__file__).resolve().parents[2]
SECRET = "synthetic-settings-test-only-ABCDEFGHIJKLMNOPQRSTUVWXYZ-0123456789"
POSTGRES = "postgresql://fixture:synthetic-db-password@db.example.invalid/soma?sslmode=verify-full&sslrootcert=system"


def deployed(**changes):
    values = {
        "SOMA_ENV": "production",
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": SECRET,
        "DJANGO_ALLOWED_HOSTS": "app.example.invalid",
        "DATABASE_URL": POSTGRES,
    }
    values.update(changes)
    return values


def local(tmp_path, **changes):
    values = {
        "SOMA_ENV": "test",
        "DATABASE_URL": "sqlite:///" + (tmp_path / "settings.sqlite3").as_posix(),
    }
    values.update(changes)
    return values


def security(values=None):
    config = load_configuration(values or deployed(), BASE)
    return {
        key: value
        for key, value in config.items()
        if key not in {"DATABASES", "STATIC_ROOT", "SOMA_ENV"}
    }


@pytest.fixture(autouse=True)
def forbid_external_connections(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("configuration test attempted a network/database connection")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(psycopg, "connect", forbidden)


@pytest.mark.parametrize("mode", [None, "", "prod", "testing", "Production", "unknown"])
def test_explicit_recognized_environment_is_required(mode):
    values = deployed()
    if mode is None:
        values.pop("SOMA_ENV")
    else:
        values["SOMA_ENV"] = mode
    with pytest.raises(ImproperlyConfigured, match="SOMA_ENV"):
        load_configuration(values, BASE)


@pytest.mark.parametrize("mode", ["development", "test", "staging", "production"])
def test_missing_database_target_never_falls_back_to_repository(mode):
    values = deployed(SOMA_ENV=mode)
    values.pop("DATABASE_URL")
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        load_configuration(values, BASE)


@pytest.mark.parametrize(
    "secret", ["", LOCAL_SECRET, "short", "a" * 80, "django-insecure-" + "Abc123" * 12]
)
def test_deployed_secret_rejects_missing_weak_and_development_values(secret):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load_configuration(deployed(DJANGO_SECRET_KEY=secret), BASE)


@pytest.mark.parametrize("value", ["true", "TRUE"])
def test_debug_cannot_be_enabled_in_staging_or_production(value):
    for mode in ("staging", "production"):
        with pytest.raises(ImproperlyConfigured, match="DJANGO_DEBUG"):
            load_configuration(deployed(SOMA_ENV=mode, DJANGO_DEBUG=value), BASE)


@pytest.mark.parametrize("name", ["DJANGO_DEBUG", "DJANGO_TRUST_PROXY_SSL_HEADER"])
@pytest.mark.parametrize("value", ["1", "yes", "", "false-ish"])
def test_malformed_booleans_are_errors_not_silent_defaults(name, value):
    with pytest.raises(ImproperlyConfigured, match=name):
        load_configuration(deployed(**{name: value}), BASE)


@pytest.mark.parametrize(
    "host",
    [
        "",
        "*",
        ".example.invalid",
        "app.example.invalid,",
        "https://app.example.invalid",
        "app.example.invalid:443",
        "localhost",
        "127.0.0.1",
        "[::1]",
        "app.local",
        "Bad.EXAMPLE",
        "app..invalid",
        "-app.example.invalid",
    ],
)
def test_unsafe_deployed_host_lists_are_rejected(host):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        load_configuration(deployed(DJANGO_ALLOWED_HOSTS=host), BASE)


@pytest.mark.parametrize(
    "origin",
    [
        "http://app.example.invalid",
        "https://*.example.invalid",
        "https://other.example.invalid",
        "https://app.example.invalid/",
        "https://app.example.invalid/path",
        "https://app.example.invalid?secret=x",
        "https://user:pass@app.example.invalid",
        "https://app.example.invalid:99999",
        "https://app.example.invalid,",
    ],
)
def test_trusted_origins_require_exact_https_allowed_hosts(origin):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_CSRF_TRUSTED_ORIGINS"):
        load_configuration(deployed(DJANGO_CSRF_TRUSTED_ORIGINS=origin), BASE)


def test_valid_origins_and_explicit_proxy_trust_do_not_enable_forwarded_host():
    config = load_configuration(
        deployed(
            DJANGO_CSRF_TRUSTED_ORIGINS="https://app.example.invalid",
            DJANGO_TRUST_PROXY_SSL_HEADER="true",
        ),
        BASE,
    )
    assert config["CSRF_TRUSTED_ORIGINS"] == ["https://app.example.invalid"]
    assert config["SECURE_PROXY_SSL_HEADER"] == ("HTTP_X_FORWARDED_PROTO", "https")
    assert config["USE_X_FORWARDED_HOST"] is False
    assert load_configuration(deployed(), BASE)["SECURE_PROXY_SSL_HEADER"] is None


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///:memory:",
        "sqlite:///db.sqlite3",
        "mysql://fixture:password@db.example.invalid/soma",
        "postgresql://fixture:password@db.example.invalid/soma",
        POSTGRES.replace("verify-full", "require"),
        POSTGRES.replace("verify-full", "disable"),
        POSTGRES.replace("&sslrootcert=system", ""),
        POSTGRES.replace("sslrootcert=system", "sslrootcert=relative.crt"),
        POSTGRES + "&sslmode=verify-full",
        POSTGRES + "&host=another.example.invalid",
        POSTGRES + "&options=ignored",
        POSTGRES + "#fragment",
        POSTGRES.replace("db.example.invalid", "localhost"),
        POSTGRES.replace("fixture:synthetic-db-password@", ""),
        POSTGRES.replace("/soma?", "/?"),
        POSTGRES + "&connect_timeout=0",
        POSTGRES + "&connect_timeout=31",
        POSTGRES + "&channel_binding=disable",
    ],
)
def test_deployed_database_requires_unambiguous_verified_tls(url):
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        load_configuration(deployed(DATABASE_URL=url), BASE)


def test_valid_synthetic_postgresql_configuration_is_parsed_without_connecting():
    config = load_configuration(deployed(), BASE)
    db = config["DATABASES"]["default"]
    assert db["ENGINE"] == "django.db.backends.postgresql"
    assert db["HOST"] == "db.example.invalid"
    assert db["OPTIONS"]["sslmode"] == "verify-full"
    assert db["OPTIONS"]["sslrootcert"] == "system"
    assert db["OPTIONS"]["connect_timeout"] == 5
    assert db["CONN_HEALTH_CHECKS"] is True


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///db.sqlite3",
        "sqlite:///:memory:",
        "sqlite:///backend/db.sqlite3",
        POSTGRES,
    ],
)
def test_local_configuration_refuses_implicit_repository_or_hosted_targets(
    tmp_path, url
):
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        load_configuration(local(tmp_path, DATABASE_URL=url), BASE)


def test_local_configuration_accepts_only_an_absolute_temp_file(tmp_path):
    config = load_configuration(local(tmp_path), BASE)
    assert config["DATABASES"]["default"]["NAME"] == str(
        (tmp_path / "settings.sqlite3").resolve()
    )
    assert not (tmp_path / "settings.sqlite3").exists()
    assert config["DEBUG"] is False and config["SESSION_COOKIE_SECURE"] is False
    assert config["SECURE_HSTS_SECONDS"] == 0
    assert (
        load_configuration(local(tmp_path, SOMA_ENV="development"), BASE)["DEBUG"]
        is True
    )


def test_repository_targets_are_refused_even_if_temp_root_is_misconfigured(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(BASE.parent))
    for path in (BASE / "db.sqlite3", BASE.parent / "db.sqlite3"):
        with pytest.raises(ImproperlyConfigured, match="repository databases"):
            load_configuration(
                local(tmp_path, DATABASE_URL="sqlite:///" + path.as_posix()), BASE
            )


def test_local_env_loading_cannot_select_environment_or_override_process_values(
    tmp_path,
):
    path = tmp_path / "local.env"
    path.write_text(
        "SOMA_ENV=production\nDJANGO_DEBUG=true\nDJANGO_SECRET_KEY=file-key\n",
        encoding="utf-8",
    )
    with pytest.raises(ImproperlyConfigured, match="SOMA_ENV"):
        load_local_environment({}, path)
    values = load_local_environment({"SOMA_ENV": "test", "DJANGO_DEBUG": "false"}, path)
    assert values["SOMA_ENV"] == "test" and values["DJANGO_DEBUG"] == "false"
    assert values["DJANGO_SECRET_KEY"] == "file-key"


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_deployed_environment_never_reads_local_env(tmp_path, monkeypatch, mode):
    path = tmp_path / "local.env"
    path.write_text(
        "DJANGO_DEBUG=true\nDATABASE_URL=sqlite:///db.sqlite3", encoding="utf-8"
    )

    def forbidden(*args, **kwargs):
        pytest.fail("deployed mode read local .env")

    monkeypatch.setattr(Path, "read_text", forbidden)
    assert load_local_environment(deployed(SOMA_ENV=mode), path) == deployed(
        SOMA_ENV=mode
    )


@pytest.mark.parametrize("value", ["-1", "31536001", "not-a-number"])
def test_hsts_rejects_invalid_values_without_preloading_other_subdomains(value):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_HSTS_SECONDS"):
        load_configuration(deployed(DJANGO_HSTS_SECONDS=value), BASE)


def test_https_redirect_proxy_boundary_and_security_headers():
    factory = RequestFactory()
    with override_settings(**security()):
        app = SecurityMiddleware(
            XFrameOptionsMiddleware(lambda request: HttpResponse("fixture"))
        )
        response = app(
            factory.get(
                "/", HTTP_HOST="app.example.invalid", HTTP_X_FORWARDED_PROTO="https"
            )
        )
        assert response.status_code == 301
        response = app(factory.get("/", secure=True, HTTP_HOST="app.example.invalid"))
        assert response["Strict-Transport-Security"] == "max-age=3600"
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["X-Frame-Options"] == "DENY"
        assert response["Referrer-Policy"] == "same-origin"
        with pytest.raises(DisallowedHost):
            factory.get("/", HTTP_HOST="evil.example.invalid").get_host()
    with override_settings(**security(deployed(DJANGO_TRUST_PROXY_SSL_HEADER="true"))):
        assert factory.get("/", HTTP_X_FORWARDED_PROTO="https").is_secure()


def test_secure_session_cookie_and_csrf_origin_rejection_without_database():
    factory = RequestFactory()

    def view(request):
        request.session["fixture"] = "synthetic"
        return HttpResponse("fixture")

    with override_settings(
        **security(), SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies"
    ):
        response = SessionMiddleware(view)(
            factory.get("/", secure=True, HTTP_HOST="app.example.invalid")
        )
        cookie = response.cookies["sessionid"]
        assert cookie["secure"] and cookie["httponly"] and cookie["samesite"] == "Lax"
        request = factory.post(
            "/",
            secure=True,
            HTTP_HOST="app.example.invalid",
            HTTP_ORIGIN="https://evil.example.invalid",
        )
        rejected = CsrfViewMiddleware(lambda request: HttpResponse()).process_view(
            request, lambda request: HttpResponse(), (), {}
        )
        assert rejected.status_code == 403


def test_deployment_security_checks_have_only_deliberately_deferred_hsts_flags():
    with override_settings(**security()):
        messages = run_checks(tags=[Tags.security], include_deployment_checks=True)
    assert {message.id for message in messages} == {"security.W005", "security.W021"}


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://fixture:redaction-sentinel@broken:invalid/soma",
        POSTGRES + "&options=redaction-sentinel",
    ],
)
def test_configuration_errors_never_echo_database_credentials(url):
    with pytest.raises(ImproperlyConfigured) as caught:
        load_configuration(deployed(DATABASE_URL=url), BASE)
    assert "redaction-sentinel" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_real_settings_import_fails_closed_without_environment_and_without_network():
    clean = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DJANGO_") and key not in {"SOMA_ENV", "DATABASE_URL"}
    }
    clean["PYTHONPATH"] = str(BASE)
    code = (
        "import runpy; runpy.run_path(" + repr(str(BASE / "soma" / "settings.py")) + ")"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=clean,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0 and "SOMA_ENV" in result.stderr
    assert "local-only-soma-development-key" not in result.stderr


def test_real_settings_accept_synthetic_production_values_without_opening_database(
    monkeypatch,
):
    for key in list(os.environ):
        if key.startswith("DJANGO_") or key in {"SOMA_ENV", "DATABASE_URL"}:
            monkeypatch.delenv(key)
    for key, value in deployed().items():
        monkeypatch.setenv(key, value)
    result = runpy.run_path(str(BASE / "soma" / "settings.py"))
    assert (
        result["DEBUG"] is False
        and result["DATABASES"]["default"]["HOST"] == "db.example.invalid"
    )
    assert (
        "django.middleware.clickjacking.XFrameOptionsMiddleware" in result["MIDDLEWARE"]
    )
    # The built bundle is the static root and is served at the site root,
    # which is where the built index document references its assets from.
    assert result["STATIC_ROOT"] == BASE.parent / "frontend" / "dist"
    assert result["WHITENOISE_ROOT"] == BASE.parent / "frontend" / "dist"
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in result["MIDDLEWARE"]


def test_real_local_settings_preserve_non_django_env_consumers_after_validation(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(os, "environ", local(tmp_path))
    env_path = BASE.parent / ".env"
    original_read = Path.read_text
    original_exists = Path.exists

    def local_env(path, *args, **kwargs):
        if path == env_path:
            return "SOMA_SENDER=console\nDJANGO_DEBUG=false\n"
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", local_env)
    monkeypatch.setattr(
        Path, "exists", lambda path: path == env_path or original_exists(path)
    )
    runpy.run_path(str(BASE / "soma" / "settings.py"))
    assert os.environ["SOMA_SENDER"] == "console"
    assert os.environ["SOMA_ENV"] == "test"
