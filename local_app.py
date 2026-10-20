"""Local sample testing: always use SQLite, regardless of DATABASE_URL."""

from app import create_app as create_base_app


def create_app():
    return create_base_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///samsam-local.db",
        "DATABASE_CONFIGURED": True,
        "GOOGLE_OAUTH_CONFIGURED": False,
        "SESSION_COOKIE_SECURE": False,
        "SESSION_COOKIE_NAME": "samsam_local_session",
    })
