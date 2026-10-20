"""Build random, position-based blanks from arbitrary input text."""

import random
import re
import hashlib

WORD = re.compile(r"\b[A-Za-z]+(?:['’\-][A-Za-z]+)*\b")


def validate_options(options):
    if not isinstance(options, dict):
        raise ValueError("본문 설정이 올바르지 않습니다.")
    text = options.get("text", "")
    if not isinstance(text, str) or not text.strip() or len(text) > 30000:
        raise ValueError("영어 본문을 1~30,000자 이내로 입력해 주세요.")
    count = options.get("blank_count", 3)
    size = options.get("chunk_words", 80)
    if type(count) is not int or not 1 <= count <= 10:
        raise ValueError("빈칸 개수는 1~10개로 선택해 주세요.")
    if type(size) is not int or size not in {0, 40, 80, 120}:
        raise ValueError("본문 범위를 다시 선택해 주세요.")
    if len({m.group().casefold() for m in WORD.finditer(text)}) < 4:
        raise ValueError("서로 다른 영어 단어가 4개 이상 있는 본문을 입력해 주세요.")
    return dict(text=text, blank_count=count, chunk_words=size)


def generate_cloze(options, seed, source="직접 입력한 본문"):
    options = validate_options(options)
    text = options["text"]
    rng = random.Random(seed)
    matches = list(WORD.finditer(text))
    pool = list(dict.fromkeys(m.group() for m in matches))
    size = options["chunk_words"] or len(matches)
    questions = []
    for group, start in enumerate(range(0, len(matches), size)):
        end = min(start + size, len(matches))
        left = 0 if start == 0 else matches[start].start()
        right = matches[end].start() if end < len(matches) else len(text)
        selected = sorted(rng.sample(range(start, end), min(options["blank_count"], end - start)))
        fragments = []
        cursor = left
        for number, index in enumerate(selected, 1):
            word = matches[index]
            fragments.extend([text[cursor:word.start()], f"⟦{number}⟧ ___"])
            cursor = word.end()
        fragments.append(text[cursor:right])
        prompt = "".join(fragments)
        for number, index in enumerate(selected, 1):
            answer = matches[index].group()
            # Case-insensitive uniqueness avoids indistinguishable distractors.
            distractors = list({w.casefold(): w for w in pool if w.casefold() != answer.casefold()}.values())
            choices = [answer] + rng.sample(distractors, 3)
            rng.shuffle(choices)
            questions.append(dict(type="article", prompt=prompt, choices=choices,
                                  review_key=f"{hashlib.sha256(text.encode()).hexdigest()}:{matches[index].start()}",
                                  answer=answer, correct_index=choices.index(answer),
                                  explanation=text[left:right], source=source,
                                  group=group, blank_number=number, blank_count=len(selected)))
    return questions
