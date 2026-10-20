/** Browser-local mistake history. No account, token or server write is needed. */
export const STORAGE_KEY = 'samsam.mistakes.v1';

function storage() { return globalThis.localStorage; }
export function readMistakes(store = storage()) {
    const raw = store.getItem(STORAGE_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (data.version !== 1 || !Array.isArray(data.items) || !data.items.every(item =>
        typeof item.id === 'string' && typeof item.quizId === 'string' && typeof item.quizTitle === 'string' &&
        typeof item.mode === 'string' && typeof item.prompt === 'string' && typeof item.answer === 'string' &&
        typeof item.selected === 'string' && Number.isSafeInteger(item.count) && item.count > 0 &&
        Number.isFinite(item.lastWrong))) throw new Error('오답 기록의 형식을 읽을 수 없어요.');
    return data.items;
}

export function recordMistake({quiz, mode, question, result}, store = storage(), now = Date.now()) {
    if (result.correct) return;
    const items = readMistakes(store);
    const identity = result.review_id || [question.type, question.prompt, result.correct_answer, question.blank_number ?? null];
    const id = JSON.stringify([quiz.id, mode, identity]);
    const previous = items.find(item => item.id === id);
    const selected = result.selected_answer;
    const entry = {
        id, quizId: quiz.id, quizTitle: quiz.title, mode, type: question.type,
        prompt: question.prompt, answer: result.correct_answer,
        selected: typeof selected === 'number' ? question.choices[selected] :
            typeof selected === 'boolean' ? (selected ? '알고 있었어요' : '다시 볼래요') : String(selected ?? ''),
        source: question.source || '', blankNumber: question.blank_number || null,
        question: {type: question.type, choices: [...(question.choices || [])],
            blank_count: question.blank_count, image_data: question.image_data},
        count: (previous?.count || 0) + 1, lastWrong: now,
    };
    const index = items.findIndex(item => item.id === id);
    if (index < 0) items.push(entry); else items[index] = entry;
    store.setItem(STORAGE_KEY, JSON.stringify({version: 1, items}));
}

export function sortedMistakes(items, {quizId = '', mode = '', search = ''} = {}) {
    const term = search.trim().toLocaleLowerCase();
    return items.filter(item => (!quizId || item.quizId === quizId) && (!mode || item.mode === mode) &&
        (!term || `${item.quizTitle} ${item.prompt} ${item.answer}`.toLocaleLowerCase().includes(term)))
        .sort((a, b) => b.count - a.count || b.lastWrong - a.lastWrong || a.id.localeCompare(b.id));
}

export function clearMistakes(store = storage()) { store.removeItem(STORAGE_KEY); }

export function recordReviewMistake(id, selected, store = storage(), now = Date.now()) {
    const items = readMistakes(store);
    const item = items.find(record => record.id === id);
    if (!item) throw new Error('원래 오답 기록이 삭제되어 횟수를 저장하지 못했어요.');
    item.count++;
    item.selected = String(selected);
    item.lastWrong = now;
    store.setItem(STORAGE_KEY, JSON.stringify({version: 1, items}));
}
