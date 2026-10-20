import {test} from 'node:test';
import assert from 'node:assert/strict';
import {reviewQuestion, checkReviewAnswer} from '../app/static/study/mistake_review.js';
import {recordMistake, readMistakes, recordReviewMistake} from '../app/static/study/mistake_store.js';
import {MasteryQueue} from '../app/static/study/mastery_queue.js';

const item = {id: 'saved', type: 'meaning', prompt: 'walk', answer: '걷다, 산책하다 (걸어서)', source: ''};
test('meaning and basic cards accept registered variants without erasing the original question', () => {
    for (const type of ['meaning', 'flashcard']) {
        const q = reviewQuestion({...item, type});
        assert.equal(q.type, 'meaning');
        assert.equal(checkReviewAnswer(q, '산책하다').correct, true);
        assert.equal(checkReviewAnswer(q, ' 걷 다 ').correct, true);
        assert.equal(checkReviewAnswer(q, '').correct, false);
        assert.equal(checkReviewAnswer(q, '달리다').correct, false);
        assert.equal(q.prompt, 'walk');
    }
});
test('saved article choices are shuffled and checked by answer, with the original blank target', () => {
    const q = reviewQuestion({...item, type: 'article', blankNumber: 3, answer: 'walk',
        question: {choices: ['walk', 'run', 'fly'], blank_count: 4}}, () => 0);
    assert.equal(q.blank_number, 3);
    assert.equal(q.blank_count, 4);
    assert.deepEqual(q.choices, ['run', 'fly', 'walk']);
    assert.equal(checkReviewAnswer(q, 2).correct, true);
    assert.equal(checkReviewAnswer(q, 0).selected_text, 'run');
    assert.equal(checkReviewAnswer(q, 0).correct, false);
});
test('legacy records remain playable, including repeated words in sentence arrangement', () => {
    const blank = reviewQuestion({...item, type: 'article', answer: 'walk', blankNumber: 2});
    assert.equal(blank.type, 'fill_blank');
    assert.match(blank.prompt, /⟦2⟧/u);
    assert.equal(checkReviewAnswer(blank, ' WALK ').correct, true);
    const translation = reviewQuestion({...item, type: 'comprehension'});
    assert.equal(translation.type, 'flashcard');
    assert.equal(checkReviewAnswer(translation, false).correct, false);
    const sentence = reviewQuestion({...item, type: 'sentence', answer: 'go go now'}, () => 0);
    assert.equal(checkReviewAnswer(sentence, [2, 0, 1]).correct, true);
    assert.equal(checkReviewAnswer(sentence, [0, 0, 1]).correct, false);
});
test('review mistakes update the original record and mastery repeats only missed items', () => {
    const data = new Map();
    const store = {getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value)};
    recordMistake({quiz: {id: 'quiz', title: 'Set'}, mode: 'article',
        question: {type: 'article', prompt: '___', choices: ['walk', 'run'], blank_number: 1},
        result: {correct: false, review_id: 'stable', correct_answer: 'walk', selected_answer: 1}}, store, 1);
    const [original] = readMistakes(store);
    assert.deepEqual(original.question.choices, ['walk', 'run']);
    const queue = new MasteryQueue(2);
    queue.record(true); queue.advance();
    recordReviewMistake(original.id, 'run', store, 2);
    queue.record(false); queue.advance();
    assert.equal(queue.current, 1);
    queue.record(true); queue.advance();
    assert.equal(queue.complete, true);
    const [updated] = readMistakes(store);
    assert.equal(updated.id, original.id);
    assert.equal(updated.mode, 'article');
    assert.equal(updated.count, 2);
    assert.equal(updated.selected, 'run');
    assert.equal(readMistakes(store).length, 1);
    assert.throws(() => recordReviewMistake('deleted', 'x', store));
});
