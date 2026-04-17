from __future__ import annotations

from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    HISTORY_SYNC_ENABLED=(bool, True),
    TIME_SYNC_ENABLED=(bool, True),
    FAST_POLL_MS=(int, 500),
    MAX_HISTORY_RECORDS_PER_CYCLE=(int, 50),
    HISTORY_SYNC_BATCH_SIZE=(int, 20),
    TIME_SYNC_INTERVAL_SEC=(int, 300),
    TIME_SYNC_DRIFT_THRESHOLD_SEC=(int, 2),
    MODBUS_UNIT_ID=(int, 1),
    MODBUS_TIMEOUT_SEC=(float, 1.0),
    PLC_SIMULATION_ENABLED=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-key")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=["http://*", "https://*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "channels",
    "apps.core",
    "apps.companies",
    "apps.products",
    "apps.recipes",
    "apps.plc",
    "apps.tests",
    "apps.reports",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.app_context",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="hvac"),
        "USER": env("POSTGRES_USER", default="hvac"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="hvac"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://redis:6379/0")]},
    }
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr-tr"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Europe/Istanbul")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 480
CELERY_BEAT_SCHEDULE = {
    "plc-fast-poll": {
        "task": "apps.plc.tasks.fast_poll_task",
        "schedule": max(env("FAST_POLL_MS") / 1000, 0.5),
    },
    "plc-history-sync": {
        "task": "apps.plc.tasks.history_sync_task",
        "schedule": 2.0,
    },
    "active-test-supervision": {
        "task": "apps.tests.tasks.supervise_active_test_task",
        "schedule": 1.0,
    },
    "periodic-time-sync": {
        "task": "apps.plc.tasks.periodic_time_sync_task",
        "schedule": crontab(minute="*/5"),
    },
    "cleanup-old-events": {
        "task": "apps.core.tasks.cleanup_old_events_task",
        "schedule": crontab(hour=3, minute=0),
    },
}

PLC_CONFIG = {
    "host": env("PLC_HOST", default="127.0.0.1"),
    "port": env("PLC_PORT", default=502),
    "unit_id": env("MODBUS_UNIT_ID"),
    "timeout_sec": env("MODBUS_TIMEOUT_SEC"),
    "fast_poll_ms": env("FAST_POLL_MS"),
    "history_sync_enabled": env("HISTORY_SYNC_ENABLED"),
    "max_history_records_per_cycle": env("MAX_HISTORY_RECORDS_PER_CYCLE"),
    "history_sync_batch_size": env("HISTORY_SYNC_BATCH_SIZE"),
    "time_sync_enabled": env("TIME_SYNC_ENABLED"),
    "time_sync_interval_sec": env("TIME_SYNC_INTERVAL_SEC"),
    "time_sync_drift_threshold_sec": env("TIME_SYNC_DRIFT_THRESHOLD_SEC"),
    "simulation_enabled": env("PLC_SIMULATION_ENABLED"),
    "report_root_path": env("REPORT_ROOT_PATH", default=str(BASE_DIR / "media" / "reports")),
}

LOGIN_URL = "/admin/login/"

LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
