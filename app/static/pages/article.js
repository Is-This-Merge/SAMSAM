import {apiRequest} from '../shared/api.js';
import {quizUrl} from '../shared/study_modes.js';

const id = new URLSearchParams(location.search).get('id');
const container = document.querySelector('#reader-passages');
const status = document.querySelector('#reader-status');
document.querySelector('#reader-mode').addEventListener('change', event => {
    container.dataset.mode = event.target.value;
});

async function load() {
    if (!id) { status.textContent = '학습 세트를 먼저 선택해 주세요.'; return; }
    document.querySelector('#reader-back').href = quizUrl(id);
    try {
        const data = await apiRequest(`/api/quizzes/${encodeURIComponent(id)}/article-source`);
        document.querySelector('#reader-title').textContent = data.title;
        document.querySelector('#reader-count').textContent = `${data.passages.length}개 문단 · 전체 본문`;
        document.querySelector('#reader-source').textContent = data.source ? `출처: ${data.source}` : '';
        container.replaceChildren(...data.passages.map(passage => {
            const card = document.createElement('article');
            card.className = 'reader-paragraph';
            const heading = document.createElement('h2');
            heading.textContent = `문단 ${passage.number}`;
            const columns = document.createElement('div');
            columns.className = 'reader-columns';
            for (const [kind, label, text, lang] of [
                ['original', 'ORIGINAL', passage.text, 'en'],
                ['translation', '해석', passage.translation, 'ko'],
            ]) {
                const section = document.createElement('section');
                section.className = `reader-${kind}`;
                const title = document.createElement('h3');
                title.textContent = label;
                const body = document.createElement('p');
                body.lang = lang;
                body.textContent = text || '등록된 해석이 없습니다.';
                section.append(title, body);
                columns.append(section);
            }
            card.append(heading, columns);
            return card;
        }));
        status.hidden = data.passages.length > 0;
        status.textContent = '이 세트에는 등록된 기사 본문이 없습니다.';
    } catch (error) { status.textContent = error.message; }
}
load();
