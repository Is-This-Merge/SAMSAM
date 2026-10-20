import os

from dotenv import load_dotenv


# Config can be imported before Flask's CLI gets a chance to load .env
# (for example, when the app is started from an IDE). Load it here so the
# values below are consistent across `flask`, `python`, and IDE launchers.
load_dotenv()

database_url = os.getenv("DATABASE_URL")
secret_key = os.getenv("SECRET_KEY")

# CockroachDB provides a PostgreSQL URL. Use CockroachDB's SQLAlchemy dialect
# so SQLAlchemy can parse CockroachDB versions and database capabilities.
if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "cockroachdb://", 1
    )


class Config:
    SECRET_KEY = secret_key or "local-development-only"
    SECRET_KEY_CONFIGURED = bool(
        secret_key and secret_key != "replace-with-a-long-random-value"
    )
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
    GOOGLE_OAUTH_CONFIGURED = bool(
        GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and SECRET_KEY_CONFIGURED
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("RENDER", "").lower() == "true"
    DATABASE_CONFIGURED = bool(database_url)
    SQLALCHEMY_DATABASE_URI = database_url or "sqlite:///samsam-local.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    # During local development stale CSS/JS makes template and asset versions
    # drift apart. Render can cache fingerprinted static URLs normally.
    SEND_FILE_MAX_AGE_DEFAULT = 3600 if os.getenv("RENDER", "").lower() == "true" else 0
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
