import assert from 'node:assert/strict';
import {test, after} from 'node:test';
import {renderAnswer} from '../app/static/study/answer_renderer.js';

class Element {
    constructor(tag) {
        this.tagName = tag; this.children = []; this.listeners = {}; this.dataset = {}; this.style = {};
        this.attributes = {}; this.textContent = ''; this.clientHeight = 100;
        this.classes = new Set();
        this.classList = {add: c => this.classes.add(c), toggle: (c, v) => v ? this.classes.add(c) : this.classes.delete(c)};
    }
    get scrollHeight() { return this.textContent.length; }
    setAttribute(k, v) { this.attributes[k] = v; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(event, fn, options) { this.listeners[event] = {fn, once: options?.once}; }
    fire(event) { const listener = this.listeners[event]; if (listener) { if (listener.once) delete this.listeners[event]; listener.fn(); } }
    focus() {}
}
globalThis.document = {createElement: tag => new Element(tag)};
globalThis.ResizeObserver = class { observe() {} disconnect() {} };
globalThis.requestAnimationFrame = fn => fn();
after(() => { delete globalThis.document; delete globalThis.ResizeObserver; delete globalThis.requestAnimationFrame; });

function mount(type, choices, answer) {
    const container = new Element('div'), nextButton = new Element('button');
    const changes = [], submits = [];
    const state = {locked: false};
    const controls = renderAnswer({question: {type, choices}, answer, container, nextButton,
        isLocked: () => state.locked,
        onChange: (...args) => changes.push(args), onSubmit: value => submits.push(value)});
    return {container, nextButton, changes, submits, state, controls};
}

test('both flashcard actions submit immediately and locked clicks do not resubmit', () => {
    for (const index of [1, 2]) {
        const view = mount('flashcard', ['meaning']);
        view.container.children[0].fire('click');
        assert.equal(view.container.children.length, 3);
        view.container.children[index].fire('click');
        assert.deepEqual(view.submits, [index === 1]);
        view.state.locked = true;
        view.container.children[index].fire('click');
        assert.equal(view.submits.length, 1);
    }
});

test('typing preserves focus by updating state without rebuilding the input', () => {
    const view = mount('meaning', []);
    const input = view.container.children[0].children[1];
    input.value = '뜻'; input.fire('input');
    assert.deepEqual(view.changes, [['뜻', false]]);
    assert.equal(view.nextButton.disabled, false);
    input.value = ' '; input.fire('input');
    assert.equal(view.nextButton.disabled, true);
});

test('sentence controls preserve indices for repeated words and require all words', () => {
    const view = mount('sentence', ['the', 'the', 'cat'], [1]);
    const [heading, tray, bank] = view.container.children[0].children;
    assert.equal(view.nextButton.disabled, true);
    assert.equal(bank.children[1].disabled, true);
    bank.children[0].fire('click');
    assert.deepEqual(view.changes[0], [[1, 0]]);
    tray.children[0].fire('click');
    assert.deepEqual(view.changes[1], [[]]);
    assert.equal(mount('sentence', ['a', 'b'], [1, 0]).nextButton.disabled, false);
});

test('long translation can be paged and corrected without changing the chosen answer', () => {
    const long = '긴 해석의 문장을 차례로 읽습니다. '.repeat(30);
    const view = mount('comprehension', [long, '다른 해석'], 0);
    const panel = view.container.children.at(-1);
    const [caption, body, navigation] = panel.children;
    const first = body.textContent;
    assert(first.length < long.length);
    navigation.children[2].fire('click');
    assert.notEqual(navigation.children[1].textContent, '1 / 1');
    view.controls.showText('정답 해석입니다.');
    assert.equal(body.textContent, '정답 해석입니다.');
    assert.equal(caption.textContent, '정답 해석');
    assert.deepEqual(view.changes, []);
    view.controls.destroy();
});
