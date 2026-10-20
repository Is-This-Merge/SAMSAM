import secrets

from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy.exc import SQLAlchemyError

from ..db import db
from ..models import QuizAttempt, QuizSet
from ..services.quiz_access import can_view_quiz
from ..services.article_repository import article_passages
from ..services.grading import check_answer
from ..services.study_modes import build_round, public_questions, round_digest
from ..services.cloze import validate_options

bp = Blueprint("study_modes", __name__, url_prefix="/api/quizzes")


def serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="study-round-v1")


@bp.get("/<quiz_id>/article-source")
def article_source(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None or not can_view_quiz(quiz, g.user):
        return jsonify(error="quiz_not_found"), 404
    passages = article_passages(quiz_id)
    return jsonify(title=quiz.title, passages=passages, text="\n\n".join(p["text"] for p in passages),
                   source=" / ".join(dict.fromkeys(p["source"] for p in passages)))


@bp.route("/<quiz_id>/study", methods=["GET", "POST"])
def start_round(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None or not can_view_quiz(quiz, g.user):
        return jsonify(error="quiz_not_found"), 404
    mode = request.args.get("mode")
    options = None
    if request.method == "POST":
        if mode != "article":
            return jsonify(error="unsupported_mode"), 400
        try:
            options = validate_options(request.get_json(silent=True))
        except ValueError as exc:
            return jsonify(error="invalid_options", message=str(exc)), 400
    seed = secrets.token_hex(16)
    questions = build_round(quiz, mode, seed, options)
    if not questions:
        return jsonify(error="unsupported_mode", message="이 세트에서 사용할 수 없는 학습 방식입니다."), 400
    token = serializer().dumps(dict(quiz_id=quiz.id, mode=mode, seed=seed, options=options, digest=round_digest(questions)))
    return jsonify(token=token, quiz=dict(id=quiz.id, title=quiz.title, subject=quiz.subject,
                                        description=quiz.description, questions=public_questions(questions)))


def submitted_round(quiz_id, payload):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None or not can_view_quiz(quiz, g.user):
        return None, None, (jsonify(error="quiz_not_found"), 404)
    try:
        if not isinstance(payload, dict) or not isinstance(payload.get("token"), str):
            raise ValueError()
        data = serializer().loads(payload["token"], max_age=86400)
        if data["quiz_id"] != quiz_id:
            raise ValueError()
        questions = build_round(quiz, data["mode"], data["seed"], data.get("options"))
        if not questions or round_digest(questions) != data["digest"]:
            raise ValueError()
    except (BadData, ValueError, KeyError, TypeError):
        return None, None, (jsonify(error="invalid_round", message="학습이 만료되었거나 내용이 변경되었습니다. 다시 시작해 주세요."), 400)
    return quiz, questions, None


@bp.post("/<quiz_id>/study/check")
def check_round_answer(quiz_id):
    payload = request.get_json(silent=True)
    _, questions, error = submitted_round(quiz_id, payload)
    if error:
        return error
    position = payload.get("position")
    if type(position) is not int or not 0 <= position < len(questions):
        return jsonify(error="invalid_position"), 400
    try:
        return jsonify(check_answer(questions[position], payload.get("answer")))
    except ValueError as exc:
        return jsonify(error="invalid_answer", message=str(exc)), 400


@bp.post("/<quiz_id>/study/grade")
def grade_round(quiz_id):
    payload = request.get_json(silent=True)
    quiz, questions, error = submitted_round(quiz_id, payload)
    if error:
        return error
    answers = payload.get("answers")
    if not isinstance(answers, list) or len(answers) != len(questions):
        return jsonify(error="invalid_answers", message="모든 문항에 답해 주세요."), 400
    try:
        results = [dict(position=i, **check_answer(q, a)) for i, (q, a) in enumerate(zip(questions, answers))]
    except ValueError as exc:
        return jsonify(error="invalid_answers", message=str(exc)), 400
    correct_count = sum(r["correct"] for r in results)
    score = round(correct_count / len(results) * 100)
    attempt = QuizAttempt(quiz_set_id=quiz.id, user_id=g.user.id if g.user else None,
                          answers=answers, score=score, correct_count=correct_count, total_count=len(results))
    try:
        db.session.add(attempt)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to save study round")
        return jsonify(error="database_error"), 500
    return jsonify(attempt_id=attempt.id, score=score, correct_count=correct_count,
                   total_count=len(results), results=results)
