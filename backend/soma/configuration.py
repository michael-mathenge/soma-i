"""Parse explicit environments without connecting to a database or logging secrets."""

import ipaddress
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

ENVIRONMENTS = {"development", "test", "staging", "production"}
LOCAL_SECRET = "local-only-soma-development-key"


def fail(name, reason):
    raise ImproperlyConfigured(f"{name}: {reason}") from None


def environment(values):
    mode = values.get("SOMA_ENV", "").strip()
    if mode not in ENVIRONMENTS:
        fail("SOMA_ENV", "set development, test, staging or production explicitly")
    return mode


def load_local_environment(values, path):
    # Environment selection must come from the process, never from a .env file.
    mode = environment(values)
    result = dict(values)
    if mode in {"development", "test"} and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() and not key.lstrip().startswith("#"):
                result.setdefault(key.strip(), value.strip().strip("\"'"))
    return result


def boolean(values, name, default):
    raw = values.get(name, str(default)).strip().lower()
    if raw not in {"true", "false"}:
        fail(name, "use true or false")
    return raw == "true"


def host_valid(host, deployed):
    if not host or len(host) > 253 or host != host.lower():
        return False
    if host == "[::1]":
        return not deployed
    try:
        ipaddress.ip_address(host)
        return not deployed
    except ValueError:
        pass
    labels = host.split(".")
    if not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
    ):
        return False
    return not deployed or (
        len(labels) > 1 and labels[-1] not in {"localhost", "local", "internal"}
    )


def hosts(values, deployed):
    raw = values.get(
        "DJANGO_ALLOWED_HOSTS", "" if deployed else "localhost,127.0.0.1,testserver"
    )
    result = [entry.strip() for entry in raw.split(",")]
    if not all(host_valid(entry, deployed) for entry in result):
        fail(
            "DJANGO_ALLOWED_HOSTS",
            "use explicit hostnames without wildcards, schemes or ports",
        )
    return list(dict.fromkeys(result))


def origins(values, allowed, deployed):
    raw = values.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
    if not raw:
        return []
    result = []
    for entry in raw.split(","):
        entry = entry.strip()
        try:
            parsed = urlsplit(entry)
            port = parsed.port
            valid = (
                parsed.scheme in ({"https"} if deployed else {"http", "https"})
                and parsed.hostname in allowed
                and not parsed.username
                and not parsed.password
                and not parsed.path
                and not parsed.query
                and not parsed.fragment
                and (port is None or 1 <= port <= 65535)
                and "*" not in entry
            )
        except ValueError:
            valid = False
        if not valid:
            fail(
                "DJANGO_CSRF_TRUSTED_ORIGINS",
                "use exact allowed-host origins; deployed origins require HTTPS",
            )
        result.append(entry)
    return list(dict.fromkeys(result))


