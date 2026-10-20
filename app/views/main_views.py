from flask import Blueprint, current_app, g, jsonify, redirect, render_template, url_for
from sqlalchemy import distinct, func, select, text
from sqlalchemy.orm import selectinload

from ..auth import login_required
from ..db import db
from ..models import QuizAttempt, QuizCollaborator, QuizSet

bp = Blueprint('main', __name__, url_prefix='/')


def _learning_stats(user_id):
    aggregate = db.session.execute(
        select(
            func.count(QuizAttempt.id),
            func.avg(QuizAttempt.score),
            func.max(QuizAttempt.score),
            func.count(distinct(QuizAttempt.quiz_set_id)),
        ).where(QuizAttempt.user_id == user_id)
    ).one()
    return {
        "attempt_count": aggregate[0] or 0,
        "average_score": round(float(aggregate[1])) if aggregate[1] is not None else 0,
        "best_score": aggregate[2] or 0,
        "studied_quiz_count": aggregate[3] or 0,
    }

@bp.get('/')
@bp.get('/index.html')
def index():
    return render_template('home.html')


@bp.get('/login.html')
def legacy_login():
    return redirect(url_for('auth.login_page'))


@bp.get('/categorysearch.html')
def legacy_search():
    return redirect(url_for('main.index') + '#discover')


@bp.get('/answer.html')
@bp.get('/false.html')
@bp.get('/next_quiz.html')
def legacy_quiz_pages():
    return redirect(url_for('main.index') + '#discover')


@bp.get('/info.html')
def info():
    return render_template('info.html')


@bp.get('/create.html')
@login_required
def create_page():
    return render_template('create.html')


@bp.get('/inventory.html')
@login_required
def inventory():
    quizzes = db.session.scalars(
        select(QuizSet)
        .where(QuizSet.owner_id == g.user.id)
        .order_by(QuizSet.updated_at.desc())
    ).all()
    attempts = db.session.scalars(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.quiz_set))
        .where(QuizAttempt.user_id == g.user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(20)
    ).all()
    shared_quizzes = db.session.scalars(
        select(QuizSet)
        .join(QuizCollaborator)
        .where(QuizCollaborator.user_id == g.user.id)
        .order_by(QuizSet.updated_at.desc())
    ).all()
    return render_template(
        'inventory.html',
        quizzes=quizzes,
        shared_quizzes=shared_quizzes,
        attempts=attempts,
    )


@bp.get('/mypage.html')
@login_required
def mypage():
    return render_template('mypage.html', stats=_learning_stats(g.user.id))


@bp.get('/quiz.html')
def quiz_page():
    return render_template('quiz_detail.html')


@bp.get('/study.html')
def study_page():
    return render_template('quiz.html')


@bp.get('/match.html')
def match_page():
    return render_template('match.html')


@bp.get('/mistakes.html')
def mistakes_page():
    return render_template('mistakes.html')


@bp.get('/article.html')
def article_page():
    return render_template('article.html')


@bp.get('/health')
def health():
    if not current_app.config['DATABASE_CONFIGURED']:
        return jsonify(status='degraded', database='not_configured'), 503

    try:
        db.session.execute(text('SELECT 1'))
    except Exception:
        current_app.logger.exception('CockroachDB health check failed')
        return jsonify(status='degraded', database='unavailable'), 503

    return jsonify(status='ok', database='ok')
