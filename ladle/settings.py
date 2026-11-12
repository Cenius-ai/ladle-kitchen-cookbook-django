"""Django settings for Ladle Kitchen Cookbook.

The project is built to boot on a fresh clone with no environment set: every
secret has an in-code development default, the database is a SQLite file next
to manage.py, and static assets are served by Django while DEBUG is on.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Populate os.environ from a plain KEY=VALUE file, without extra packages."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(BASE_DIR / ".env")

# A generated value lands in .env at install time; the fallback keeps a bare
# checkout bootable without any environment at all.
SECRET_KEY = os.environ.get("SECRET_KEY") or "cenius-dev-4f1c9a7b2e6d8350"

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() not in {"0", "false", "no"}

# The preview and local development both arrive through proxies with varied
# Host headers, so the list stays open here. Tighten it in production.
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "cookbook",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "ladle.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ladle.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cookbook.context_processors.palette",
            ],
        },
    },
]

WSGI_APPLICATION = "ladle.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "ladle.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/recipes/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sessions last two weeks and ride plain HTTP in the preview, so the secure
# cookie flags stay off deliberately: a Secure cookie is dropped over http://
# and every post-login page would bounce back to the sign-in card.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# The suite creates many users; iterate the hash cheaply there only.
RUNNING_TESTS = bool(
    "test" in sys.argv
    or "pytest" in sys.modules
    or "pytest" in os.path.basename(sys.argv[0] if sys.argv else "")
)
if RUNNING_TESTS:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
