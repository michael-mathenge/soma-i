import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() and not key.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-only-soma-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
).split(",")
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "content",
    "pathways",
    "learners",
    "opportunities",
    "engagement",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "soma.urls"
TEMPLATES = []
WSGI_APPLICATION = "soma.wsgi.application"
database_url = os.getenv("DATABASE_URL")
if database_url:
    database_config = dj_database_url.parse(database_url, conn_max_age=600)
    if (
        database_config["ENGINE"].endswith("sqlite3")
        and database_config["NAME"] != ":memory:"
        and not Path(database_config["NAME"]).is_absolute()
    ):
        database_config["NAME"] = str(
            (BASE_DIR.parent / database_config["NAME"]).resolve()
        )
    DATABASES = {"default": database_config}
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600
        )
    }
LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
REST_FRAMEWORK = {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]}
