import {apiRequest} from '../shared/api.js';
import {QUESTION_LABELS, quizUrl} from '../shared/study_modes.js';

const quizId = new URLSearchParams(window.location.search).get('id');
if (quizId) document.querySelector('#set-mistakes-link').href = `/mistakes.html?quiz=${encodeURIComponent(quizId)}`;
const loading = document.querySelector('#detail-loading');
const detail = document.querySelector('#detail-view');
const errorView = document.querySelector('#detail-error');
const shuffleToggle = document.querySelector('#shuffle-mode');
try { shuffleToggle.checked = localStorage.getItem('samsam.shuffle') === '1'; } catch {}
function updateShuffle() {
    document.querySelectorAll('.learning-mode-card').forEach(link => {
        const url = new URL(link.href, location.origin);
        if (url.pathname !== '/study.html') return;
        if (shuffleToggle.checked) url.searchParams.set('shuffle', '1');
        else url.searchParams.delete('shuffle');
        link.href = url.pathname + url.search;
    });
}
shuffleToggle.addEventListener('change', () => {
    try { localStorage.setItem('samsam.shuffle', shuffleToggle.checked ? '1' : '0'); } catch {}
    updateShuffle();
});

function fail(message) {
    loading.hidden = true;
    detail.hidden = true;
    errorView.hidden = false;
    document.querySelector('#detail-error-message').textContent = message;
}

async function loadDetail() {
    if (!quizId) return fail('선택한 퀴즈 정보가 없습니다.');
    try {
        const {quiz} = await apiRequest(`/api/quizzes/${encodeURIComponent(quizId)}`);
        const types = [...new Set(quiz.questions.map((question) => QUESTION_LABELS[question.type] || question.type))];
        document.querySelector('#detail-subject').textContent = quiz.subject;
        document.querySelector('#detail-title').textContent = quiz.title;
        document.querySelector('#detail-description').textContent = quiz.description || '설명이 없는 퀴즈입니다.';
        document.querySelector('#detail-count').textContent = `${quiz.questions.length}문항`;
        document.querySelector('#detail-types').textContent = types.join(' · ');
        document.querySelector('#standard-study-link').href = quizUrl(quiz.id, 'study');
        document.querySelector('#detail-match-link').href = quizUrl(quiz.id, 'match');
        for (const mode of ['meaning', 'article', 'sentence', 'comprehension']) {
            const link = document.querySelector(`#${mode}-study-link`);
            link.hidden = !(quiz.study_modes || []).includes(mode);
            link.href = quizUrl(quiz.id, 'study', mode);
        }
        const reader = document.querySelector('#article-reader-link');
        reader.hidden = !(quiz.study_modes || []).includes('comprehension');
        reader.href = `/article.html?id=${encodeURIComponent(quiz.id)}`;
        updateShuffle();
        loading.hidden = true;
        errorView.hidden = true;
        detail.hidden = false;
    } catch (error) {
        fail(error.message);
    }
}

loadDetail();
