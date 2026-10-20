"""Compose reproducible rounds; grading and source data live in dedicated services."""

import hashlib
import json
import random

from .article_repository import TOPICS, article_passages, quiz_number, topic_for_quiz, vocabulary_key
from .sentences import sentence_candidates
from .grading import check_answer, meaning_variants, normalize
from .cloze import generate_cloze


def available_modes(quiz):
    modes = []
    if any(q.question_type == "flashcard" for q in quiz.questions):
        modes.append("meaning")
    modes.append("article")
    passages = article_passages(quiz.id)
    if passages:
        modes.append("sentence")
    if len([p for p in passages if p.get("translation")]) > 1:
        modes.append("comprehension")
    return modes


def build_round(quiz, mode, seed, options=None):
    rng = random.Random(seed)
    questions = []
    if mode == "standard":
        for q in quiz.questions:
            choices = [c.text for c in q.choices]
            correct = next(c.position for c in q.choices if c.is_correct)
            questions.append(dict(type=q.question_type, prompt=q.prompt, choices=choices,
                                  answer=choices[correct], correct_index=correct,
                                  explanation=q.explanation, image_data=q.image_data,
                                  explanation_image_data=q.explanation_image_data))
    elif mode == "meaning":
        for q in quiz.questions:
            if q.question_type != "flashcard":
                continue
            answer = next(c.text for c in q.choices if c.is_correct)
            questions.append(dict(type="meaning", prompt=q.prompt, choices=[], answer=answer,
                                  explanation=q.explanation))
    elif mode == "article":
        if options is None:
            passages = article_passages(quiz.id)
            if not passages:
                return []
            options = dict(text="\n\n".join(p["text"] for p in passages), blank_count=3, chunk_words=80)
            source = " / ".join(dict.fromkeys(p["source"] for p in passages))
        else:
            source = "입력한 본문"
        questions = generate_cloze(options, seed, source)
    elif mode == "sentence":
        candidates = sentence_candidates(article_passages(quiz.id))
        for item in rng.sample(candidates, min(5, len(candidates))):
            words = item["text"].split()
            shuffled = words[:]
            rng.shuffle(shuffled)
            if shuffled == words:
                shuffled = shuffled[1:] + shuffled[:1]
            questions.append(dict(type="sentence", prompt=item["prompt"], choices=shuffled,
                                  answer=item["text"], explanation=item["text"], source=item["source"]))
    elif mode == "comprehension":
        passages = [p for p in article_passages(quiz.id) if p.get("translation")]
        if len(passages) < 2:
            return []
        rng.shuffle(passages)
        for item in passages:
            answer = item["translation"]
            others = list(dict.fromkeys(p["translation"] for p in passages if p["translation"] != answer))
            choices = [answer, *rng.sample(others, min(3, len(others)))]
            rng.shuffle(choices)
            questions.append(dict(type="comprehension", prompt=item["text"], choices=choices,
                                  answer=answer, correct_index=choices.index(answer),
                                  explanation=answer, source=item["source"]))
    return questions


def round_digest(questions):
    return hashlib.sha256(json.dumps(questions, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def public_questions(questions):
    result = []
    for q in questions:
        public = {k: v for k, v in q.items() if k in {"type", "prompt", "choices", "source", "image_data", "group", "blank_number", "blank_count"}}
        if q["type"] == "fill_blank":
            public["choices"] = []
        result.append(public)
    return result


