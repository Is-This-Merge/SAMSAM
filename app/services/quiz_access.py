from sqlalchemy import select

from ..db import db
from ..models import QuizCollaborator


def get_collaboration(quiz, user):
    if user is None:
        return None
    return db.session.scalar(
        select(QuizCollaborator).where(
            QuizCollaborator.quiz_set_id == quiz.id,
            QuizCollaborator.user_id == user.id,
        )
    )


def can_view_quiz(quiz, user):
    return (
        quiz.visibility == "public"
        or (user is not None and quiz.owner_id == user.id)
        or get_collaboration(quiz, user) is not None
    )


def can_edit_quiz(quiz, user):
    if user is None:
        return False
    if quiz.owner_id == user.id:
        return True
    collaboration = get_collaboration(quiz, user)
    return collaboration is not None and collaboration.can_edit
