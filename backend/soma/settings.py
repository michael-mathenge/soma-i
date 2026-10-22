import os
from pathlib import Path

from soma.configuration import load_configuration, load_local_environment

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / ".env"
_environment_values = load_local_environment(os.environ, ENV_FILE)
_configuration = load_configuration(_environment_values, BASE_DIR)
# Preserve local .env consumers outside Django settings after target validation.
for _name, _value in _environment_values.items():
    os.environ.setdefault(_name, _value)
globals().update(_configuration)
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
    "learners.authentication.PrivateAPIHeaders",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "soma.urls"
TEMPLATES = []
WSGI_APPLICATION = "soma.wsgi.application"
LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "learners.authentication.GuestSessionAuthentication"
    ],
}
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SOMA_ACCOUNT_EMAIL_MODE = _environment_values.get("SOMA_ACCOUNT_EMAIL_MODE", "disabled")
if SOMA_ACCOUNT_EMAIL_MODE not in {"disabled", "memory"} or (
    _configuration["SOMA_ENV"] not in {"development", "test"}
    and SOMA_ACCOUNT_EMAIL_MODE != "disabled"
):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "SOMA_ACCOUNT_EMAIL_MODE: only disabled or local memory preview is supported"
    )
