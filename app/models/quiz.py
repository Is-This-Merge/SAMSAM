from datetime import datetime, timezone
from uuid import uuid4

from ..db import db


def new_id():
    return str(uuid4())


class QuizSet(db.Model):
    __tablename__ = "quiz_sets"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    title = db.Column(db.String(120), nullable=False, index=True)
    subject = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    visibility = db.Column(db.String(20), nullable=False, default="public", index=True)
    owner_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    questions = db.relationship(
        "Question",
        back_populates="quiz_set",
        cascade="all, delete-orphan",
        order_by="Question.position",
        lazy="selectin",
    )
    attempts = db.relationship(
        "QuizAttempt",
        back_populates="quiz_set",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    owner = db.relationship("User", back_populates="quizzes")
    collaborators = db.relationship(
        "QuizCollaborator",
        back_populates="quiz_set",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def to_dict(self, include_answers=False):
        return {
            "id": self.id,
            "title": self.title,
            "subject": self.subject,
            "description": self.description,
            "visibility": self.visibility,
            "questions": [
                question.to_dict(include_answer=include_answers)
                for question in self.questions
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Question(db.Model):
    __tablename__ = "questions"
    __table_args__ = (
        db.UniqueConstraint("quiz_set_id", "position", name="uq_question_position"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    quiz_set_id = db.Column(
        db.String(36),
        db.ForeignKey("quiz_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = db.Column(db.Integer, nullable=False)
    question_type = db.Column(
        db.String(30), nullable=False, default="multiple_choice"
    )
    prompt = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False, default="")
    image_data = db.Column(db.Text, nullable=True)
    explanation_image_data = db.Column(db.Text, nullable=True)

    quiz_set = db.relationship("QuizSet", back_populates="questions")
    choices = db.relationship(
        "Choice",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Choice.position",
        lazy="selectin",
    )

    def to_dict(self, include_answer=False):
        data = {
            "id": self.id,
            "position": self.position,
            "type": self.question_type,
            "prompt": self.prompt,
            "explanation": self.explanation,
            "image_data": self.image_data,
            "explanation_image_data": self.explanation_image_data,
            "choices": [choice.text for choice in self.choices],
        }
        if include_answer:
            data["correct_index"] = next(
                (
                    choice.position
                    for choice in self.choices
                    if choice.is_correct
                ),
                None,
            )
        return data


class Choice(db.Model):
    __tablename__ = "choices"
    __table_args__ = (
        db.UniqueConstraint("question_id", "position", name="uq_choice_position"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    question_id = db.Column(
        db.String(36),
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String(300), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)

    question = db.relationship("Question", back_populates="choices")


class QuizAttempt(db.Model):
    """한 번의 퀴즈 풀이 결과.

    사용자 기능이 추가되기 전까지는 익명 기록으로 저장하고, 4단계에서
    사용자 외래 키를 추가할 수 있도록 퀴즈 기록을 별도 테이블로 둔다.
    """

    __tablename__ = "quiz_attempts"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    quiz_set_id = db.Column(
        db.String(36),
        db.ForeignKey("quiz_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    answers = db.Column(db.JSON, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    correct_count = db.Column(db.Integer, nullable=False)
    total_count = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    quiz_set = db.relationship("QuizSet", back_populates="attempts")
    user = db.relationship("User", back_populates="attempts")
