from app.services.cloze import generate_cloze
from app.services.grading import check_answer


def test_mistakes_page_is_available_without_login(client):
    with client.session_transaction() as session:
        session.clear()
    response = client.get('/mistakes.html')
    assert response.status_code == 200
    assert 'mistakes.js' in response.text
    assert '로그인 없이' in response.text


def test_review_identity_is_independent_of_shuffled_choices():
    first = dict(type='comprehension', prompt='Text', choices=['no', 'yes'], answer='yes', correct_index=1, explanation='')
    second = dict(first, choices=['yes', 'no'], correct_index=0)
    assert check_answer(first, 0)['review_id'] == check_answer(second, 1)['review_id']
    second['prompt'] = 'Different text'
    assert check_answer(first, 0)['review_id'] != check_answer(second, 1)['review_id']


def test_random_blanks_use_source_position_not_other_blanks_or_display_number():
    options = dict(text='one two one four five six seven eight nine ten', chunk_words=0, blank_count=4)
    seen = {}
    changed_prompt_same_identity = False
    for seed in range(20):
        for question in generate_cloze(options, str(seed)):
            identity = check_answer(question, 0)['review_id']
            if question['review_key'] in seen:
                old_id, old_prompt = seen[question['review_key']]
                assert identity == old_id
                changed_prompt_same_identity |= old_prompt != question['prompt']
            seen[question['review_key']] = identity, question['prompt']
    assert len(seen) == 10
    assert len({value[0] for value in seen.values()}) == 10
    assert changed_prompt_same_identity
