import {renderAnswer} from '../study/answer_renderer.js';
import {apiRequest} from '../shared/api.js';
import {STUDY_LABELS, quizUrl} from '../shared/study_modes.js';
import {handleStudyKey} from '../study/keyboard.js';
import {paginateText} from '../study/passage_pages.js';
import {MasteryQueue} from '../study/mastery_queue.js';
import {recordMistake, readMistakes, recordReviewMistake} from '../study/mistake_store.js';
import {REVIEW_SELECTION_KEY, reviewQuestion, checkReviewAnswer} from '../study/mistake_review.js';

const params = new URLSearchParams(window.location.search);
const quizId = params.get('id');
const mode = params.get('mode') || 'standard';
const isReview = params.get('review') === '1';
let mastery;
let roundToken;
let checked = [];
let busy = false;
let articleOptions = null;
let articleSourceLoaded = false;
let solvedBlanks = new Map();
let lastPassageQuestion = null;
let answerControls;
const articleSetup = document.querySelector('#article-setup');
const loading = document.querySelector('#loading');
const studyView = document.querySelector('#study-view');
const resultView = document.querySelector('#result-view');
const errorView = document.querySelector('#error-view');
const nextButton = document.querySelector('#next-question');
document.querySelectorAll('[data-back-to-set]').forEach(link => { if (quizId) link.href = quizUrl(quizId); });
if (isReview) document.querySelectorAll('[data-back-to-set]').forEach(link => {
    link.href = '/mistakes.html'; link.textContent = '← 오답 목록';
});
if (isReview) document.querySelector('#error-view a').href = '/mistakes.html';

let quiz;
let currentIndex = 0;
let answers = [];
let passagePages = [];
let passagePage = 0;
const promptElement = document.querySelector('#question-prompt');

function showPassagePage() {
    promptElement.textContent = passagePages[passagePage] || '';
    document.querySelector('#passage-pages').style.visibility = passagePages.length > 1 ? 'visible' : 'hidden';
    document.querySelector('#passage-prev').disabled = passagePage === 0;
    document.querySelector('#passage-next').disabled = passagePage >= passagePages.length - 1;
    document.querySelector('#passage-page-count').textContent = `${passagePage + 1} / ${passagePages.length}`;
}

function fitPassage() {
    if (studyView.hidden || !quiz || promptElement.clientHeight < 1) return;
    const question = quiz.questions[currentIndex];
    let text = question.prompt;
    if (question.type === 'article') {
        for (const [index, answer] of solvedBlanks) {
            const solved = quiz.questions[index];
            if (solved.group === question.group) text = text.replace(`⟦${solved.blank_number}⟧ ___`, `⟦${solved.blank_number}⟧ ${answer}`);
        }
    }
    passagePages = paginateText(text, (part) => {
        promptElement.textContent = part;
        return promptElement.scrollHeight <= promptElement.clientHeight + 1;
    });
    passagePage = Math.min(passagePage, Math.max(0, passagePages.length - 1));
    if (question.type === 'article' && lastPassageQuestion !== currentIndex) {
        const target = passagePages.findIndex(page => page.includes(`⟦${question.blank_number}⟧`));
        if (target >= 0) passagePage = target;
    }
    lastPassageQuestion = currentIndex;
    showPassagePage();
}

document.querySelector('#passage-prev').addEventListener('click', () => {
    passagePage = Math.max(0, passagePage - 1); showPassagePage();
});
document.querySelector('#passage-next').addEventListener('click', () => {
    passagePage = Math.min(passagePages.length - 1, passagePage + 1); showPassagePage();
});
new ResizeObserver(() => fitPassage()).observe(promptElement);
document.fonts?.ready.then(fitPassage);
document.querySelector('#question-image').addEventListener('load', fitPassage);

function showOnly(target) {
    document.body.classList.toggle('study-active', target === studyView);
    [loading, studyView, resultView, errorView, articleSetup].forEach((view) => { view.hidden = view !== target; });
}

function fail(message) {
    showOnly(errorView);
    document.querySelector('#error-message').textContent = message;
}

