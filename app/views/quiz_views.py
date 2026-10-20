from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from ..db import db
from ..auth import login_required
from ..models import Question, QuizAttempt, QuizCollaborator, QuizSet, User
from ..services.quiz_access import can_edit_quiz, can_view_quiz, get_collaboration
from ..services.quiz_content import replace_questions
from ..services.quiz_validation import clean_text, validate_quiz
from ..services.study_modes import available_modes
from ..services.article_repository import TOPICS, vocabulary_key
from uuid import NAMESPACE_URL, uuid5

bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")


@bp.get("/preview")
def preview_quiz():
    question_count = (
        select(func.count(Question.id))
        .where(Question.quiz_set_id == QuizSet.id)
        .correlate(QuizSet)
        .scalar_subquery()
    )
    quiz = db.session.scalar(
        select(QuizSet)
        .where(QuizSet.visibility == "public")
        .where(question_count > 1)
        .order_by(func.random())
        .limit(1)
    )
    if quiz is None:
        quiz = db.session.scalar(
            select(QuizSet)
            .where(QuizSet.visibility == "public")
            .where(QuizSet.questions.any())
            .order_by(func.random())
            .limit(1)
        )
    if quiz is None:
        return jsonify(quiz=None)

    return jsonify(quiz={
        "id": quiz.id,
        "title": quiz.title,
        "subject": quiz.subject,
        "question_count": len(quiz.questions),
        "questions": [
            {
                "prompt": question.prompt,
                "answer": next(
                    choice.text for choice in question.choices if choice.is_correct
                ),
                "image_data": question.image_data,
            }
            for question in quiz.questions
        ],
    })


