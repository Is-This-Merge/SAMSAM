from flask import Blueprint, g, jsonify
from sqlalchemy import distinct, func, select

from ..auth import login_required
from ..db import db
from ..models import QuizAttempt

bp = Blueprint("profile", __name__, url_prefix="/api/me")


@bp.get("/stats")
@login_required
def stats():
    result = db.session.execute(
        select(
            func.count(QuizAttempt.id),
            func.avg(QuizAttempt.score),
            func.max(QuizAttempt.score),
            func.count(distinct(QuizAttempt.quiz_set_id)),
        ).where(QuizAttempt.user_id == g.user.id)
    ).one()
    return jsonify(
        attempt_count=result[0] or 0,
        average_score=round(float(result[1])) if result[1] is not None else 0,
        best_score=result[2] or 0,
        studied_quiz_count=result[3] or 0,
    )
