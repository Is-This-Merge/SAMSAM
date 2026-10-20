from app.db import db
from app.models import QuizAttempt, User


def valid_quiz():
    return {
        "title": "세포 소기관 퀴즈",
        "subject": "생명과학",
        "description": "객관식 테스트",
        "questions": [
            {
                "prompt": "ATP를 주로 생성하는 소기관은?",
                "choices": ["핵", "미토콘드리아", "골지체", "리보솜"],
                "correct_index": 1,
                "explanation": "미토콘드리아는 세포 호흡을 담당한다.",
            }
        ],
    }


def test_create_and_get_quiz(client):
    created = client.post("/api/quizzes", json=valid_quiz())
    assert created.status_code == 201
    created_quiz = created.get_json()["quiz"]
    assert created_quiz["questions"][0]["correct_index"] == 1

    fetched = client.get(f"/api/quizzes/{created_quiz['id']}")
    assert fetched.status_code == 200
    fetched_quiz = fetched.get_json()["quiz"]
    assert fetched_quiz["title"] == "세포 소기관 퀴즈"
    assert "correct_index" not in fetched_quiz["questions"][0]

    editable = client.get(f"/api/quizzes/{created_quiz['id']}?edit=1").get_json()["quiz"]
    assert editable["questions"][0]["correct_index"] == 1

    listed = client.get("/api/quizzes?q=세포")
    assert listed.status_code == 200
    assert listed.get_json()["quizzes"][0]["question_count"] == 1


def test_public_quiz_preview_uses_real_questions(client):
    created = client.post("/api/quizzes", json=valid_quiz()).get_json()["quiz"]

    response = client.get("/api/quizzes/preview")

    assert response.status_code == 200
    preview = response.get_json()["quiz"]
    assert preview["id"] == created["id"]
    assert preview["question_count"] == len(created["questions"])
    assert len(preview["questions"]) == preview["question_count"]
    assert preview["questions"][0]["prompt"] == created["questions"][0]["prompt"]
    assert preview["questions"][0]["answer"] == valid_quiz()["questions"][0]["choices"][1]


def test_quiz_subject_filters_are_derived_from_public_data(client):
    client.post("/api/quizzes", json=valid_quiz())
    subject = valid_quiz()["subject"]

    listed = client.get("/api/quizzes").get_json()
    matching = client.get("/api/quizzes", query_string={"subject": subject}).get_json()
    missing = client.get("/api/quizzes", query_string={"subject": "없는과목"}).get_json()

    assert listed["subjects"] == [{"name": subject, "count": 1}]
    assert len(matching["quizzes"]) == 1
    assert missing["quizzes"] == []


def test_true_false_question_and_image_round_trip(client):
    payload = valid_quiz()
    payload["questions"] = [{
        "question_type": "true_false",
        "prompt": "테스트 문항",
        "choices": ["O", "X"],
        "correct_index": 0,
        "explanation": "테스트 해설",
        "image_data": "data:image/png;base64,iVBORw0KGgo=",
        "explanation_image_data": "data:image/png;base64,iVBORw0KGgo=",
    }]

    response = client.post("/api/quizzes", json=payload)

    assert response.status_code == 201
    question = response.get_json()["quiz"]["questions"][0]
    assert question["type"] == "true_false"
    assert question["choices"] == ["O", "X"]
    assert question["image_data"].startswith("data:image/png;base64,")
    assert question["explanation_image_data"].startswith("data:image/png;base64,")


def test_fill_blank_converts_answer_in_body_to_blank(client):
    payload = valid_quiz()
    payload["questions"] = [{
        "question_type": "fill_blank",
        "prompt": "대한민국의 수도는 서울이다.",
        "choices": ["서울"],
        "correct_index": 0,
    }]

    response = client.post("/api/quizzes", json=payload)

    assert response.status_code == 201
    assert response.get_json()["quiz"]["questions"][0]["prompt"] == "대한민국의 수도는 ___이다."


def test_subject_rejects_whitespace(client):
    payload = valid_quiz()
    payload["subject"] = "생명 과학"

    response = client.post("/api/quizzes", json=payload)

    assert response.status_code == 400
    assert "subject" in response.get_json()["fields"]


def test_grades_quiz(client):
    created = client.post("/api/quizzes", json=valid_quiz()).get_json()["quiz"]
    response = client.post(
        f"/api/quizzes/{created['id']}/grade",
        json={"answers": [1]},
    )
    assert response.status_code == 200
    result = response.get_json()
    assert result["score"] == 100
    assert result["results"][0]["correct"] is True
    assert result["attempt_id"]

    with client.application.app_context():
        attempt = db.session.get(QuizAttempt, result["attempt_id"])
        assert attempt is not None
        assert attempt.quiz_set_id == created["id"]
        assert attempt.answers == [1]
        assert attempt.correct_count == 1


def test_rejects_out_of_range_answer_without_saving_attempt(client):
    created = client.post("/api/quizzes", json=valid_quiz()).get_json()["quiz"]
    response = client.post(
        f"/api/quizzes/{created['id']}/grade",
        json={"answers": [99]},
    )

    assert response.status_code == 400
    with client.application.app_context():
        assert db.session.query(QuizAttempt).count() == 0


