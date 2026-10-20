import {test} from 'node:test';
import assert from 'node:assert/strict';
import {STORAGE_KEY, readMistakes, recordMistake, sortedMistakes, clearMistakes} from '../app/static/study/mistake_store.js';

function memory() {
    const data = new Map();
    return {getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, v), removeItem: k => data.delete(k)};
}
function attempt(id = 'a', correct = false) {
    return {quiz: {id: 'quiz', title: '단어 세트'}, mode: 'meaning', question: {type: 'meaning', prompt: id, choices: []},
        result: {review_id: id, correct, correct_answer: '정답', selected_answer: '오답'}};
}
test('mistakes persist across reads and rounds; successful answers never erase counts', () => {
    const store = memory();
    recordMistake(attempt(), store, 10); recordMistake(attempt(), store, 20);
    recordMistake(attempt('a', true), store, 30);
    assert.equal(readMistakes(store).length, 1);
    assert.equal(readMistakes(store)[0].count, 2);
    assert.equal(readMistakes(store)[0].lastWrong, 20);
    recordMistake(attempt('b', true), store, 40);
    assert.equal(readMistakes(store).length, 1);
});
test('descending count, then recency; filters and search do not mutate stored records', () => {
    const store = memory();
    recordMistake(attempt('a'), store, 10); recordMistake(attempt('a'), store, 20);
    recordMistake(attempt('b'), store, 30); recordMistake(attempt('c'), store, 40);
    const records = readMistakes(store);
    assert.deepEqual(sortedMistakes(records).map(r => r.prompt), ['a', 'c', 'b']);
    assert.deepEqual(records.map(r => r.prompt), ['a', 'b', 'c']);
    assert.equal(sortedMistakes(records, {quizId: 'other'}).length, 0);
    assert.equal(sortedMistakes(records, {mode: 'article'}).length, 0);
    assert.equal(sortedMistakes(records, {search: ' A '})[0].prompt, 'a');
});
test('shuffled choices keep the same identity and store selected answer text', () => {
    const store = memory(); const event = attempt();
    event.mode = 'article'; event.question = {type: 'article', prompt: '___ text', choices: ['wrong', 'right'], blank_number: 1};
    event.result.selected_answer = 0;
    recordMistake(event, store);
    event.question.choices.reverse(); event.result.selected_answer = 1;
    recordMistake(event, store);
    assert.equal(readMistakes(store)[0].count, 2);
    assert.equal(readMistakes(store)[0].selected, 'wrong');
    event.mode = 'standard'; recordMistake(event, store);
    assert.equal(readMistakes(store).length, 2);
});
test('flashcard review counts; corruption and quota failures remain visible; reset is scoped', () => {
    const store = memory(); const event = attempt(); event.result.selected_answer = false;
    recordMistake(event, store);
    assert.equal(readMistakes(store)[0].selected, '다시 볼래요');
    store.setItem('other', 'keep'); clearMistakes(store);
    assert.deepEqual(readMistakes(store), []); assert.equal(store.getItem('other'), 'keep');
    store.setItem(STORAGE_KEY, 'broken');
    assert.throws(() => recordMistake(event, store));
    assert.equal(store.getItem(STORAGE_KEY), 'broken');
    assert.throws(() => recordMistake(event, {getItem: () => null, setItem: () => {throw new Error('quota');}}));
});
