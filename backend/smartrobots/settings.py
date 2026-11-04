"""
Django settings for SmartRobots BB IA backend.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

import os
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-bb-ia-development-only")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
WATSONX_API_KEY = os.environ.get("WATSONX_API_KEY", "")
WATSONX_URL = os.environ.get("WATSONX_URL", "")
WATSONX_PROJECT_ID = os.environ.get("WATSONX_PROJECT_ID", "")
WATSONX_MODEL_ID = os.environ.get("WATSONX_MODEL_ID", "")

# ─── Apps ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "agent",
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# ─── CORS (aceita o front-end em qualquer origem durante o desenvolvimento) ───
_cors_origins_env = os.environ.get("DJANGO_CORS_ORIGINS", "")
if _cors_origins_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
else:
    # Em desenvolvimento sem variável definida, permite qualquer origem.
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
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

# ─── URLs ─────────────────────────────────────────────────────────────────────
ROOT_URLCONF = "smartrobots.urls"

# ─── Database (SQLite por padrão) ─────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ─── Internacionalização ──────────────────────────────────────────────────────
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ─── Static files ─────────────────────────────────────────────────────────────
STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

WSGI_APPLICATION = "smartrobots.wsgi.application"
