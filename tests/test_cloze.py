import pytest

from app.services.cloze import generate_cloze, validate_options


def restore_group(questions):
    text = questions[0]["prompt"]
    for q in questions:
        text = text.replace(f"⟦{q['blank_number']}⟧ ___", q["answer"], 1)
    return text


def test_arbitrary_text_multiple_blanks_preserves_exact_positions_and_punctuation():
    text = "Apple, apple! Birds fly; don't stop.\n\nApple trees grow quickly."
    options = dict(text=text, chunk_words=0, blank_count=10)
    questions = generate_cloze(options, "seed")
    assert len(questions) == 10
    assert restore_group(questions) == text
    assert all(q["prompt"].count("___") == 10 for q in questions)
    assert all(len({w.casefold() for w in q["choices"]}) == 4 for q in questions)
    assert questions == generate_cloze(options, "seed")
    assert questions != generate_cloze(options, "other")


def test_word_chunks_cross_paragraphs_and_reassemble_the_input():
    text = ("alpha beta gamma delta epsilon\n\n" * 19) + "omega"
    questions = generate_cloze(dict(text=text, chunk_words=40, blank_count=3), "seed")
    assert len(questions) == 9
    groups = [[q for q in questions if q["group"] == i] for i in range(3)]
    assert "".join(restore_group(group) for group in groups) == text
    assert groups[0][0]["explanation"].count("\n\n") > 1


def test_short_tail_caps_blanks_and_no_manual_target_list_is_needed():
    questions = generate_cloze(dict(text="one two three four", chunk_words=0, blank_count=10), "seed")
    assert len(questions) == 4
    assert {q["answer"] for q in questions} == {"one", "two", "three", "four"}
    assert restore_group(questions) == "one two three four"


@pytest.mark.parametrize("options", [None, {}, {"text": ""}, {"text": "same SAME same same"},
    {"text": "a" * 30001}, {"text": "one two three four", "blank_count": True},
    {"text": "one two three four", "blank_count": 0}, {"text": "one two three four", "blank_count": 11},
    {"text": "one two three four", "chunk_words": 1}, {"text": "one two three four", "chunk_words": False}])
def test_bad_input_rejected(options):
    with pytest.raises(ValueError):
        validate_options(options)


def test_custom_source_is_used_for_generation_and_signed_grading(client):
    from app.seed import load_samples, seed_samples
    from app.db import db
    from app.models import QuizSet
    from sqlalchemy import select
    from app.views.study_views import serializer
    seed_samples(load_samples())
    quiz = db.session.scalar(select(QuizSet))
    url = f"/api/quizzes/{quiz.id}/study"
    options = dict(text="Unique robots explore distant planets. They collect stones carefully.", chunk_words=0, blank_count=4)
    response = client.post(url + "?mode=article", json=options)
    assert response.status_code == 200
    data = response.json
    assert len(data["quiz"]["questions"]) == 4
    assert all("answer" not in q and "explanation" not in q for q in data["quiz"]["questions"])
    payload = serializer().loads(data["token"])
    generated = generate_cloze(options, payload["seed"], "입력한 본문")
    answers = [q["correct_index"] for q in generated]
    result = client.post(url + "/grade", json=dict(token=data["token"], answers=answers))
    assert result.status_code == 200 and result.json["score"] == 100
    wrong = client.post(url + "/check", json=dict(token=data["token"], position=0, answer=(answers[0] + 1) % 4))
    assert wrong.json["correct"] is False
    tampered = data["token"][:-6] + "broken"
    assert client.post(url + "/check", json=dict(token=tampered, position=0, answer=answers[0])).status_code == 400
    assert client.post(url + "?mode=article", json=dict(text="same same")).status_code == 400
    assert client.post(url + "?mode=meaning", json=options).status_code == 400
