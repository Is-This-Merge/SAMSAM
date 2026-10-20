from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import func, select

from app.db import db
from app.models import QuizAttempt, QuizSet
from app.seed import load_samples, seed_samples
from app.services.study_modes import build_round, meaning_variants, normalize


@pytest.fixture()
def samples(client):
    seed_samples(load_samples())
    return {s["key"]: str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{s['key']}")) for s in load_samples()}


def test_meaning_input_grading_and_no_answer_leak(client, samples):
    quiz_id = samples["exam-vocabulary"]
    data = client.get(f"/api/quizzes/{quiz_id}/study?mode=meaning").json
    assert len(data["quiz"]["questions"]) == 50
    meanings = {q["prompt"]: q["choices"][0] for s in load_samples() if s["key"] == "exam-vocabulary" for q in s["questions"]}
    answers = []
    for q in data["quiz"]["questions"]:
        assert q["choices"] == []
        assert "answer" not in q and "explanation" not in q
        answers.append(meanings[q["prompt"]].split(",")[0])
    answers[0] = "틀린 답"
    check = client.post(f"/api/quizzes/{quiz_id}/study/check", json=dict(token=data["token"], position=0, answer=answers[0]))
    assert check.status_code == 200 and check.json["correct"] is False
    result = client.post(f"/api/quizzes/{quiz_id}/study/grade", json=dict(token=data["token"], answers=answers))
    assert result.status_code == 200
    assert result.json["correct_count"] == 49
    assert db.session.get(QuizAttempt, result.json["attempt_id"]).total_count == 50
    assert normalize("회복력이강한") in meaning_variants("회복력이 강한")
    assert normalize("꿀") in meaning_variants("(꽃의) 꿀")
    assert normalize("탐욕적인") in meaning_variants("탐욕적인, 게걸스러운")
    assert normalize("독") not in meaning_variants("고독한")


def test_articles_randomized_reproducible_and_graded(client, samples):
    for key, quiz_id in samples.items():
        detail = client.get(f"/api/quizzes/{quiz_id}").json["quiz"]
        assert "meaning" in detail["study_modes"]
        assert set(detail["study_modes"]) == {"meaning", "article", "sentence", "comprehension"}
        quiz = db.session.get(QuizSet, quiz_id)
        first = build_round(quiz, "article", "fixed")
        assert first == build_round(quiz, "article", "fixed")
        variants = {tuple(q["prompt"] for q in build_round(quiz, "article", str(i))) for i in range(10)}
        assert len(variants) > 1
        for q in first:
            assert q["prompt"].count("___") == q["blank_count"]
            assert len(set(q["choices"])) == 4
            restored = q["prompt"]
            for blank in first:
                if blank["group"] == q["group"]:
                    restored = restored.replace(f"⟦{blank['blank_number']}⟧ ___", blank["answer"], 1)
            assert restored == q["explanation"]
        data = client.get(f"/api/quizzes/{quiz_id}/study?mode=article").json
        answers = []
        for i, q in enumerate(data["quiz"]["questions"]):
            assert "correct_index" not in q
            checked = client.post(f"/api/quizzes/{quiz_id}/study/check", json=dict(token=data["token"], position=i, answer=0)).json
            answers.append(q["choices"].index(checked["correct_answer"]))
        result = client.post(f"/api/quizzes/{quiz_id}/study/grade", json=dict(token=data["token"], answers=answers))
        assert result.status_code == 200 and result.json["score"] == 100


def test_invalid_round_and_answers_do_not_save(client, samples):
    quiz_id = samples["exam-vocabulary"]
    data = client.get(f"/api/quizzes/{quiz_id}/study?mode=article").json
    endpoint = f"/api/quizzes/{quiz_id}/study/grade"
    for payload in [None, {}, dict(token="invalid", answers=[0, 0]), dict(token=data["token"], answers=[True, 0]), dict(token=data["token"], answers=[0]), dict(token=data["token"], answers=[999, 0])]:
        assert client.post(endpoint, json=payload).status_code == 400
    assert client.post(f"/api/quizzes/{samples['exam-vocabulary-endurance']}/study/grade", json=dict(token=data["token"], answers=[0, 0])).status_code == 400
    assert client.get(f"/api/quizzes/{quiz_id}/study?mode=unknown").status_code == 400
    assert db.session.scalar(select(func.count(QuizAttempt.id))) == 0


def test_private_round_access_and_changed_content(client, samples):
    quiz_id = samples["exam-vocabulary"]
    data = client.get(f"/api/quizzes/{quiz_id}/study?mode=meaning").json
    quiz = db.session.get(QuizSet, quiz_id)
    quiz.questions[0].prompt = "Changed word"
    db.session.commit()
    assert client.post(f"/api/quizzes/{quiz_id}/study/check", json=dict(token=data["token"], position=0, answer="test")).status_code == 400
    quiz.visibility = "private"
    db.session.commit()
    assert client.get(f"/api/quizzes/{quiz_id}/study?mode=meaning").status_code == 404
    assert client.post(f"/api/quizzes/{quiz_id}/study/check", json=dict(token=data["token"], position=0, answer="test")).status_code == 404


def test_pdf_numbering_and_order(client, samples):
    listed = client.get("/api/quizzes").json["quizzes"]
    assert [q["title"][:3] for q in listed] == ["01.", "02.", "03.", "04.", "05."]
    for number, q in enumerate(listed, 1):
        detail = client.get(f"/api/quizzes/{q['id']}").json["quiz"]
        first = client.get(f"/api/quizzes/{q['id']}/study?mode=meaning").json["quiz"]["questions"]
        second = client.get(f"/api/quizzes/{q['id']}/study?mode=meaning").json["quiz"]["questions"]
        assert [item["prompt"] for item in first] == [item["prompt"] for item in detail["questions"]]
        assert all("number" not in item for item in first + detail["questions"])
        assert first == second


def test_sentence_and_comprehension_rounds(client, samples):
    from app.services.study_modes import article_passages, check_answer
    from app.views.study_views import serializer
    for quiz_id in samples.values():
        quiz = db.session.get(QuizSet, quiz_id)
        passages = " ".join(p["text"] for p in article_passages(quiz_id))
        for mode in ["sentence", "comprehension"]:
            data = client.get(f"/api/quizzes/{quiz_id}/study?mode={mode}").json
            seed = serializer().loads(data["token"])["seed"]
            generated = build_round(quiz, mode, seed)
            assert len(generated) == (5 if mode == "sentence" else len(article_passages(quiz_id)))
            assert generated == build_round(quiz, mode, seed)
            answers = []
            for i, q in enumerate(data["quiz"]["questions"]):
                assert "answer" not in q and "correct_index" not in q
                if mode == "sentence":
                    assert generated[i]["answer"] in passages
                    words = generated[i]["answer"].split()
                    unused = list(range(len(q["choices"])))
                    order = []
                    for word in words:
                        index = next(index for index in unused if q["choices"][index] == word)
                        unused.remove(index)
                        order.append(index)
                    answers.append(order)
                else:
                    source = next(p for p in article_passages(quiz_id) if p["text"] == q["prompt"])
                    assert any("\uac00" <= char <= "\ud7a3" for char in source["translation"])
                    answers.append(q["choices"].index(source["translation"]))
                checked = client.post(f"/api/quizzes/{quiz_id}/study/check", json=dict(token=data["token"], position=i, answer=answers[-1]))
                assert checked.status_code == 200 and checked.json["correct"] is True
            result = client.post(f"/api/quizzes/{quiz_id}/study/grade", json=dict(token=data["token"], answers=answers))
            assert result.status_code == 200 and result.json["score"] == 100
        q = build_round(quiz, "sentence", "seed")[0]
        variants = {tuple(item["answer"] for item in build_round(quiz, "sentence", str(seed))) for seed in range(10)}
        assert len(variants) > 1
        for invalid in [[], [0] * len(q["choices"]), [True] * len(q["choices"]), "not a list"]:
            with pytest.raises(ValueError):
                check_answer(q, invalid)
    duplicate = dict(type="sentence", choices=["the", "cat", "the", "dog"], answer="the cat the dog", explanation="")
    assert check_answer(duplicate, [2, 1, 0, 3])["correct"]
    assert not check_answer(duplicate, [0, 3, 2, 1])["correct"]


def test_standard_mode_supports_immediate_checks_for_every_question_type(client):
    from app.services.quiz_content import replace_questions
    quiz = QuizSet(title="Mixed practice", subject="ERW")
    replace_questions(quiz, [
        dict(type="flashcard", prompt="word", choices=["meaning"]),
        dict(type="fill_blank", prompt="A ___ B", choices=["test"]),
        dict(type="multiple_choice", prompt="Pick", choices=["no", "yes"], correct_index=1),
        dict(type="true_false", prompt="True", choices=["O", "X"], correct_index=0),
    ])
    db.session.add(quiz); db.session.commit()
    prefix = f"/api/quizzes/{quiz.id}/study"
    data = client.get(prefix + "?mode=standard").json
    assert data["quiz"]["questions"][1]["choices"] == []
    assert all("explanation" not in q for q in data["quiz"]["questions"])
    wrong = [False, "wrong", 0, 1]
    right = [True, " TEST ", 1, 0]
    for i in range(4):
        for answer, expected in [(wrong[i], False), (right[i], True)]:
            response = client.post(prefix + "/check", json=dict(token=data["token"], position=i, answer=answer))
            assert response.status_code == 200
            assert response.json["correct"] is expected
    assert db.session.scalar(select(func.count(QuizAttempt.id))) == 0
    result = client.post(prefix + "/grade", json=dict(token=data["token"], answers=right))
    assert result.status_code == 200 and result.json["score"] == 100
    assert db.session.scalar(select(func.count(QuizAttempt.id))) == 1
