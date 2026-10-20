import base64
import binascii
import re


SUPPORTED_QUESTION_TYPES = {"multiple_choice", "flashcard", "fill_blank", "true_false"}
SUPPORTED_VISIBILITIES = {"public", "private"}
IMAGE_PATTERN = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")
MAX_IMAGE_BYTES = 600 * 1024


def clean_text(value):
    return value.strip() if isinstance(value, str) else ""


def validate_quiz(payload):
    errors = {}
    if not isinstance(payload, dict):
        return {"body": "JSON 객체가 필요합니다."}

    title = clean_text(payload.get("title"))
    subject = clean_text(payload.get("subject"))
    description = clean_text(payload.get("description"))
    questions = payload.get("questions")
    visibility = clean_text(payload.get("visibility") or "public")

    if not title:
        errors["title"] = "퀴즈 제목을 입력해 주세요."
    elif len(title) > 120:
        errors["title"] = "퀴즈 제목은 120자 이하여야 합니다."
    if not subject:
        errors["subject"] = "과목을 입력해 주세요."
    elif len(subject) > 50:
        errors["subject"] = "과목은 50자 이하여야 합니다."
    elif any(character.isspace() for character in subject):
        errors["subject"] = "과목에는 띄어쓰기를 사용할 수 없습니다."
    if len(description) > 1_000:
        errors["description"] = "설명은 1,000자 이하여야 합니다."
    if visibility not in SUPPORTED_VISIBILITIES:
        errors["visibility"] = "공개 또는 비공개만 선택할 수 있습니다."
    if not isinstance(questions, list) or not questions:
        errors["questions"] = "문항을 한 개 이상 추가해 주세요."
        return errors
    if len(questions) > 100:
        errors["questions"] = "한 퀴즈에는 문항을 최대 100개까지 추가할 수 있습니다."
        return errors

    for index, question in enumerate(questions):
        prefix = f"questions.{index}"
        if not isinstance(question, dict):
            errors[prefix] = "문항 형식이 올바르지 않습니다."
            continue
        prompt = clean_text(question.get("prompt"))
        explanation = clean_text(question.get("explanation"))
        image_data = clean_text(question.get("image_data"))
        explanation_image_data = clean_text(question.get("explanation_image_data"))
        choices = question.get("choices")
        correct_index = question.get("correct_index")
        question_type = clean_text(
            question.get("question_type") or question.get("type") or "multiple_choice"
        )

        if question_type not in SUPPORTED_QUESTION_TYPES:
            errors[f"{prefix}.question_type"] = "지원하지 않는 문제 유형입니다."
        if not prompt:
            errors[f"{prefix}.prompt"] = "질문을 입력해 주세요."
        elif len(prompt) > 1_000:
            errors[f"{prefix}.prompt"] = "질문은 1,000자 이하여야 합니다."
        if len(explanation) > 2_000:
            errors[f"{prefix}.explanation"] = "해설은 2,000자 이하여야 합니다."

        if image_data:
            match = IMAGE_PATTERN.fullmatch(image_data)
            if match is None:
                errors[f"{prefix}.image_data"] = "PNG, JPEG, WebP 이미지만 첨부할 수 있습니다."
            else:
                try:
                    image_bytes = base64.b64decode(match.group(2), validate=True)
                except (binascii.Error, ValueError):
                    errors[f"{prefix}.image_data"] = "이미지 데이터가 올바르지 않습니다."
                else:
                    if len(image_bytes) > MAX_IMAGE_BYTES:
                        errors[f"{prefix}.image_data"] = "이미지는 한 장당 600KB 이하여야 합니다."

        if explanation_image_data:
            match = IMAGE_PATTERN.fullmatch(explanation_image_data)
            if match is None:
                errors[f"{prefix}.explanation_image_data"] = "PNG, JPEG, WebP 이미지만 첨부할 수 있습니다."
            else:
                try:
                    image_bytes = base64.b64decode(match.group(2), validate=True)
                except (binascii.Error, ValueError):
                    errors[f"{prefix}.explanation_image_data"] = "해설 이미지 데이터가 올바르지 않습니다."
                else:
                    if len(image_bytes) > MAX_IMAGE_BYTES:
                        errors[f"{prefix}.explanation_image_data"] = "해설 이미지는 한 장당 600KB 이하여야 합니다."

        if question_type == "multiple_choice":
            minimum, maximum = 2, 6
        elif question_type == "true_false":
            minimum, maximum = 2, 2
        else:
            minimum, maximum = 1, 1
        if not isinstance(choices, list) or not minimum <= len(choices) <= maximum:
            errors[f"{prefix}.choices"] = (
                "선택지는 2개 이상 6개 이하여야 합니다."
                if question_type == "multiple_choice"
                else "이 문제 유형에 필요한 답안을 입력해 주세요."
            )
            continue
        cleaned_choices = [clean_text(choice) for choice in choices]
        if any(not choice for choice in cleaned_choices):
            errors[f"{prefix}.choices"] = "모든 선택지 또는 답안을 입력해 주세요."
        elif any(len(choice) > 300 for choice in cleaned_choices):
            errors[f"{prefix}.choices"] = "답안은 각각 300자 이하여야 합니다."
        if question_type in {"multiple_choice", "true_false"} and (
            isinstance(correct_index, bool)
            or not isinstance(correct_index, int)
            or not 0 <= correct_index < len(choices)
        ):
            errors[f"{prefix}.correct_index"] = "정답을 지정해 주세요."
        if question_type == "true_false" and cleaned_choices != ["O", "X"]:
            errors[f"{prefix}.choices"] = "O/X 문항의 선택지는 O와 X여야 합니다."
        if question_type == "fill_blank" and "___" not in prompt and cleaned_choices[0].casefold() not in prompt.casefold():
            errors[f"{prefix}.prompt"] = "빈칸 정답은 입력한 본문 안에 포함되어야 합니다."
    return errors
