def test_primary_pages_use_shared_layout(client):
    for path in ["/", "/create.html", "/inventory.html", "/mypage.html", "/info.html", "/quiz.html", "/study.html", "/match.html"]:
        response = client.get(path)
        assert response.status_code == 200
        assert b'class="site-header"' in response.data
        assert b'class="site-footer"' in response.data


def test_legacy_pages_redirect_to_current_experience(client):
    for path in ["/categorysearch.html", "/answer.html", "/false.html", "/next_quiz.html"]:
        assert client.get(path).status_code == 302


def test_create_page_has_three_step_wizard_and_new_question_inputs(client):
    response = client.get("/create.html")

    assert response.status_code == 200
    assert b'data-step="1"' in response.data
    assert b'data-step="2"' in response.data
    assert b'data-step="3"' in response.data
    assert b'value="true_false"' in response.data
    assert b'question-image-input' in response.data
    assert b'explanation-image-input' in response.data


def test_logout_is_available_on_profile_not_global_header(client):
    home = client.get("/")
    profile = client.get("/mypage.html")

    assert b'profile-logout' not in home.data
    assert b'profile-logout' in profile.data
    assert b'profile-stats' in profile.data
    assert b'stats-grid' not in client.get("/inventory.html").data
