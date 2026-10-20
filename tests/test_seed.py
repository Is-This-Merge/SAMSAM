from sqlalchemy import func, select

from app.db import db
from app.models import Choice, Question, QuizSet
from app.seed import load_samples
from app.seed import seed_samples, load_vocabulary_samples
from app.models import QuizAttempt


def test_seed_is_repeatable_and_preserves_existing_content(client):
    app = client.application
    runner = app.test_cli_runner()
    with app.app_context():
        existing = QuizSet(title="Existing quiz", subject="ERW", description="Keep me")
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id
    result = runner.invoke(args=["seed-samples"])
    assert result.exit_code == 0, result.output
    assert "Created: 5 sets, 255 questions" in result.output
    with app.app_context():
        sample = db.session.scalar(select(QuizSet).where(QuizSet.id != existing_id))
        sample.description = "Keep sample edits too"
        sample_id = sample.id
        db.session.commit()
    result = runner.invoke(args=["seed-samples"])
    assert result.exit_code == 0, result.output
    assert "skipped: 5" in result.output
    with app.app_context():
        assert db.session.scalar(select(func.count(QuizSet.id))) == 6
        assert db.session.scalar(select(func.count(Question.id))) == 255
        assert db.session.get(QuizSet, existing_id).description == "Keep me"
        assert db.session.get(QuizSet, sample_id).description == "Keep sample edits too"
        for question in db.session.scalars(select(Question)):
            assert sum(c.is_correct for c in question.choices) == 1
    response = client.get("/api/quizzes?subject=ERW")
    assert response.status_code == 200
    assert len(response.json["quizzes"]) == 6


def test_dry_run_does_not_insert(client):
    result = client.application.test_cli_runner().invoke(args=["seed-samples", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "5 sets, 255 questions" in result.output
    with client.application.app_context():
        assert db.session.scalar(select(func.count(QuizSet.id))) == 0
        assert db.session.scalar(select(func.count(Choice.id))) == 0
    samples = load_samples()
    assert {q["type"] for s in samples for q in s["questions"]} == {
        "flashcard"
    }


def test_expand_vocabulary_preserves_ids_attempts_and_existing_edits(client):
    import copy
    original = copy.deepcopy(load_vocabulary_samples()[0])
    original["questions"] = original["questions"][:20]
    seed_samples([original])
    quiz = db.session.scalar(select(QuizSet))
    original_ids = [q.id for q in quiz.questions]
    quiz.questions[0].explanation = "Preserve my explanation"
    attempt = QuizAttempt(quiz_set_id=quiz.id, answers=[True] * 20, score=100, correct_count=20, total_count=20)
    db.session.add(attempt)
    db.session.commit()
    attempt_id = attempt.id
    runner = client.application.test_cli_runner()
    result = runner.invoke(args=["seed-samples", "--expand-vocabulary"])
    assert result.exit_code == 0, result.output
    assert len(quiz.questions) == 50
    assert [q.id for q in quiz.questions[:20]] == original_ids
    assert quiz.questions[0].explanation == "Preserve my explanation"
    assert db.session.get(QuizAttempt, attempt_id).total_count == 20
    assert [q.position for q in quiz.questions] == list(range(50))
    result = runner.invoke(args=["seed-samples", "--expand-vocabulary"])
    assert result.exit_code == 0, result.output
    assert db.session.scalar(select(func.count(Question.id))) == 255


def test_full_pdf_vocabulary_coverage():
    import json
    from pathlib import Path
    data = json.loads(Path("app/data/erw_vocabulary.json").read_text(encoding="utf-8"))
    assert [len(g["entries"]) for g in data["groups"]] == [50, 69, 49, 37, 50]
    samples = load_vocabulary_samples()
    assert sum(len(s["questions"]) for s in samples) == 255
    for group, sample in zip(data["groups"], samples):
        assert len({e["term"] for e in group["entries"]}) == len(group["entries"])
        assert {q["prompt"] for q in sample["questions"]} == {e["term"] for e in group["entries"]}
        assert all(e["meaning"] and 2 <= e["page"] <= 7 for e in group["entries"])


def test_retire_only_known_legacy_sets(client):
    from uuid import NAMESPACE_URL, uuid5
    from app.seed import retire_legacy_samples
    from app.services.quiz_content import replace_questions
    seed_samples(load_samples())
    legacy = QuizSet(id=str(uuid5(NAMESPACE_URL, "samsam:erw-samples:wasps")), title="Old sample", subject="ERW")
    unrelated = QuizSet(title="User's 11 questions", subject="ERW")
    payload = [dict(prompt="Word", type="flashcard", choices=["answer"])]
    for quiz in [legacy, unrelated]:
        replace_questions(quiz, payload * 11)
        db.session.add(quiz)
    db.session.commit()
    legacy_id, unrelated_id = legacy.id, unrelated.id
    db.session.add(QuizAttempt(quiz_set_id=legacy.id, answers=[True] * 11, score=100, correct_count=11, total_count=11))
    db.session.commit()
    assert retire_legacy_samples() == 1
    assert db.session.get(QuizSet, legacy_id) is None
    assert db.session.get(QuizSet, unrelated_id) is not None
    assert db.session.scalar(select(func.count(QuizSet.id))) == 6
    assert db.session.scalar(select(func.count(QuizAttempt.id))) == 0
    assert retire_legacy_samples() == 0
