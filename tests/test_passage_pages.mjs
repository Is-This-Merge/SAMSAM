import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';

const code = readFileSync(new URL('../app/static/study/passage_pages.js', import.meta.url), 'utf8');
const {paginateText} = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);

test('long passages fit without dropping words, whitespace or the blank', () => {
    const text = 'An article with a ___ and several words.\nAnother sentence follows. '.repeat(10);
    const pages = paginateText(text, part => part.length <= 60);
    assert.ok(pages.length > 1);
    assert.equal(pages.join(''), text);
    assert.ok(pages.every(page => page.length <= 60));
});
test('unbroken text and short prompts remain fully readable', () => {
    const text = '아주긴공백없는문장'.repeat(30);
    const pages = paginateText(text, part => part.length <= 30);
    assert.equal(pages.join(''), text);
    assert.ok(pages.every(page => page.length <= 30));
    assert.deepEqual(paginateText('word', part => part.length <= 30), ['word']);
    assert.deepEqual(paginateText('', () => true), ['']);
});
