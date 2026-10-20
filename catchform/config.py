import os
from datetime import timedelta


def _env_flag(name, default="0"):
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _database_url():
    """SQLite en local, Postgres (driver psycopg 3) en production."""
    url = os.environ.get("DATABASE_URL", "sqlite:///catchform.db")
    # Les hébergeurs fournissent "postgres://..." ou "postgresql://..." :
    # on force le driver psycopg 3 installé via requirements.txt.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Config:
    """Configuration de l'application, pilotée par variables d'environnement."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-prod")

    SQLALCHEMY_DATABASE_URI = _database_url()
    # Postgres hébergé : on vérifie les connexions avant usage (coupures réseau).
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True, "pool_recycle": 300}
        if SQLALCHEMY_DATABASE_URI.startswith("postgresql")
        else {}
    )

    # Plan gratuit : soumissions acceptées par mois, tous formulaires confondus.
    FREE_PLAN_MONTHLY_LIMIT = int(os.environ.get("FREE_PLAN_MONTHLY_LIMIT", "100"))
    SUBMISSIONS_PER_PAGE = 50

    # Taille max d'une requête : protège l'endpoint public des gros envois.
    MAX_CONTENT_LENGTH = 100 * 1024

    # Cookies : SameSite=Lax partout, Secure en production (HTTPS).
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE")
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

    # CSRF (Flask-WTF) : jeton valable toute la durée de la session.
    WTF_CSRF_TIME_LIMIT = None

    # Notifications e-mail via l'API Resend (désactivées sans clé).
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "CatchForm <onboarding@resend.dev>")

    # Adresse de contact pour passer au plan Pro (en attendant Stripe).
    CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "contact@example.com")
