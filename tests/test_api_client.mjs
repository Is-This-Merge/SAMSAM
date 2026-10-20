import assert from 'node:assert/strict';
import {test, after} from 'node:test';
import {apiRequest} from '../app/static/shared/api.js';

const originalFetch = globalThis.fetch;
after(() => { globalThis.fetch = originalFetch; delete globalThis.document; });

test('JSON writes carry CSRF and preserve the payload; reads carry no CSRF', async () => {
    globalThis.document = {querySelector: () => ({content: 'test-token'})};
    let received;
    globalThis.fetch = async (url, options) => { received = options; return new Response('{"saved":true}'); };
    assert.deepEqual(await apiRequest('/test', {method: 'POST', json: {answer: false}}), {saved: true});
    assert.equal(received.headers.get('X-CSRF-Token'), 'test-token');
    assert.equal(received.headers.get('Content-Type'), 'application/json');
    assert.equal(received.body, '{"answer":false}');
    await apiRequest('/test');
    assert.equal(received.headers.has('X-CSRF-Token'), false);
});

test('validation and non-JSON failures become readable errors', async () => {
    globalThis.fetch = async () => new Response('{"fields":{"title":"제목을 입력하세요"}}', {status: 400});
    await assert.rejects(apiRequest('/test'), error => error.status === 400 && error.message === '제목을 입력하세요');
    globalThis.fetch = async () => new Response('<html>Bad Gateway</html>', {status: 502});
    await assert.rejects(apiRequest('/test'), error => error.status === 502 && !error.message.includes('<html>'));
    globalThis.fetch = async () => new Response(null, {status: 204});
    assert.equal(await apiRequest('/test', {method: 'DELETE'}), null);
});

test('abort stays distinguishable from an offline request', async () => {
    const abort = new DOMException('aborted', 'AbortError');
    globalThis.fetch = async () => { throw abort; };
    await assert.rejects(apiRequest('/test'), error => error === abort);
    globalThis.fetch = async () => { throw new TypeError('fetch failed'); };
    await assert.rejects(apiRequest('/test'), /연결/);
});