@bp.get("")
def list_quizzes():
    keyword = clean_text(request.args.get("q"))[:100]
    subject = clean_text(request.args.get("subject"))[:50]
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    statement = select(QuizSet).where(QuizSet.visibility == "public")
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                QuizSet.title.ilike(pattern),
                QuizSet.subject.ilike(pattern),
                QuizSet.description.ilike(pattern),
            )
        )
    if subject:
        statement = statement.where(QuizSet.subject == subject)

    numbered_ids = {str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{vocabulary_key(topic)}")): i for i, topic in enumerate(TOPICS, 1)}
    quizzes = db.session.scalars(
        statement.order_by(case(numbered_ids, value=QuizSet.id, else_=6), QuizSet.created_at.desc()).offset((page - 1) * 30).limit(30)
    ).all()
    subject_rows = db.session.execute(
        select(QuizSet.subject, func.count(QuizSet.id))
        .where(QuizSet.visibility == "public")
        .group_by(QuizSet.subject)
        .order_by(QuizSet.subject)
    ).all()
    return jsonify(
        page=page,
        subjects=[{"name": name, "count": count} for name, count in subject_rows],
        quizzes=[
            {
                "id": quiz.id,
                "title": quiz.title,
                "subject": quiz.subject,
                "description": quiz.description,
                "question_count": len(quiz.questions),
                "question_types": sorted({question.question_type for question in quiz.questions}),
                "created_at": quiz.created_at.isoformat(),
            }
            for quiz in quizzes
        ]
    )


@bp.post("")
@login_required
def create_quiz():
    payload = request.get_json(silent=True)
    errors = validate_quiz(payload)
    if errors:
        return jsonify(error="validation_error", fields=errors), 400

    quiz = QuizSet(
        title=clean_text(payload["title"]),
        subject=clean_text(payload["subject"]),
        description=clean_text(payload.get("description")),
        visibility=clean_text(payload.get("visibility") or "public"),
        owner_id=g.user.id,
    )

    replace_questions(quiz, payload["questions"])

    try:
        db.session.add(quiz)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to create quiz")
        return jsonify(error="database_error"), 500

    return jsonify(quiz=quiz.to_dict(include_answers=True)), 201


@bp.get("/<quiz_id>")
def get_quiz(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None or not can_view_quiz(quiz, g.user):
        return jsonify(error="quiz_not_found"), 404
    include_answers = request.args.get("edit") == "1" and can_edit_quiz(quiz, g.user)
    data = quiz.to_dict(include_answers=include_answers)
    data["study_modes"] = available_modes(quiz)
    return jsonify(quiz=data)


@bp.put("/<quiz_id>")
@login_required
def update_quiz(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None:
        return jsonify(error="quiz_not_found"), 404
    if not can_edit_quiz(quiz, g.user):
        return jsonify(error="forbidden"), 403

    payload = request.get_json(silent=True)
    errors = validate_quiz(payload)
    if errors:
        return jsonify(error="validation_error", fields=errors), 400

    quiz.title = clean_text(payload["title"])
    quiz.subject = clean_text(payload["subject"])
    quiz.description = clean_text(payload.get("description"))
    if quiz.owner_id == g.user.id:
        quiz.visibility = clean_text(payload.get("visibility") or "public")
    replace_questions(quiz, payload["questions"], remove_existing=True)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to update quiz")
        return jsonify(error="database_error"), 500
    return jsonify(quiz=quiz.to_dict(include_answers=True))


@bp.delete("/<quiz_id>")
@login_required
def delete_quiz(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None:
        return jsonify(error="quiz_not_found"), 404
    if quiz.owner_id != g.user.id:
        return jsonify(error="forbidden"), 403
    try:
        db.session.delete(quiz)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete quiz")
        return jsonify(error="database_error"), 500
    return "", 204


@bp.get("/<quiz_id>/collaborators")
@login_required
def list_collaborators(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None:
        return jsonify(error="quiz_not_found"), 404
    if quiz.owner_id != g.user.id:
        return jsonify(error="forbidden"), 403
    collaborations = db.session.scalars(
        select(QuizCollaborator).where(QuizCollaborator.quiz_set_id == quiz.id)
    ).all()
    return jsonify(collaborators=[{
        "user_id": item.user_id,
        "email": item.user.email,
        "display_name": item.user.display_name,
        "can_edit": item.can_edit,
    } for item in collaborations])


@bp.post("/<quiz_id>/collaborators")
@login_required
def add_collaborator(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None:
        return jsonify(error="quiz_not_found"), 404
    if quiz.owner_id != g.user.id:
        return jsonify(error="forbidden"), 403
    payload = request.get_json(silent=True)
    email = clean_text(payload.get("email") if isinstance(payload, dict) else "").lower()
    if not email:
        return jsonify(error="validation_error", message="공유할 이메일을 입력해 주세요."), 400
    user = db.session.scalar(select(User).where(User.email == email))
    if user is None:
        return jsonify(error="user_not_found", message="SAMSAM에 가입한 사용자를 찾을 수 없습니다."), 404
    if user.id == g.user.id:
        return jsonify(error="invalid_collaborator", message="자신은 공동 편집자로 추가할 수 없습니다."), 400
    existing = get_collaboration(quiz, user)
    if existing:
        return jsonify(error="already_shared", message="이미 공유한 사용자입니다."), 409
    collaboration = QuizCollaborator(quiz_set_id=quiz.id, user_id=user.id, can_edit=True)
    try:
        db.session.add(collaboration)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to add quiz collaborator")
        return jsonify(error="database_error"), 500
    return jsonify(collaborator={"user_id": user.id, "email": user.email, "display_name": user.display_name, "can_edit": True}), 201


@bp.delete("/<quiz_id>/collaborators/<user_id>")
@login_required
def remove_collaborator(quiz_id, user_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None:
        return jsonify(error="quiz_not_found"), 404
    if quiz.owner_id != g.user.id:
        return jsonify(error="forbidden"), 403
    collaboration = db.session.scalar(select(QuizCollaborator).where(
        QuizCollaborator.quiz_set_id == quiz.id,
        QuizCollaborator.user_id == user_id,
    ))
    if collaboration is None:
        return jsonify(error="collaborator_not_found"), 404
    db.session.delete(collaboration)
    db.session.commit()
    return "", 204


@bp.post("/<quiz_id>/grade")
def grade_quiz(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None or not can_view_quiz(quiz, g.user):
        return jsonify(error="quiz_not_found"), 404

    payload = request.get_json(silent=True)
    answers = payload.get("answers") if isinstance(payload, dict) else None
    if not isinstance(answers, list) or len(answers) != len(quiz.questions):
        return jsonify(error="invalid_answers", message="모든 문항에 답해 주세요."), 400

    results = []
    for question, answer in zip(quiz.questions, answers):
        if question.question_type in {"multiple_choice", "true_false"} and (
            isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer < len(question.choices)
        ):
            return jsonify(error="invalid_answers", message="답안 형식이 올바르지 않습니다."), 400
        if question.question_type == "fill_blank" and not isinstance(answer, str):
            return jsonify(error="invalid_answers", message="빈칸 답안을 입력해 주세요."), 400
        if question.question_type == "flashcard" and not isinstance(answer, bool):
            return jsonify(error="invalid_answers", message="카드 학습 여부를 선택해 주세요."), 400
        correct_index = next(choice.position for choice in question.choices if choice.is_correct)
        if question.question_type == "fill_blank":
            normalized_answer = " ".join(answer.casefold().split())
            normalized_correct = " ".join(question.choices[correct_index].text.casefold().split())
            is_correct = normalized_answer == normalized_correct
        elif question.question_type == "flashcard":
            is_correct = answer
        else:
            is_correct = answer == correct_index
        results.append(
            {
                "position": question.position,
                "selected_answer": answer,
                "correct_index": correct_index,
                "correct": is_correct,
                "explanation": question.explanation,
                "explanation_image_data": question.explanation_image_data,
            }
        )

    correct_count = sum(result["correct"] for result in results)
    score = round(correct_count / len(results) * 100)
    attempt = QuizAttempt(
        quiz_set_id=quiz.id,
        user_id=g.user.id if g.user else None,
        answers=answers,
        score=score,
        correct_count=correct_count,
        total_count=len(results),
    )
    try:
        db.session.add(attempt)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to save quiz attempt")
        return jsonify(error="database_error"), 500

    return jsonify(
        attempt_id=attempt.id,
        completed_at=attempt.completed_at.isoformat(),
        score=score,
        correct_count=correct_count,
        total_count=len(results),
        results=results,
    )


@bp.get("/<quiz_id>/match")
def match_pairs(quiz_id):
    quiz = db.session.get(QuizSet, quiz_id)
    if quiz is None or not can_view_quiz(quiz, g.user):
        return jsonify(error="quiz_not_found"), 404
    pairs = [
        {
            "id": question.id,
            "term": question.prompt,
            "answer": next(choice.text for choice in question.choices if choice.is_correct),
        }
        for question in quiz.questions[:8]
    ]
    return jsonify(quiz={"id": quiz.id, "title": quiz.title}, pairs=pairs)