function renderQuestion() {
    const question = quiz.questions[currentIndex];
    requestAnimationFrame(fitPassage);
    renderProgress();
    document.querySelector('#question-kicker').textContent = mastery.round === 1 ? '학습하기' : '틀린 문항 다시 풀기';
    if (isReview) {
        const record = question.reviewRecord;
        document.querySelector('#question-kicker').textContent += ` · ${record.quizTitle} · ${STUDY_LABELS[record.mode] || record.mode}`;
        if (record.type === 'comprehension' && question.type === 'flashcard') {
            document.querySelector('#question-kicker').textContent += ' · 기존 기록: 해석 카드 복습';
        }
    }
    if (question.type === 'article') document.querySelector('#question-kicker').textContent += ` · 이번 답: 빈칸 ⟦${question.blank_number}⟧ (${question.blank_count}개 중)`;
    document.querySelector('#question-prompt').textContent = question.prompt;
    document.querySelector('#question-prompt').classList.toggle('article-prompt', ['article', 'comprehension', 'sentence'].includes(question.type));
    document.querySelector('#answer-options').classList.toggle('paragraph-options', question.type === 'comprehension');
    document.querySelector('.question-stage').classList.remove('is-correct', 'is-incorrect');
    const source = document.querySelector('#question-source');
    source.hidden = !question.source;
    source.textContent = question.source ? `출처: ${question.source}` : '';
    source.title = source.textContent;
    const questionImage = document.querySelector('#question-image');
    questionImage.hidden = !question.image_data;
    if (question.image_data) questionImage.src = question.image_data;
    document.querySelector('#answer-feedback').hidden = true;
    nextButton.disabled = answers[currentIndex] === undefined;
    nextButton.textContent = '정답 확인';
    nextButton.hidden = question.type === 'flashcard';

    answerControls?.destroy?.();
    answerControls = renderAnswer({
        question, answer: answers[currentIndex], container: document.querySelector('#answer-options'),
        nextButton, isLocked: () => busy || checked[currentIndex],
        onChange(value, redraw = true) { answers[currentIndex] = value; if (redraw) renderQuestion(); },
        onSubmit(value) { answers[currentIndex] = value; submitAnswer(); },
    });
}

async function gradeQuiz() {
    nextButton.disabled = true;
    nextButton.textContent = '채점 중…';
    const result = isReview ? {
        score: 100, total_count: quiz.questions.length,
        results: quiz.questions.map((question, index) => checkReviewAnswer(question, answers[index])),
    } : await apiRequest(`/api/quizzes/${encodeURIComponent(quizId)}/study/grade`, {
        method: 'POST', json: {answers, token: roundToken},
    });
    showOnly(resultView);
    document.querySelector('#result-score').textContent = result.score;
    document.querySelector('#result-summary').textContent = `${result.total_count}${mode === 'article' ? '개 빈칸' : '문항'}을 모두 맞혔어요. ${mastery.round}회차 · 총 ${mastery.responses}번 답했어요.`;
    const reviewItems = result.results.map((item, index) => {
        const article = document.createElement('article');
        article.className = `result-review-item ${item.correct ? 'correct' : 'incorrect'}`;
        const heading = document.createElement('h3');
        heading.textContent = item.correct ? '학습 완료' : '다시 보기';
        if (mode === 'article') heading.textContent = `빈칸 ⟦${quiz.questions[index].blank_number}⟧ · ${heading.textContent}`;
        const prompt = document.createElement('p');
        prompt.textContent = quiz.questions[index].prompt;
        article.append(heading, prompt);
        if (item.correct_answer) {
            const answer = document.createElement('p');
            const selected = typeof item.selected_answer === 'number' ? quiz.questions[index].choices[item.selected_answer] :
                typeof item.selected_answer === 'boolean' ? (item.selected_answer ? '알고 있었어요' : '다시 볼래요') : item.selected_answer;
            answer.textContent = `내 답: ${selected} · 정답: ${item.correct_answer}`;
            article.append(answer);
        }
        if (item.explanation) {
            const explanation = document.createElement('small');
            explanation.textContent = item.explanation;
            article.append(explanation);
        }
        if (item.explanation_image_data) {
            const image = document.createElement('img');
            image.src = item.explanation_image_data;
            image.alt = `${index + 1}번 문항 해설 이미지`;
            article.append(image);
        }
        return article;
    });
    document.querySelector('#result-review').replaceChildren(...reviewItems);
}

function renderProgress() {
    document.querySelector('#question-progress').textContent = `${mastery.round}회차 · 완료 ${mastery.mastered.size}/${mastery.total} · 남은 ${mode === 'article' ? '빈칸' : '문항'} ${mastery.total - mastery.mastered.size}`;
    document.querySelector('#progress-bar').style.width = `${mastery.mastered.size / mastery.total * 100}%`;
    document.querySelector('.progress-track').setAttribute('aria-valuenow', String(mastery.mastered.size));
    document.querySelector('.progress-track').setAttribute('aria-valuemax', String(mastery.total));
}

async function submitAnswer() {
    if (busy || answers[currentIndex] === undefined) return;
    if (mode && !checked[currentIndex]) {
        busy = true;
        nextButton.disabled = true;
        document.querySelectorAll('#answer-options input, #answer-options button:not([data-reading-control])').forEach(el => { el.disabled = true; });
        try {
            const result = isReview ? checkReviewAnswer(quiz.questions[currentIndex], answers[currentIndex]) :
                await apiRequest(`/api/quizzes/${encodeURIComponent(quizId)}/study/check`, {
                method: 'POST', json: {token: roundToken, position: currentIndex, answer: answers[currentIndex]},
            });
            checked[currentIndex] = true;
            mastery.record(result.correct);
            try {
                if (isReview) {
                    if (!result.correct) recordReviewMistake(quiz.questions[currentIndex].reviewRecord.id, result.selected_text);
                } else recordMistake({quiz, mode, question: quiz.questions[currentIndex], result});
            } catch {
                const notice = document.querySelector('#mistake-save-notice');
                notice.hidden = false;
                notice.textContent = '브라우저 저장 공간을 사용할 수 없어 이번 오답 기록을 저장하지 못했어요. 학습은 계속할 수 있습니다.';
            }
            if (quiz.questions[currentIndex].type === 'article' && result.correct) {
                solvedBlanks.set(currentIndex, result.correct_answer);
                requestAnimationFrame(fitPassage);
            }
            renderProgress();
            document.querySelector('.question-stage').classList.add(result.correct ? 'is-correct' : 'is-incorrect');
            document.querySelectorAll('#answer-options .answer-option').forEach((button, index) => {
                button.classList.toggle('correct', quiz.questions[currentIndex].choices[index] === result.correct_answer);
                button.classList.toggle('incorrect', !result.correct && answers[currentIndex] === index);
            });
            const feedback = document.querySelector('#answer-feedback');
            feedback.classList.toggle('correct', result.correct);
            feedback.classList.toggle('incorrect', !result.correct);
            feedback.hidden = false;
            feedback.textContent = `${result.correct ? '✓ 정답이에요! 반복 목록에서 제외했어요.' : '✕ 오답이에요. 다음 회차에서 다시 풀어요.'} 정답: ${result.correct_answer}`;
            if (quiz.questions[currentIndex].type === 'comprehension') {
                feedback.textContent = result.correct ? '✓ 정답이에요! 이 문단은 학습을 마쳤어요.' : '✕ 오답이에요. 초록색으로 표시한 해석을 확인하세요.';
                answerControls?.showText(result.correct_answer);
            }
            if (quiz.questions[currentIndex].type === 'flashcard') {
                await advanceQuestion();
                return;
            }
            nextButton.textContent = mastery.complete ? '학습 완료' : (mastery.cursor === mastery.pending.length - 1 ? '오답 다시 풀기' : '다음 문항');
            nextButton.disabled = false;
            nextButton.focus({preventScroll: true});
        } catch (error) { fail(error.message); }
        finally { busy = false; }
        return;
    }
    busy = true;
    try { await advanceQuestion(); } catch (error) { fail(error.message); }
    finally { busy = false; }
}

async function advanceQuestion() {
    const nextIndex = mastery.advance();
    if (nextIndex !== null) {
        currentIndex = nextIndex;
        answers[currentIndex] = undefined;
        checked[currentIndex] = false;
        passagePage = 0;
        renderQuestion();
        return;
    }
    await gradeQuiz();
}
nextButton.addEventListener('click', submitAnswer);

document.addEventListener('keydown', (event) => handleStudyKey(event, {
    active: !studyView.hidden,
    busy,
    checked: Boolean(checked[currentIndex]),
    nextButton,
    options: document.querySelectorAll('#answer-options .answer-option'),
}));

document.querySelector('#retry-quiz').addEventListener('click', () => {
    answers = [];
    currentIndex = 0;
    passagePage = 0;
    checked = [];
    loadQuiz();
});

