from app.db import db
from app.models import QuizSet
from app.seed import load_samples, seed_samples, correct_vocabulary


def test_reader_anonymous_full_text_and_translation(client):
    seed_samples(load_samples())
    with client.session_transaction() as session:
        session.clear()
    assert client.get("/article.html").status_code == 200
    for quiz in db.session.query(QuizSet).all():
        response = client.get(f"/api/quizzes/{quiz.id}/article-source")
        assert response.status_code == 200
        data = response.json
        assert len(data["passages"]) > 1
        assert all(p["translation"] and p["text"] for p in data["passages"])
        assert data["text"] == "\n\n".join(p["text"] for p in data["passages"])


def test_errata_preserves_ids_and_is_repeatable(client):
    seed_samples(load_samples())
    questions = [q for quiz in db.session.query(QuizSet).all() for q in quiz.questions]
    replacements = {"diarrhea": "diarrhoea", "ramble": "reamble", "Lost and Found": "Last and Found"}
    original = {}
    for question in questions:
        if question.prompt in replacements:
            original[question.id] = question.prompt
            question.prompt = replacements[question.prompt]
        if question.choices[0].text == "관절이 있는 다리":
            original[question.id] = question.prompt
            question.choices[0].text = "뼈가 있는 다리"
    db.session.commit()
    assert len(original) == 4
    assert correct_vocabulary() == 4
    assert correct_vocabulary() == 0
    for question in questions:
        if question.id in original:
            assert question.prompt == original[question.id]
    assert any(q.choices[0].text == "관절이 있는 다리" for q in questions)
