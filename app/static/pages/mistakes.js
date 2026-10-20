import {readMistakes, sortedMistakes, clearMistakes, STORAGE_KEY} from '../study/mistake_store.js';
import {STUDY_LABELS, quizUrl} from '../shared/study_modes.js';
import {REVIEW_SELECTION_KEY} from '../study/mistake_review.js';

const setFilter = document.querySelector('#mistake-set');
const modeFilter = document.querySelector('#mistake-mode');
const search = document.querySelector('#mistake-search');
const list = document.querySelector('#mistake-list');
const empty = document.querySelector('#mistake-empty');
const error = document.querySelector('#mistake-error');
let records = [], page = 0;
const pageSize = 20;
let selectedSet = new URLSearchParams(location.search).get('quiz') || '';
function matches() {
    return sortedMistakes(records, {quizId: setFilter.value, mode: modeFilter.value, search: search.value});
}
function startReview(items) {
    if (!items.length) return;
    try {
        sessionStorage.setItem(REVIEW_SELECTION_KEY, JSON.stringify(items.map(item => item.id)));
        location.href = '/study.html?review=1';
    } catch {
        error.hidden = false;
        error.textContent = '테스트를 준비하지 못했어요. 브라우저 저장 공간 설정을 확인해 주세요.';
    }
}
document.querySelector('#mistake-test').addEventListener('click', () => startReview(matches()));

function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function card(item, rank) {
    const article = element('article', 'mistake-card');
    const top = element('div', 'mistake-card-top');
    top.append(element('span', 'mistake-rank', `#${rank}`), element('strong', 'mistake-count', `오답 ${item.count}회`),
        element('span', 'mistake-mode', STUDY_LABELS[item.mode] || item.mode));
    const title = element('p', 'mistake-set-title', item.quizTitle);
    const prompt = element('p', 'mistake-prompt', item.prompt);
    if (item.blankNumber) top.append(element('span', 'mistake-mode', `빈칸 ⟦${item.blankNumber}⟧`));
    const detail = element('details', 'mistake-detail');
    detail.append(element('summary', '', '문제 전체와 답 확인'));
    const full = element('p', 'mistake-full', item.prompt);
    detail.append(full, element('p', 'mistake-wrong', `최근 오답: ${item.selected}`),
        element('p', 'mistake-answer', `정답: ${item.answer}`));
    if (item.source) detail.append(element('small', 'mistake-source', item.source));
    const bottom = element('div', 'mistake-card-bottom');
    const time = element('time', '', new Date(item.lastWrong).toLocaleString('ko-KR'));
    time.dateTime = new Date(item.lastWrong).toISOString();
    const link = element('a', 'back-link', '이 세트 다시 학습 ↗'); link.href = quizUrl(item.quizId, 'study', item.mode);
    const test = element('button', 'button button-secondary', '이 문제 테스트');
    test.type = 'button';
    test.addEventListener('click', () => startReview([item]));
    bottom.append(time, test, link); article.append(top, title, prompt, detail, bottom);
    return article;
}

function render() {
    const matches = sortedMistakes(records, {quizId: setFilter.value, mode: modeFilter.value, search: search.value});
    document.querySelector('#mistake-test').disabled = !matches.length;
    document.querySelector('#mistake-test').textContent = `현재 목록 ${matches.length}문제 테스트`;
    const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
    page = Math.min(page, pageCount - 1);
    list.replaceChildren(...matches.slice(page * pageSize, (page + 1) * pageSize).map((item, i) => card(item, page * pageSize + i + 1)));
    document.querySelector('#mistake-summary').textContent = `${matches.length}문제 · 누적 오답 ${matches.reduce((sum, item) => sum + item.count, 0)}회`;
    empty.hidden = matches.length !== 0 || !error.hidden;
    empty.querySelector('h2').textContent = records.length ? '조건에 맞는 오답이 없어요' : '아직 기록된 오답이 없어요';
    empty.querySelector('p').textContent = records.length ? '검색어나 필터를 바꿔 보세요.' : '지금부터 틀린 문제가 기록됩니다. 기존 완료 기록에서는 과거 오답을 복원할 수 없어요.';
    document.querySelector('.mistake-pagination').hidden = matches.length <= pageSize;
    document.querySelector('#mistake-page').textContent = `${page + 1} / ${pageCount}`;
    document.querySelector('#mistake-prev').disabled = page === 0;
    document.querySelector('#mistake-next').disabled = page >= pageCount - 1;
    document.querySelector('#mistake-clear').disabled = !records.length && error.hidden;
}

function load() {
    try {
        records = readMistakes(); error.hidden = true;
        const sets = new Map(records.map(item => [item.quizId, item.quizTitle]));
        if (selectedSet && !sets.has(selectedSet)) sets.set(selectedSet, '선택한 세트 (기록 없음)');
        setFilter.replaceChildren(new Option('전체 세트', ''), ...[...sets].map(([id, title]) => new Option(title, id)));
        setFilter.value = selectedSet;
    } catch {
        records = []; error.hidden = false;
        error.textContent = '브라우저의 오답 기록을 읽지 못했어요. 저장 공간 설정을 확인해 주세요. 손상된 기록이라면 아래 초기화 버튼으로 지울 수 있습니다.';
    }
    render();
}

modeFilter.append(...Object.entries(STUDY_LABELS).map(([mode, name]) => new Option(name, mode)));
[setFilter, modeFilter].forEach(select => select.addEventListener('change', () => { selectedSet = setFilter.value; page = 0; render(); }));
search.addEventListener('input', () => { page = 0; render(); });
document.querySelector('#mistake-reset-filters').addEventListener('click', () => {
    selectedSet = ''; setFilter.value = ''; modeFilter.value = ''; search.value = ''; page = 0; render();
});
document.querySelector('#mistake-prev').addEventListener('click', () => { page--; render(); });
document.querySelector('#mistake-next').addEventListener('click', () => { page++; render(); });
document.querySelector('#mistake-clear').addEventListener('click', () => {
    if (!confirm('모든 세트의 오답 횟수와 답안 기록을 이 브라우저에서 삭제할까요? 삭제한 기록은 복구할 수 없습니다.')) return;
    try { clearMistakes(); page = 0; load(); }
    catch { error.hidden = false; error.textContent = '기록을 지우지 못했어요. 브라우저 저장 공간 설정을 확인해 주세요.'; }
});
window.addEventListener('storage', event => { if (event.key === STORAGE_KEY || event.key === null) load(); });
load();
