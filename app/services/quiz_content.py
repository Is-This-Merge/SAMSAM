import re

from ..db import db
from ..models import Choice, Question
from .quiz_validation import clean_text


def replace_questions(quiz, question_payloads, *, remove_existing=False):
    """검증된 문항 payload로 퀴즈 내용을 구성한다."""
    if remove_existing:
        quiz.questions.clear()
        db.session.flush()

    for question_index, data in enumerate(question_payloads, start=len(quiz.questions)):
        question_type = clean_text(
            data.get("question_type") or data.get("type") or "multiple_choice"
        )
        prompt = clean_text(data["prompt"])
        choices = [clean_text(choice) for choice in data["choices"]]
        if question_type == "fill_blank" and "___" not in prompt and choices:
            prompt = re.sub(re.escape(choices[0]), "___", prompt, count=1, flags=re.IGNORECASE)
        question = Question(
            position=question_index,
            question_type=question_type,
            prompt=prompt,
            explanation=clean_text(data.get("explanation")),
            image_data=clean_text(data.get("image_data")) or None,
            explanation_image_data=clean_text(data.get("explanation_image_data")) or None,
        )
        correct_index = data.get("correct_index", 0)
        question.choices.extend(
            Choice(
                position=choice_index,
                text=clean_text(choice_text),
                is_correct=choice_index == correct_index,
            )
            for choice_index, choice_text in enumerate(choices)
        )
        quiz.questions.append(question)
