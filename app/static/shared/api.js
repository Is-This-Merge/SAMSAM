/** JSON requests, CSRF and user-facing failures shared by every page. */
export async function apiRequest(url, {method = 'GET', json, signal, ...options} = {}) {
    const headers = new Headers(options.headers);
    headers.set('Accept', 'application/json');
    if (json !== undefined) headers.set('Content-Type', 'application/json');
    const csrf = globalThis.document?.querySelector('meta[name="csrf-token"]')?.content;
    if (csrf && !['GET', 'HEAD'].includes(method.toUpperCase())) headers.set('X-CSRF-Token', csrf);
    let response;
    try {
        response = await fetch(url, {...options, method, headers, signal,
            ...(json !== undefined ? {body: JSON.stringify(json)} : {})});
    } catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new Error('연결이 원활하지 않아요. 인터넷 연결을 확인하고 다시 시도해 주세요.');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        const messages = {401: '로그인 후 다시 시도해 주세요.', 403: '접근 권한이 없거나 세션이 만료되었어요.',
            404: '자료를 찾을 수 없어요. 삭제되었거나 접근 권한이 없을 수 있습니다.'};
        const error = new Error(data?.message || Object.values(data?.fields || {})[0] || messages[response.status] || '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.');
        error.status = response.status;
        throw error;
    }
    if (data === null && response.status !== 204) throw new Error('서버 응답을 읽지 못했어요. 다시 시도해 주세요.');
    return data;
}
