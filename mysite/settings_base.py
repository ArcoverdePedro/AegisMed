import base64
import binascii
import os
from pathlib import Path

import environ
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECURE_SSL_REDIRECT=(bool, True),
    SESSION_COOKIE_SECURE=(bool, True),
    CSRF_COOKIE_SECURE=(bool, True),
    FILE_MAX_UPLOAD_MB=(int, 50),
    SENTRY_TRACES_SAMPLE_RATE=(float, 0.05),
)

ENV_FILE = env.str("ENV_FILE", default=str(BASE_DIR / ".env"))
if os.path.exists(ENV_FILE):
    environ.Env.read_env(ENV_FILE)

SECRET_KEY = env.str("SECRET_KEY", default="")
DEBUG = env.bool("DEBUG")
ENVIRONMENT = env.str("ENVIRONMENT", default="development" if DEBUG else "production")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "development-only-insecure-key"
    else:
        raise ImproperlyConfigured("SECRET_KEY e obrigatoria quando DEBUG=False.")

if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("CHANGE_ME")):
    raise ImproperlyConfigured(
        "SECRET_KEY de producao deve possuir pelo menos 50 caracteres e nao pode ser placeholder."
    )

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT") if not DEBUG else False
# Healthcheck do container fala HTTP direto com o app; sem isso ele recebe 301 e falha.
SECURE_REDIRECT_EXEMPT = [r"^health/"]
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE") if not DEBUG else False
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE") if not DEBUG else False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# IPs/redes do proxy reverso; so eles podem informar o IP real do cliente.
TRUSTED_PROXY_IPS = env.list("TRUSTED_PROXY_IPS", default=["127.0.0.1"])
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# Scripts so do proprio servidor ou inline com nonce; estilos inline ainda sao usados nos templates.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF, "data:"],
    "connect-src": [CSP.SELF],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Estacao de trabalho compartilhada: a sessao expira por inatividade e ao fechar o navegador.
SESSION_COOKIE_AGE = env.int("SESSION_IDLE_TIMEOUT_SECONDS", default=30 * 60)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

if not DEBUG:
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

INSTALLED_APPS = [
    "channels",
    "django_htmx",
    "auditlog",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "django_simple_bulma",
    "crispy_bulma",
    "django_feather",
    "aegis_med",
    "apps.pwa.apps.PwaConfig",
    "apps.clinical.pep.apps.PepConfig",
    "apps.clinical.adt.apps.AdtConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "aegis_med.middleware.TrackedSessionMiddleware",
    "aegis_med.middleware.FirstAccessRedirectMiddleware",
    "aegis_med.middleware.CallPanelKioskMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csp",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mysite.wsgi.application"
ASGI_APPLICATION = "mysite.asgi.application"

DATABASE_URL = env.str("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db_url_config(DATABASE_URL)}
elif not DEBUG:
    raise ImproperlyConfigured(
        "DATABASE_URL e obrigatoria em producao. Use PostgreSQL interno ou um host externo."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# A aplicacao e ASGI; conexoes persistentes devem permanecer desativadas.
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

REDIS_URL = env.str("REDIS_URL", default="")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            # redis-py 8 lê com timeout padrão de 5 s, o mesmo do BZPOPMIN (brpop_timeout)
            # do channels_redis; sem folga, sockets ociosos caem com TimeoutError.
            "CONFIG": {"hosts": [{"address": REDIS_URL, "socket_timeout": 10}]},
        }
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "aegismed-local",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]

AUTH_USER_MODEL = "aegis_med.CustomUser"
LOGIN_URL = "login"
LOGOUT_REDIRECT_URL = "home"

MESSAGE_TAGS = {
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bulma"
CRISPY_TEMPLATE_PACK = "bulma"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = env.str("TIME_ZONE", default="America/Fortaleza")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_simple_bulma.finders.SimpleBulmaFinder",
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FILE_MAX_UPLOAD_MB = env.int("FILE_MAX_UPLOAD_MB")
FILE_UPLOAD_MAX_MEMORY_SIZE = min(FILE_MAX_UPLOAD_MB * 1024 * 1024, 5 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_MAX_UPLOAD_MB * 1024 * 1024 + 1024 * 1024

FILE_ENCRYPTION_KEY = env.str("FILE_ENCRYPTION_KEY", default="")
if not FILE_ENCRYPTION_KEY and DEBUG:
    FILE_ENCRYPTION_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

if not FILE_ENCRYPTION_KEY:
    raise ImproperlyConfigured("FILE_ENCRYPTION_KEY e obrigatoria em producao.")

try:
    _decoded_file_key = base64.urlsafe_b64decode(FILE_ENCRYPTION_KEY.encode("ascii"))
except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
    raise ImproperlyConfigured(
        "FILE_ENCRYPTION_KEY deve ser base64 URL-safe representando exatamente 32 bytes."
    ) from exc
if len(_decoded_file_key) != 32:
    raise ImproperlyConfigured(
        "FILE_ENCRYPTION_KEY deve representar exatamente 32 bytes."
    )
del _decoded_file_key

# Chave propria dos backups; guardar separada da FILE_ENCRYPTION_KEY e do proprio backup.
BACKUP_ENCRYPTION_KEY = env.str("BACKUP_ENCRYPTION_KEY", default="")


AUDITLOG_STORE_JSON_CHANGES = True
AUDITLOG_DISABLE_ON_RAW_SAVE = True
AUDITLOG_CHANGE_DISPLAY_TRUNCATE_LENGTH = 140

# Equivalente ao antigo send_default_pii=False (guia de migracao do SDK 3): os padroes
# do 3.x enviam usuario, corpos HTTP e mais headers, o que nao cabe em dado de saude.
# Cookies ficam no padrao do SDK, que ja mascara sessao e CSRF.
SENTRY_DATA_COLLECTION = {
    "user_info": False,
    "http_bodies": [],
    "graphql": {"document": False, "variables": False},
    "gen_ai": {"inputs": False, "outputs": False},
    "mcp": {"inputs": False, "outputs": False},
    "database_query_data": False,
    "queues": False,
    "http_headers": {
        "request": {
            "mode": "denylist",
            # referer e hx-current-url trazem a URL inteira, com a busca por nome/CPF.
            "terms": ["forwarded", "-ip", "remote-", "via", "-user", "referer", "hx-current-url"],
        },
    },
    # Buscas por nome/CPF passam na URL: nenhum parametro vai para o Sentry.
    "url_query_params": {"mode": "off"},
    # Variaveis locais dos frames carregam pacientes, prescricoes e a propria URL.
    "stack_frame_variables": False,
}

SENTRY_DSN = env.str("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE"),
        data_collection=SENTRY_DATA_COLLECTION,
    )

LOG_LEVEL = env.str("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "mysite.logging.JsonFormatter"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"}
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "aegis_med": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "apps.pwa": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
