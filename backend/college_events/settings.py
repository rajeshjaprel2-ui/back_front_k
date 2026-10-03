"""
Django settings for College Events Management System.
"""

import os
from pathlib import Path

import django_mongodb_backend
from django.contrib.messages import constants as message_constants
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

load_dotenv(PROJECT_ROOT / ".env")

SECRET_KEY = "django-insecure-college-events-bca-minor-project-key"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "college_events.apps.MongoAdminConfig",
    "college_events.apps.MongoAuthConfig",
    "college_events.apps.MongoContentTypesConfig",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_mongodb_backend",
    "events",
]

MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "events.middleware.EventStatusMiddleware",
]

ROOT_URLCONF = "college_events.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "college_events.wsgi.application"

MONGODB_URI = os.environ.get("MONGODB_URI") or "mongodb://MONGODB_URI-is-not-set:27017"

DATABASES = {
    "default": django_mongodb_backend.parse_uri(
        MONGODB_URI,
        db_name="college_events",
        options={"serverSelectionTimeoutMS": 5000},
    ),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [FRONTEND_DIR / "static"]
STATIC_ROOT = PROJECT_ROOT / "staticfiles"

MEDIA_URL = "media/"

STORAGES = {
    "default": {"BACKEND": "events.storage.GridFSStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = 10
# Without SMTP credentials, emails are printed to the terminal instead of being sent.
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else "django.core.mail.backends.console.EmailBackend"
)
SITE_URL = os.environ.get("SITE_URL", "https://back-front-k.vercel.app").rstrip("/")

EMAIL_BRAND = {
    "university": os.environ.get("BRAND_UNIVERSITY", "Srinivas University"),
    "portal": os.environ.get("BRAND_PORTAL", "Srinivas University Events"),
    "team": os.environ.get("BRAND_TEAM", "Srinivas University Events Team"),
    "logo": FRONTEND_DIR / "static" / os.environ.get("BRAND_LOGO", "events/img/srinivas-logo.jpeg"),
}
# Who receives an email on every sign-in: any of "student", "admin" (comma-separated). Empty disables it.
LOGIN_ALERT_ROLES = {
    role.strip().lower() for role in os.environ.get("LOGIN_ALERT_ROLES", "student,admin").split(",") if role.strip()
}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL") or EMAIL_HOST_USER or "noreply@college.edu"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}