def test_rejects_invalid_quiz(client):
    response = client.post("/api/quizzes", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_rejects_missing_correct_choice(client):
    payload = valid_quiz()
    payload["questions"][0]["correct_index"] = -1
    response = client.post("/api/quizzes", json=payload)
    assert response.status_code == 400
    assert "questions.0.correct_index" in response.get_json()["fields"]


def test_requires_login_and_checks_quiz_ownership(client):
    created = client.post("/api/quizzes", json=valid_quiz()).get_json()["quiz"]
    with client.session_transaction() as session:
        session.clear()
    assert client.post("/api/quizzes", json=valid_quiz()).status_code == 401
    assert client.put(f"/api/quizzes/{created['id']}", json=valid_quiz()).status_code == 401

    with client.application.app_context():
        other = User(google_sub="other-google-user", email="other@example.com", display_name="다른 학생")
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    with client.session_transaction() as session:
        session["user_id"] = other_id
        session["csrf_token"] = "test-csrf-token"
    assert client.put(f"/api/quizzes/{created['id']}", json=valid_quiz()).status_code == 403
    assert client.delete(f"/api/quizzes/{created['id']}").status_code == 403


def test_update_and_delete_owned_quiz(client):
    created = client.post("/api/quizzes", json=valid_quiz()).get_json()["quiz"]
    payload = valid_quiz()
    payload["title"] = "수정된 퀴즈"
    updated = client.put(f"/api/quizzes/{created['id']}", json=payload)
    assert updated.status_code == 200
    assert updated.get_json()["quiz"]["title"] == "수정된 퀴즈"
    assert client.delete(f"/api/quizzes/{created['id']}").status_code == 204
    assert client.get(f"/api/quizzes/{created['id']}").status_code == 404


def test_inventory_requires_login(client):
    assert client.get("/inventory.html").status_code == 200
    with client.session_transaction() as session:
        session.clear()
    response = client.get("/inventory.html")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_private_quiz_can_be_shared_and_edited_by_collaborator(client):
    payload = valid_quiz()
    payload["visibility"] = "private"
    created = client.post("/api/quizzes", json=payload).get_json()["quiz"]

    with client.application.app_context():
        collaborator = User(
            google_sub="collaborator-google-user",
            email="collaborator@example.com",
            display_name="공동 편집자",
        )
        db.session.add(collaborator)
        db.session.commit()
        collaborator_id = collaborator.id

    shared = client.post(
        f"/api/quizzes/{created['id']}/collaborators",
        json={"email": "collaborator@example.com"},
    )
    assert shared.status_code == 201

    with client.session_transaction() as session:
        session["user_id"] = collaborator_id
    assert client.get(f"/api/quizzes/{created['id']}").status_code == 200
    editable = client.get(f"/api/quizzes/{created['id']}?edit=1").get_json()["quiz"]
    assert editable["questions"][0]["correct_index"] == 1

    payload["title"] = "함께 수정한 퀴즈"
    assert client.put(f"/api/quizzes/{created['id']}", json=payload).status_code == 200
    assert client.delete(f"/api/quizzes/{created['id']}").status_code == 403
    assert client.get("/api/quizzes?q=함께").get_json()["quizzes"] == []


def test_flashcard_and_fill_blank_are_created_and_graded(client):
    payload = {
        "title": "혼합 학습",
        "subject": "영어",
        "questions": [
            {
                "question_type": "flashcard",
                "prompt": "photosynthesis",
                "choices": ["광합성"],
                "correct_index": 0,
                "explanation": "",
            },
            {
                "question_type": "fill_blank",
                "prompt": "식물은 ___을 통해 에너지를 저장한다.",
                "choices": ["광합성"],
                "correct_index": 0,
                "explanation": "",
            },
        ],
    }
    created = client.post("/api/quizzes", json=payload)
    assert created.status_code == 201
    quiz = created.get_json()["quiz"]
    assert [question["type"] for question in quiz["questions"]] == ["flashcard", "fill_blank"]

    graded = client.post(
        f"/api/quizzes/{quiz['id']}/grade",
        json={"answers": [True, "  광합성  "]},
    )
    assert graded.status_code == 200
    assert graded.get_json()["score"] == 100

    match = client.get(f"/api/quizzes/{quiz['id']}/match")
    assert match.status_code == 200
    assert len(match.get_json()["pairs"]) == 2


def test_learning_stats_and_security_headers(client):
    created = client.post("/api/quizzes", json=valid_quiz()).get_json()["quiz"]
    client.post(f"/api/quizzes/{created['id']}/grade", json={"answers": [1]})
    response = client.get("/api/me/stats")
    assert response.status_code == 200
    assert response.get_json() == {
        "attempt_count": 1,
        "average_score": 100,
        "best_score": 100,
        "studied_quiz_count": 1,
    }
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_authenticated_mutation_requires_csrf_token(client):
    client.environ_base.pop("HTTP_X_CSRF_TOKEN", None)
    response = client.post("/api/quizzes", json=valid_quiz())
    assert response.status_code == 403
    assert response.get_json()["error"] == "invalid_csrf_token"
