import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';

const code = readFileSync(new URL('../app/static/study/keyboard.js', import.meta.url), 'utf8');
const {handleStudyKey} = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);

function setup() {
    let next = 0;
    const chosen = [];
    const state = {active: true, busy: false, checked: false,
        nextButton: {disabled: false, click() { next++; }},
        options: Array.from({length: 4}, (_, i) => ({disabled: false, click() { chosen.push(i); }}))};
    function press(key, overrides = {}) {
        const event = {key, preventDefault() { this.prevented = true; }, ...overrides};
        handleStudyKey(event, state);
        return event;
    }
    return {state, press, chosen, next: () => next};
}

test('Enter advances once after feedback and prevents native duplicate activation', () => {
    const t = setup(); t.state.checked = true;
    assert.equal(t.press('Enter').prevented, true);
    assert.equal(t.next(), 1);
    assert.equal(t.press('Enter', {repeat: true}).prevented, true);
    assert.equal(t.next(), 1);
});
test('number keys select matching choices but do not submit', () => {
    const t = setup();
    for (const key of ['1', '2', '4', '5', '0']) t.press(key);
    assert.deepEqual(t.chosen, [0, 1, 3]);
    assert.equal(t.next(), 0);
    t.state.checked = true; t.press('3');
    assert.deepEqual(t.chosen, [0, 1, 3]);
});
test('typing, Korean composition, busy state and hidden study do not trigger shortcuts', () => {
    const t = setup();
    const input = {matches: () => true};
    t.press('2', {target: input});
    t.press('Enter', {target: input, isComposing: true});
    t.press('Enter', {keyCode: 229});
    t.press('1', {ctrlKey: true});
    t.state.busy = true; t.press('Enter'); t.press('1');
    t.state.busy = false; t.state.active = false; t.press('Enter');
    assert.equal(t.next(), 0); assert.deepEqual(t.chosen, []);
    t.state.active = true;
    assert.equal(t.press('Enter', {target: input}).prevented, true);
    assert.equal(t.next(), 1);
    t.state.nextButton.disabled = true; t.press('Enter');
    assert.equal(t.next(), 1);
});
