import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.services.study_modes import article_passages, sentence_candidates


EXPECTED = {
    "wasps": (16, [3, 4], "his PhD thesis.”"),
    "digital-detox": (13, [3, 4], "so much fun."),
    "friendships": (7, [3], "the chance to try."),
    "new-start": (13, [4, 5], "ready as ever for work."),
    "endurance": (10, [3], "aged 47."),
}


def corpus():
    return json.loads((Path(__file__).parents[1] / "app/data/article_passages.json").read_text(encoding="utf-8"))


def test_complete_pdf_paragraphs_and_page_continuations():
    data = corpus()
    assert {g["key"] for g in data} == set(EXPECTED)
    assert sum(len(g["passages"]) for g in data) == 59
    for group in data:
        count, pages, ending = EXPECTED[group["key"]]
        passages = group["passages"]
        assert group["coverage"] == "complete_article_body"
        assert [p["number"] for p in passages] == list(range(1, count + 1))
        assert sorted({page for p in passages for page in p["pages"]}) == pages
        assert passages[-1]["text"].endswith(ending)
        assert all(p["text"] and p["translation"] and "pdf" in p["source"] for p in passages)
        assert all(any("가" <= c <= "힣" for c in p["translation"]) for p in passages)
        assert all("Glossary" not in p["text"] and "Comprehension check" not in p["text"] for p in passages)
    start = next(g for g in data if g["key"] == "new-start")["passages"][-1]
    assert start["pages"] == [4, 5]
    assert "She has just published a book, The Well-Lived Life:" in start["text"]
    friends = next(g for g in data if g["key"] == "friendships")["passages"]
    assert "we mainly settle wherever makes financial and practical sense" in friends[2]["text"]
    wasps = next(g for g in data if g["key"] == "wasps")["passages"]
    assert "70,000 are parasitic, which are stingless" in wasps[6]["text"]


def test_sentence_hints_have_translation_and_exact_masked_context_for_every_paragraph():
    for group in corpus():
        passages = {p["number"]: p for p in group["passages"]}
        candidates = sentence_candidates(list(passages.values()))
        assert {c["paragraph_number"] for c in candidates} == set(passages)
        for c in candidates:
            passage = passages[c["paragraph_number"]]
            assert passage["translation"] in c["prompt"]
            context = c["prompt"].split("원문 문맥\n", 1)[1]
            assert context.count("[배열할 문장]") == 1
            assert context.replace("[배열할 문장]", c["text"]) == passage["text"]
            assert c["text"] not in context
            assert c["source"] == passage["source"]


def test_sentence_quotes_and_attribution_stay_with_their_sentence():
    text = '“I was broken,” she says. “It really hurt.” Then she recovered.'
    items = sentence_candidates([dict(number=1, text=text, translation="그녀의 회복 과정", source="test")])
    assert [c["text"] for c in items] == ['“I was broken,” she says.', '“It really hurt.”', 'Then she recovered.']


def test_article_source_endpoint_returns_all_paragraphs(client):
    from app.seed import load_samples, seed_samples
    seed_samples(load_samples())
    for topic, (count, _, ending) in EXPECTED.items():
        key = "exam-vocabulary" if topic == "wasps" else f"exam-vocabulary-{topic}"
        quiz_id = str(uuid5(NAMESPACE_URL, f"samsam:erw-samples:{key}"))
        response = client.get(f"/api/quizzes/{quiz_id}/article-source")
        assert response.status_code == 200
        paragraphs = response.json["text"].split("\n\n")
        assert len(paragraphs) == count
        assert paragraphs == [p["text"] for p in article_passages(quiz_id)]
        assert response.json["text"].endswith(ending)
