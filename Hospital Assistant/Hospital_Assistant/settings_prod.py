"""Production settings."""

from .settings_base import *  # noqa: F403
from .settings_base import _env_bool

DEBUG = _env_bool("DJANGO_DEBUG", False)  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django.db.backends.postgresql"),  # noqa: F405
        "NAME": os.getenv("DJANGO_DB_NAME", "Hospital Data"),  # noqa: F405
        "USER": os.getenv("DJANGO_DB_USER", "postgres"),  # noqa: F405
        "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", ""),  # noqa: F405
        "HOST": os.getenv("DJANGO_DB_HOST", "localhost"),  # noqa: F405
        "PORT": os.getenv("DJANGO_DB_PORT", "5432"),  # noqa: F405
    }
}

SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = _env_bool("DJANGO_SESSION_COOKIE_SECURE", True)  # noqa: F405
CSRF_COOKIE_SECURE = _env_bool("DJANGO_CSRF_COOKIE_SECURE", True)  # noqa: F405
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = _env_bool("DJANGO_SECURE_HSTS_PRELOAD", True)  # noqa: F405
