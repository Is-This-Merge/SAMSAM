from datetime import datetime, timezone

from ..db import db
from .quiz import new_id


class QuizCollaborator(db.Model):
    __tablename__ = "quiz_collaborators"
    __table_args__ = (
        db.UniqueConstraint("quiz_set_id", "user_id", name="uq_quiz_collaborator"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    quiz_set_id = db.Column(
        db.String(36), db.ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    can_edit = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    quiz_set = db.relationship("QuizSet", back_populates="collaborators")
    user = db.relationship("User", back_populates="collaborations")
