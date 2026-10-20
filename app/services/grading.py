"""Answer validation and grading, independent of HTTP and persistence."""

import re
import unicodedata
import hashlib
import json


def normalize(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold()).strip(".!。")


def meaning_variants(answer):
    variants = {normalize(answer)}
    for part in re.split(r"[,;/]|\n", answer):
        variants.add(normalize(part))
        variants.add(normalize(re.sub(r"\([^)]*\)", "", part)))
    return variants - {""}


def check_answer(question, answer):
    if question["type"] in {"meaning", "fill_blank"}:
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 300:
            raise ValueError("뜻을 300자 이내로 입력해 주세요.")
        correct = (normalize(answer) in meaning_variants(question["answer"]) if question["type"] == "meaning"
                   else " ".join(answer.casefold().split()) == " ".join(question["answer"].casefold().split()))
    elif question["type"] == "flashcard":
        if type(answer) is not bool:
            raise ValueError("카드 학습 여부를 선택해 주세요.")
        correct = answer
    elif question["type"] == "sentence":
        if (not isinstance(answer, list) or len(answer) != len(question["choices"])
                or any(type(i) is not int for i in answer)
                or sorted(answer) != list(range(len(question["choices"])))):
            raise ValueError("모든 단어를 한 번씩 사용해 문장을 완성해 주세요.")
        assembled = " ".join(question["choices"][i] for i in answer)
        correct = assembled == " ".join(question["answer"].split())
    else:
        if type(answer) is not int or not 0 <= answer < len(question["choices"]):
            raise ValueError("보기에서 답을 골라 주세요.")
        correct = answer == question["correct_index"]
    identity = question.get("review_key") or [question["type"], question.get("prompt", ""), question["answer"]]
    review_id = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
    return dict(correct=correct, review_id=review_id, correct_answer=question["answer"], selected_answer=assembled if question["type"] == "sentence" else answer,
                explanation=question["explanation"], source=question.get("source", ""),
                explanation_image_data=question.get("explanation_image_data"))
