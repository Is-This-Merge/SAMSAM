"""Explicit, repeatable import of the bundled ERW sample quizzes."""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import click
from flask.cli import with_appcontext

from .db import db
from .models import QuizSet
from .services.quiz_content import replace_questions
from .services.quiz_validation import validate_quiz


def load_samples():
    samples = load_vocabulary_samples()
    keys = set()
    for sample in samples:
        key = sample["key"]
        if key in keys:
            raise ValueError(f"Duplicate sample key: {key}")
        keys.add(key)
        errors = validate_quiz(sample)
        if errors:
            raise ValueError(f"Invalid sample {key}: {errors}")
    return samples


def load_vocabulary_samples():
    path = Path(__file__).parent / "data" / "erw_vocabulary.json"
    vocabulary = json.loads(path.read_text(encoding="utf-8"))
    samples = []
    for number, group in enumerate(vocabulary["groups"], start=1):
        questions = []
        for entry in group["entries"]:
            explanation = f"{entry['term']}: {entry['meaning']}. 출처: {vocabulary['source']}, PDF {entry['page']}쪽."
            if entry.get("note"):
                explanation += " " + entry["note"]
            questions.append(dict(type="flashcard", prompt=entry["term"],
                                  choices=[entry["meaning"]], correct_index=0, explanation=explanation))
        samples.append(dict(
            key="exam-vocabulary" if group["key"] == "wasps" else f"exam-vocabulary-{group['key']}",
            title=f"{number:02d}. {group['title']} · 2026 ERW",
            subject="ERW", visibility="public",
            description=f"단어장 전체 어휘 · {len(questions)}개 단어와 표현. 출처: {vocabulary['source']}. 연습용 중복 항목은 제외했습니다.",
            questions=questions,
        ))
    return samples


def retire_legacy_samples():
    from .services.article_repository import TOPICS
    deleted = 0
    try:
        for topic in TOPICS:
            quiz_id = str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{topic}"))
            quiz = db.session.get(QuizSet, quiz_id)
            if quiz is not None and quiz.owner_id is None:
                db.session.delete(quiz)
                deleted += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return deleted


def correct_vocabulary():
    """Apply approved errata to bundled sets without replacing question IDs."""
    aliases = {"diarrhoea": "diarrhea", "reamble": "ramble",
               "last and found": "Lost and Found", "lost and found": "Lost and Found"}
    changed = 0
    try:
        for sample in load_vocabulary_samples():
            quiz_id = str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{sample['key']}"))
            quiz = db.session.get(QuizSet, quiz_id)
            if quiz is None or quiz.owner_id is not None:
                continue
            canonical = {q["prompt"]: q for q in sample["questions"]}
            for question in quiz.questions:
                term = aliases.get(question.prompt.lower(), question.prompt)
                payload = canonical.get(term)
                if not payload:
                    continue
                meaning = any(c.text in ("뼈 있는 다리", "뼈가 있는 다리") for c in question.choices)
                if term != question.prompt or meaning:
                    question.prompt = term
                    question.explanation = payload["explanation"]
                    for choice in question.choices:
                        if choice.is_correct:
                            choice.text = payload["choices"][0]
                    changed += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return changed


def seed_samples(samples, *, expand_vocabulary=False):
    created = skipped = questions = 0
    try:
        for sample in samples:
            quiz_id = str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{sample['key']}"))
            existing = db.session.get(QuizSet, quiz_id)
            if existing is not None:
                if expand_vocabulary and sample["key"].startswith("exam-vocabulary"):
                    if existing.owner_id is not None:
                        raise ValueError("Owned vocabulary sets cannot be expanded by the sample importer")
                    prompts = {q.prompt for q in existing.questions}
                    missing = [q for q in sample["questions"] if q["prompt"] not in prompts]
                    replace_questions(existing, missing)
                    questions += len(missing)
                    existing.title = sample["title"]
                    existing.description = sample["description"]
                skipped += 1
                continue
            quiz = QuizSet(
                id=quiz_id,
                title=sample["title"],
                subject=sample["subject"],
                description=sample["description"],
                visibility="public",
            )
            replace_questions(quiz, sample["questions"])
            db.session.add(quiz)
            created += 1
            questions += len(sample["questions"])
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return created, skipped, questions


@click.command("seed-samples")
@click.option("--dry-run", is_flag=True, help="Validate samples without accessing the database.")
@click.option("--expand-vocabulary", is_flag=True, help="Append missing PDF vocabulary to existing sample sets.")
@click.option("--retire-legacy", is_flag=True, help="Remove the five original 11-question sample sets and their attempts.")
@click.option("--correct-vocabulary", "apply_corrections", is_flag=True, help="Apply vocabulary errata while preserving question IDs.")
@with_appcontext
def seed_samples_command(dry_run, expand_vocabulary, retire_legacy, apply_corrections):
    """Add ERW samples; existing sample IDs and user content are preserved."""
    samples = load_samples()
    if dry_run:
        click.echo(f"Valid: {len(samples)} sets, {sum(len(s['questions']) for s in samples)} questions")
        return
    created, skipped, questions = seed_samples(samples, expand_vocabulary=expand_vocabulary)
    click.echo(f"Created: {created} sets, {questions} questions; skipped: {skipped} existing sets")
    if retire_legacy:
        click.echo(f"Removed legacy sets: {retire_legacy_samples()}")
    if apply_corrections:
        click.echo(f"Corrected vocabulary: {correct_vocabulary()}")
