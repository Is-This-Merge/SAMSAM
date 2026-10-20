from datetime import datetime, timezone

from ..db import db
from .quiz import new_id


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    google_sub = db.Column(db.String(255), nullable=False, unique=True, index=True)
    email = db.Column(db.String(320), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    picture_url = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    quizzes = db.relationship("QuizSet", back_populates="owner", lazy="raise")
    attempts = db.relationship("QuizAttempt", back_populates="user", lazy="raise")
    collaborations = db.relationship(
        "QuizCollaborator",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )
