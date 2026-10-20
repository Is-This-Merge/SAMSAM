import {apiRequest} from '../shared/api.js';
import {QUESTION_LABELS, quizUrl} from '../shared/study_modes.js';

const grid = document.querySelector('#quiz-grid');
const emptyState = document.querySelector('#empty-state');
const resultCount = document.querySelector('#result-count');
const searchForm = document.querySelector('#search-form');
const searchInput = document.querySelector('#search-input');
const filterContainer = document.querySelector('#subject-filters');
const preview = document.querySelector('#study-preview');
const previewCard = document.querySelector('#preview-card');
const previewTitle = document.querySelector('#preview-title');
const previewCounter = document.querySelector('#preview-counter');
const previewRefresh = document.querySelector('#preview-refresh');
const previewSubject = document.querySelector('#preview-subject');
const previewImage = document.querySelector('#preview-image');
const previewQuestion = document.querySelector('#preview-question');
const previewAnswer = document.querySelector('#preview-answer');
const previewHint = document.querySelector('#preview-hint');
const previewPrevious = document.querySelector('#preview-previous');
const previewNext = document.querySelector('#preview-next');
const previewProgress = document.querySelector('#preview-progress-bar');
const previewStart = document.querySelector('#preview-start');

let activeSubject = '';
let searchTimer;
let activeRequest;
let previewQuiz;
let previewIndex = 0;

function showSkeletons() {
    grid.replaceChildren(...Array.from({length: 6}, () => {
        const item = document.createElement('div');
        item.className = 'skeleton';
        item.setAttribute('aria-hidden', 'true');
        return item;
    }));
    grid.hidden = false;
    grid.setAttribute('aria-busy', 'true');
    emptyState.hidden = true;
}

function createQuizCard(quiz) {
    const card = document.createElement('a');
    card.className = 'quiz-card';
    card.href = quizUrl(quiz.id);
    const top = document.createElement('div');
    top.className = 'quiz-card-top';
    const subject = document.createElement('span');
    subject.className = 'quiz-subject';
    subject.textContent = quiz.subject;
    const count = document.createElement('span');
    count.className = 'quiz-count';
    const typeLabel = (quiz.question_types || ['multiple_choice']).map((type) => QUESTION_LABELS[type] || type).join(' · ');
    count.textContent = `${quiz.question_count}문항 · ${typeLabel}`;
    top.append(subject, count);
    const title = document.createElement('h3');
    title.textContent = quiz.title;
    const description = document.createElement('p');
    description.textContent = quiz.description || '설명 없이 바로 시작할 수 있는 퀴즈입니다.';
    const bottom = document.createElement('div');
    bottom.className = 'quiz-card-bottom';
    const label = document.createElement('span');
    label.textContent = '학습 방식 선택';
    const arrow = document.createElement('span');
    arrow.textContent = '→';
    bottom.append(label, arrow);
    card.append(top, title, description, bottom);
    return card;
}

function renderSubjectFilters(subjects) {
    if (activeSubject && !subjects.some((subject) => subject.name === activeSubject)) activeSubject = '';
    const total = subjects.reduce((sum, subject) => sum + subject.count, 0);
    const items = [{name: '', label: `전체 ${total}`}, ...subjects.map((subject) => ({name: subject.name, label: `${subject.name} ${subject.count}`}))];
    filterContainer.replaceChildren(...items.map((item) => {
        const button = document.createElement('button');
        button.className = 'filter-chip';
        button.classList.toggle('active', item.name === activeSubject);
        button.setAttribute('aria-pressed', String(item.name === activeSubject));
        button.type = 'button';
        button.dataset.subject = item.name;
        button.textContent = item.label;
        return button;
    }));
}

async function loadQuizzes() {
    activeRequest?.abort();
    const requestController = new AbortController();
    activeRequest = requestController;
    showSkeletons();
    const params = new URLSearchParams();
    const keyword = searchInput.value.trim();
    if (keyword) params.set('q', keyword);
    if (activeSubject) params.set('subject', activeSubject);
    try {
        const {quizzes, subjects} = await apiRequest(`/api/quizzes?${params}`, {signal: requestController.signal});
        if (activeRequest !== requestController) return;
        emptyState.querySelector('h3').textContent = '검색 결과가 없어요';
        emptyState.querySelector('p').textContent = '검색어를 줄이거나 다른 과목을 선택해 보세요.';
        document.querySelector('#search-retry').hidden = true;
        document.querySelector('#search-reset').hidden = false;
        renderSubjectFilters(subjects || []);
        grid.replaceChildren(...quizzes.map(createQuizCard));
        grid.hidden = quizzes.length === 0;
        emptyState.hidden = quizzes.length !== 0;
        resultCount.textContent = `${quizzes.length}개의 학습 세트`;
    } catch (error) {
        if (error.name === 'AbortError') return;
        grid.replaceChildren();
        grid.hidden = true;
        emptyState.hidden = false;
        emptyState.querySelector('h3').textContent = '목록을 불러오지 못했어요';
        emptyState.querySelector('p').textContent = error.message;
        document.querySelector('#search-retry').hidden = false;
        document.querySelector('#search-reset').hidden = true;
        resultCount.textContent = '';
    } finally {
        if (activeRequest === requestController) grid.setAttribute('aria-busy', 'false');
    }
}

function setPreviewFlipped(flipped) {
    previewCard.setAttribute('aria-pressed', String(flipped));
    previewCard.classList.toggle('is-flipped', flipped);
    previewQuestion.hidden = flipped;
    previewAnswer.hidden = !flipped;
    previewHint.textContent = flipped ? '눌러서 질문 보기' : '눌러서 정답 확인';
}

function renderPreviewQuestion() {
    const question = previewQuiz.questions[previewIndex];
    const total = previewQuiz.questions.length;
    previewTitle.textContent = previewQuiz.title;
    previewSubject.textContent = previewQuiz.subject;
    previewQuestion.textContent = question.prompt;
    previewAnswer.textContent = question.answer;
    previewImage.hidden = !question.image_data;
    if (question.image_data) previewImage.src = question.image_data;
    previewCounter.textContent = `${String(previewIndex + 1).padStart(2, '0')} / ${String(total).padStart(2, '0')}`;
    previewProgress.style.width = `${((previewIndex + 1) / total) * 100}%`;
    previewPrevious.disabled = total < 2;
    previewNext.disabled = total < 2;
    setPreviewFlipped(false);
}

async function loadPreview() {
    previewQuiz = null;
    previewStart.hidden = true;
    previewImage.hidden = true;
    setPreviewFlipped(false);
    preview.classList.add('is-loading');
    previewRefresh.disabled = true;
    preview.setAttribute('aria-busy', 'true');
    try {
        const {quiz} = await apiRequest('/api/quizzes/preview');
        if (!quiz?.questions?.length) {
            previewTitle.textContent = '공개 퀴즈 미리보기';
            previewQuestion.textContent = '아직 공개된 퀴즈가 없어요.';
            previewHint.textContent = '첫 퀴즈를 만들어 보세요';
            previewCounter.textContent = '00 / 00';
            previewPrevious.disabled = true;
            previewNext.disabled = true;
            return;
        }
        previewQuiz = quiz;
        previewIndex = 0;
        previewStart.href = `/quiz.html?id=${encodeURIComponent(quiz.id)}`;
        previewStart.hidden = false;
        renderPreviewQuestion();
    } catch {
        previewTitle.textContent = '공개 퀴즈 미리보기';
        previewQuestion.textContent = '미리보기를 불러오지 못했어요.';
        previewHint.textContent = '잠시 후 다시 시도해 주세요';
        previewCounter.textContent = '-- / --';
        previewPrevious.disabled = true;
        previewNext.disabled = true;
    } finally {
        preview.classList.remove('is-loading');
        previewRefresh.disabled = false;
        preview.setAttribute('aria-busy', 'false');
    }
}

function movePreview(direction) {
    if (!previewQuiz) return;
    previewIndex = (previewIndex + direction + previewQuiz.questions.length) % previewQuiz.questions.length;
    renderPreviewQuestion();
}

searchForm.addEventListener('submit', (event) => { event.preventDefault(); loadQuizzes(); });
searchInput.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadQuizzes, 250); });
previewCard.addEventListener('click', () => { if (previewQuiz) setPreviewFlipped(previewCard.getAttribute('aria-pressed') !== 'true'); });
previewPrevious.addEventListener('click', () => movePreview(-1));
previewNext.addEventListener('click', () => movePreview(1));
previewRefresh.addEventListener('click', loadPreview);
preview.addEventListener('keydown', (event) => { if (event.key === 'ArrowLeft') { event.preventDefault(); movePreview(-1); } if (event.key === 'ArrowRight') { event.preventDefault(); movePreview(1); } });
filterContainer.addEventListener('click', (event) => { const button = event.target.closest('.filter-chip'); if (!button) return; activeSubject = button.dataset.subject; loadQuizzes(); });
document.querySelector('#search-retry').addEventListener('click', loadQuizzes);
document.querySelector('#search-reset').addEventListener('click', () => {
    searchInput.value = ''; activeSubject = ''; loadQuizzes(); searchInput.focus({preventScroll: true});
});

loadPreview();
loadQuizzes();