def database(values, deployed, base_dir):
    raw = values.get("DATABASE_URL", "").strip()
    if not raw:
        fail("DATABASE_URL", "an explicit database target is required")
    try:
        parsed = urlsplit(raw)
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        options = dict(pairs)
        config = dj_database_url.parse(raw, conn_max_age=600 if deployed else 0)
    except Exception:
        fail("DATABASE_URL", "invalid target configuration")
    if deployed:
        if parsed.fragment:
            fail("DATABASE_URL", "fragments are not connection configuration")
        if parsed.scheme not in {"postgres", "postgresql"}:
            fail("DATABASE_URL", "staging and production require PostgreSQL")
        if not (
            parsed.hostname
            and host_valid(parsed.hostname, True)
            and parsed.username
            and parsed.password
            and parsed.path not in {"", "/"}
        ):
            fail(
                "DATABASE_URL",
                "specify a PostgreSQL hostname, database and credentials",
            )
        if len(options) != len(pairs) or set(options) - {
            "sslmode",
            "sslrootcert",
            "connect_timeout",
            "application_name",
            "channel_binding",
        }:
            fail("DATABASE_URL", "duplicate or unsupported connection options")
        root = options.get("sslrootcert", "")
        if options.get("sslmode") != "verify-full" or not (
            root == "system" or (root and Path(root).is_absolute())
        ):
            fail(
                "DATABASE_URL",
                "require sslmode=verify-full and system or an absolute sslrootcert",
            )
        try:
            timeout = int(options.get("connect_timeout", "5"))
            if not 1 <= timeout <= 30:
                raise ValueError
        except ValueError:
            fail("DATABASE_URL", "connect_timeout must be between 1 and 30 seconds")
        if options.get("channel_binding", "prefer") not in {"prefer", "require"}:
            fail("DATABASE_URL", "channel_binding cannot be disabled")
        config["OPTIONS"]["connect_timeout"] = timeout
        config["CONN_HEALTH_CHECKS"] = True
    else:
        if parsed.scheme != "sqlite" or parsed.query or parsed.fragment:
            fail(
                "DATABASE_URL", "local commands require an explicit OS-temp SQLite file"
            )
        target = Path(config["NAME"])
        root = Path(tempfile.gettempdir()).resolve()
        if not target.is_absolute() or not target.resolve().is_relative_to(root):
            fail("DATABASE_URL", "local SQLite target must be an absolute OS-temp file")
        if target.resolve() in {
            (base_dir / "db.sqlite3").resolve(),
            (base_dir.parent / "db.sqlite3").resolve(),
        }:
            fail("DATABASE_URL", "repository databases are forbidden")
        config["NAME"] = str(target.resolve())
    return {"default": config}


def load_configuration(values, base_dir):
    mode = environment(values)
    deployed = mode in {"staging", "production"}
    debug = boolean(values, "DJANGO_DEBUG", mode == "development")
    if deployed and debug:
        fail("DJANGO_DEBUG", "must be false in staging and production")
    secret = values.get("DJANGO_SECRET_KEY", "" if deployed else LOCAL_SECRET)
    if deployed and (
        len(secret) < 50
        or len(set(secret)) < 5
        or secret.startswith("django-insecure-")
        or LOCAL_SECRET in secret
    ):
        fail("DJANGO_SECRET_KEY", "provide a separate strong production secret")
    if not secret:
        fail("DJANGO_SECRET_KEY", "cannot be empty")
    allowed = hosts(values, deployed)
    trusted = origins(values, allowed, deployed)
    proxy = boolean(values, "DJANGO_TRUST_PROXY_SSL_HEADER", False)
    if proxy and not deployed:
        fail(
            "DJANGO_TRUST_PROXY_SSL_HEADER",
            "proxy trust is only available in deployed modes",
        )
    try:
        hsts = int(values.get("DJANGO_HSTS_SECONDS", "3600" if deployed else "0"))
        if not 0 <= hsts <= 31536000 or (not deployed and hsts != 0):
            raise ValueError
    except ValueError:
        fail("DJANGO_HSTS_SECONDS", "use 0-31536000 seconds; local modes require 0")
    return {
        "SOMA_ENV": mode,
        "DEBUG": debug,
        "SECRET_KEY": secret,
        "ALLOWED_HOSTS": allowed,
        "CSRF_TRUSTED_ORIGINS": trusted,
        "DATABASES": database(values, deployed, base_dir),
        "SESSION_COOKIE_SECURE": deployed,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "CSRF_COOKIE_SECURE": deployed,
        "CSRF_COOKIE_SAMESITE": "Lax",
        "SECURE_SSL_REDIRECT": deployed,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https")
        if proxy
        else None,
        "USE_X_FORWARDED_HOST": False,
        "SECURE_HSTS_SECONDS": hsts,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
        "SECURE_HSTS_PRELOAD": False,
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        "SECURE_REFERRER_POLICY": "same-origin",
        "X_FRAME_OPTIONS": "DENY",
        "STATIC_ROOT": base_dir.parent / ".local" / "static",
    }