async function loadQuiz() {
    if (isReview) return loadReview();
    if (!quizId) return fail('선택한 퀴즈 정보가 없습니다. 홈에서 퀴즈를 다시 선택해 주세요.');
    try {
        showOnly(loading);
        if (mode === 'article' && !articleOptions) {
            if (!articleSourceLoaded) {
                const source = await apiRequest(`/api/quizzes/${encodeURIComponent(quizId)}/article-source`);
                document.querySelector('#article-text').value = source.text;
                document.querySelector('#article-input-source').textContent = source.source ? `기본 본문 출처: ${source.source}` : '영어 본문을 직접 입력해 주세요.';
                articleSourceLoaded = true;
            }
            showOnly(articleSetup);
            return;
        }
        let data;
        try {
            data = await apiRequest(`/api/quizzes/${encodeURIComponent(quizId)}/study?mode=${encodeURIComponent(mode)}`,
                mode === 'article' ? {method: 'POST', json: articleOptions} : {});
        } catch (error) {
            if (mode === 'article' && error.status === 400) {
                document.querySelector('#article-setup-error').textContent = error.message;
                document.querySelector('#article-setup-error').hidden = false;
                showOnly(articleSetup);
                return;
            }
            throw error;
        }
        quiz = data.quiz;
        currentIndex = 0; answers = []; checked = []; passagePage = 0;
        lastPassageQuestion = null; solvedBlanks = new Map();
        mastery = new MasteryQueue(quiz.questions.length, {shuffle: params.get('shuffle') === '1'});
        currentIndex = mastery.current;
        roundToken = data.token;
        document.querySelector('#match-game-link').href = `/match.html?id=${encodeURIComponent(quizId)}`;
        document.querySelector('#study-title').textContent = `${quiz.title} · ${STUDY_LABELS[mode] || mode}`;
        if (mastery.shuffle) document.querySelector('#study-title').textContent += ' · 셔플';
        document.querySelector('#study-subject').textContent = quiz.subject;
        document.querySelector('#study-description').textContent = '카드를 눌러 뜻을 확인하고, 알고 있었는지 선택하세요. 선택하면 바로 다음 카드로 넘어갑니다.';
        if (mode === 'standard' && quiz.questions.some(q => q.type !== 'flashcard')) document.querySelector('#study-description').textContent = '문항에 답한 뒤 정답을 확인하세요. 카드 문항은 뒷면을 확인한 뒤 알고 있었는지 선택합니다.';
        if (mode === 'meaning') document.querySelector('#study-description').textContent = '뜻을 하나 입력한 뒤 정답을 확인하세요. 띄어쓰기 차이는 무시하며, 등록되지 않은 유의어는 오답 처리될 수 있습니다.';
        if (mode === 'article') document.querySelector('#study-description').textContent = '번호가 표시된 이번 빈칸에 들어갈 말을 고르세요. 맞힌 빈칸은 본문에 채워지고, 틀린 빈칸만 다시 풉니다.';
        if (mode === 'sentence') document.querySelector('#study-description').textContent = '문단 해석과 원문 문맥을 참고해 [배열할 문장]을 완성하세요. 긴 힌트는 이전·다음 부분으로 넘겨 읽을 수 있습니다.';
        if (mode === 'comprehension') document.querySelector('#study-description').textContent = '영어 문단에 해당하는 한국어 해석을 고르세요.';
        document.querySelector('#study-description').textContent += ' 맞힌 문항은 제외하고, 오답이 없어질 때까지 반복합니다.';
        showOnly(studyView);
        document.querySelector('#edit-article').hidden = mode !== 'article';
        renderQuestion();
    } catch (error) { fail(error.message); }
}

function loadReview() {
    try {
        showOnly(loading);
        const ids = JSON.parse(sessionStorage.getItem(REVIEW_SELECTION_KEY) || '[]');
        if (!Array.isArray(ids) || !ids.every(id => typeof id === 'string')) throw new Error('테스트 목록이 올바르지 않아요.');
        const records = new Map(readMistakes().map(item => [item.id, item]));
        const selected = [...new Set(ids)].map(id => records.get(id)).filter(Boolean);
        if (!selected.length) throw new Error('테스트할 오답이 없어요. 오답 목록에서 다시 선택해 주세요.');
        quiz = {title: '오답 테스트', questions: selected.map(item => reviewQuestion(item))};
        answers = []; checked = []; passagePage = 0; lastPassageQuestion = null; solvedBlanks = new Map();
        mastery = new MasteryQueue(quiz.questions.length);
        currentIndex = mastery.current;
        document.querySelector('#study-title').textContent = `오답 테스트 · ${quiz.questions.length}문제`;
        document.querySelector('#study-subject').textContent = '오답 노트';
        document.querySelector('#study-description').textContent = '선택한 오답을 많은 순서부터 복습합니다. 맞힌 문제는 제외하고 모두 맞힐 때까지 반복해요. 누적 오답 기록은 유지됩니다.';
        document.querySelector('#match-game-link').hidden = true;
        document.querySelector('#edit-article').hidden = true;
        showOnly(studyView);
        renderQuestion();
    } catch (error) { fail(error.message); }
}

document.querySelector('#article-setup-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    document.querySelector('#article-start').disabled = true;
    document.querySelector('#article-setup-error').hidden = true;
    articleOptions = {
        text: document.querySelector('#article-text').value,
        blank_count: Number(document.querySelector('#article-blank-count').value),
        chunk_words: Number(document.querySelector('#article-chunk').value),
    };
    try { await loadQuiz(); }
    finally { busy = false; document.querySelector('#article-start').disabled = false; }
});
document.querySelector('#edit-article').addEventListener('click', () => {
    articleOptions = null; loadQuiz();
});

loadQuiz();
