import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';

const code = readFileSync(new URL('../app/static/study/mastery_queue.js', import.meta.url), 'utf8');
const {MasteryQueue} = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);

test('only wrong questions return, across as many passes as needed', () => {
    const q = new MasteryQueue(4);
    const visited = [];
    for (const correct of [true, false, true, false, true, false, true]) {
        visited.push(q.current);
        q.record(correct);
        q.advance();
    }
    assert.deepEqual(visited, [0, 1, 2, 3, 1, 3, 3]);
    assert.equal(q.round, 3);
    assert.equal(q.responses, 7);
    assert.equal(q.complete, true);
    assert.equal(q.current, null);
    assert.equal(q.mastered.size, 4);
});
test('all correct finishes once; all wrong repeats the entire pending set', () => {
    const q = new MasteryQueue(2);
    q.record(false); q.advance(); q.record(false); q.advance();
    assert.equal(q.round, 2); assert.equal(q.mastered.size, 0);
    assert.equal(q.current, 0);
    q.record(true); q.advance(); q.record(true);
    assert.equal(q.complete, true); assert.equal(q.advance(), null);
    const fresh = new MasteryQueue(2);
    fresh.record(true); fresh.advance(); fresh.record(true); fresh.advance();
    assert.equal(fresh.round, 1); assert.equal(fresh.responses, 2);
});
test('fresh submissions are required and duplicate checks cannot corrupt the queue', () => {
    const q = new MasteryQueue(1);
    assert.throws(() => q.advance());
    q.record(false);
    assert.throws(() => q.record(true));
    assert.equal(q.responses, 1);
    q.advance();
    assert.throws(() => q.advance());
    q.record(true); q.advance();
    assert.equal(q.responses, 2);
    assert.throws(() => q.record(true));
});
test('correct answers keep their original positions for final server grading', () => {
    const q = new MasteryQueue(3);
    const answers = [];
    for (const [answer, correct] of [['right0', true], ['wrong1', false], ['right2', true], ['right1', true]]) {
        answers[q.current] = answer;
        q.record(correct);
        const next = q.advance();
        if (next !== null) answers[next] = undefined;
    }
    assert.deepEqual(answers, ['right0', 'right1', 'right2']);
    assert.equal(q.complete, true);
});

test('shuffle visits every original position and reshuffles only missed questions', () => {
    const q = new MasteryQueue(4, {shuffle: true, random: () => 0});
    assert.deepEqual(q.pending, [1, 2, 3, 0]);
    const first = [...q.pending];
    for (const index of first) {
        assert.equal(q.current, index);
        q.record(index === 2);
        q.advance();
    }
    assert.equal(q.round, 2);
    assert.deepEqual(q.pending, [3, 0, 1]);
    assert.deepEqual([...q.mastered], [2]);
    for (let i = 0; i < 3; i++) { q.record(true); q.advance(); }
    assert.equal(q.complete, true);
    assert.equal(q.current, null);
});
