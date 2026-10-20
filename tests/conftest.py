import pytest

from app import create_app
from app.db import db
from app.models import User


@pytest.fixture()
def client():
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_CONFIGURED": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "GOOGLE_OAUTH_CONFIGURED": False,
        }
    )
    with app.app_context():
        db.create_all()
        user = User(
            google_sub="test-google-user",
            email="student@example.com",
            display_name="테스트 학생",
        )
        db.session.add(user)
        db.session.commit()
        client = app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = user.id
            session["csrf_token"] = "test-csrf-token"
        client.environ_base["HTTP_X_CSRF_TOKEN"] = "test-csrf-token"
        yield client
        db.session.remove()
        db.drop_all()
