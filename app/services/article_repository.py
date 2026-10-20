"""Local article corpus and stable vocabulary-set identifiers."""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


TOPICS = ["wasps", "digital-detox", "friendships", "new-start", "endurance"]


def vocabulary_key(topic):
    return "exam-vocabulary" if topic == "wasps" else f"exam-vocabulary-{topic}"


def topic_for_quiz(quiz_id):
    return next((topic for topic in TOPICS if str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{vocabulary_key(topic)}")) == quiz_id), None)


def quiz_number(quiz_id):
    topic = topic_for_quiz(quiz_id)
    return TOPICS.index(topic) + 1 if topic else None


def article_passages(quiz_id):
    data = json.loads((Path(__file__).parents[1] / "data" / "article_passages.json").read_text(encoding="utf-8"))
    return next((s["passages"] for s in data if s["key"] == topic_for_quiz(quiz_id)), [])


