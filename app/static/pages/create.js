import {apiRequest} from '../shared/api.js';

const form = document.querySelector('#quiz-form');
const questionsContainer = document.querySelector('#questions');
const questionTemplate = document.querySelector('#question-template');
const choiceTemplate = document.querySelector('#choice-template');
const message = document.querySelector('#form-message');
const subjectMessage = document.querySelector('#subject-message');
const previousButton = document.querySelector('#previous-step');
const nextButton = document.querySelector('#next-step');
const submitButton = document.querySelector('#submit-quiz');
const editQuizId = new URLSearchParams(window.location.search).get('id');
let currentStep = 1;

function showMessage(text, success = false) {
    message.textContent = text;
    message.classList.toggle('success', success);
    message.classList.toggle('error', Boolean(text) && !success);
}

form.elements.subject.addEventListener('input', (event) => {
    const containedSpaces = /\s/.test(event.target.value);
    event.target.value = event.target.value.replace(/\s+/g, '');
    subjectMessage.textContent = containedSpaces ? '과목에는 띄어쓰기를 사용할 수 없습니다.' : '';
});

function updateQuestionNumbers() {
    const cards = [...questionsContainer.querySelectorAll('.question-card')];
    cards.forEach((card, index) => {
        card.querySelector('.question-number').textContent = index + 1;
        card.querySelector('.move-up').disabled = index === 0;
        card.querySelector('.move-down').disabled = index === cards.length - 1;
        card.querySelectorAll('.correct-choice').forEach((radio, choiceIndex) => {
            const id = `question-${index}-choice-${choiceIndex}`;
            radio.name = `question-${index}-correct`;
            radio.id = id;
            radio.nextElementSibling.htmlFor = id;
            radio.nextElementSibling.textContent = `${choiceIndex + 1}번을 정답으로 선택`;
            radio.nextElementSibling.nextElementSibling.textContent = String.fromCharCode(65 + choiceIndex);
        });
    });
    document.querySelector('#question-count').textContent = `${cards.length}개 문항`;
}

function addChoice(card, value = '') {
    const list = card.querySelector('.choice-list');
    if (list.children.length >= 6) return;
    const row = choiceTemplate.content.firstElementChild.cloneNode(true);
    row.querySelector('.choice-text').value = value;
    list.append(row);
    updateQuestionNumbers();
}

function buildFillBlankPrompt(prompt, answer) {
    if (!prompt || !answer || prompt.includes('___')) return prompt;
    const index = prompt.toLocaleLowerCase().indexOf(answer.toLocaleLowerCase());
    if (index < 0) return prompt;
    return `${prompt.slice(0, index)}___${prompt.slice(index + answer.length)}`;
}

function updateFillBlankPreview(card) {
    const preview = card.querySelector('.fill-blank-preview');
    const isFillBlank = card.querySelector('.question-type').value === 'fill_blank';
    preview.hidden = !isFillBlank;
    if (!isFillBlank) return;
    const prompt = card.querySelector('.question-prompt').value.trim();
    const answer = card.querySelector('.choice-text')?.value.trim() || '';
    preview.querySelector('p').textContent = buildFillBlankPrompt(prompt, answer) || '본문과 정답을 입력하면 빈칸이 자동으로 표시됩니다.';
}

function configureQuestionType(card) {
    const type = card.querySelector('.question-type').value;
    const list = card.querySelector('.choice-list');
    if (type === 'true_false') {
        list.replaceChildren();
        addChoice(card, 'O');
        addChoice(card, 'X');
        [...list.querySelectorAll('.choice-text')].forEach((input) => { input.readOnly = true; });
    } else if (type !== 'multiple_choice') {
        while (list.children.length > 1) list.lastElementChild.remove();
        if (!list.children.length) addChoice(card);
    } else {
        [...list.querySelectorAll('.choice-text')].forEach((input) => { input.readOnly = false; });
        while (list.children.length < 2) addChoice(card);
    }

    const rows = [...list.querySelectorAll('.choice-row')];
    const selectable = ['multiple_choice', 'true_false'].includes(type);
    card.querySelector('.choices-label strong').textContent = type === 'flashcard' ? '카드 뒷면' : type === 'fill_blank' ? '빈칸 정답' : '선택지';
    card.querySelector('.choices-label small').textContent = selectable ? '왼쪽 원을 눌러 정답을 지정하세요.' : type === 'fill_blank' ? '본문에 포함된 정답을 입력하면 첫 번째 표현이 빈칸으로 바뀝니다.' : '카드 뒷면에 표시할 내용을 입력하세요.';
    card.querySelector('.add-choice').hidden = type !== 'multiple_choice';
    rows.forEach((row) => {
        row.querySelector('.correct-choice').hidden = !selectable;
        row.querySelector('.correct-choice').disabled = !selectable;
        row.querySelector('.choice-letter').hidden = !selectable;
        row.querySelector('.remove-choice').hidden = type !== 'multiple_choice';
        row.querySelector('.choice-text').placeholder = type === 'flashcard' ? '카드 뒷면 내용' : type === 'fill_blank' ? '본문에서 빈칸으로 만들 정답' : '선택지 입력';
    });
    if (!selectable && rows[0]) rows[0].querySelector('.correct-choice').checked = true;
    updateFillBlankPreview(card);
    updateQuestionNumbers();
}

function questionData(card) {
    const type = card.querySelector('.question-type').value;
    const choices = [...card.querySelectorAll('.choice-text:not(:disabled)')].map((input) => input.value.trim());
    const originalPrompt = card.querySelector('.question-prompt').value.trim();
    return {
        question_type: type,
        prompt: type === 'fill_blank' ? buildFillBlankPrompt(originalPrompt, choices[0] || '') : originalPrompt,
        explanation: card.querySelector('.question-explanation').value.trim(),
        image_data: card.dataset.imageData || '',
        explanation_image_data: card.dataset.explanationImageData || '',
        choices,
        correct_index: ['multiple_choice', 'true_false'].includes(type)
            ? [...card.querySelectorAll('.correct-choice')].findIndex((radio) => radio.checked)
            : 0,
    };
}

function setImage(card, kind, dataUrl) {
    const key = kind === 'explanation' ? 'explanationImageData' : 'imageData';
    card.dataset[key] = dataUrl;
    const preview = card.querySelector(`[data-image-preview="${kind}"]`);
    preview.querySelector('img').src = dataUrl;
    preview.hidden = false;
}

function addQuestion(data = {}) {
    if (questionsContainer.children.length >= 100) return;
    const card = questionTemplate.content.firstElementChild.cloneNode(true);
    const type = data.type || data.question_type || 'multiple_choice';
    const choices = Array.isArray(data.choices) && data.choices.length ? data.choices : ['', ''];
    const editablePrompt = type === 'fill_blank' && data.prompt?.includes('___')
        ? data.prompt.replace('___', choices[0] || '')
        : data.prompt || '';
    card.querySelector('.question-type').value = type;
    card.querySelector('.question-prompt').value = editablePrompt;
    card.querySelector('.question-explanation').value = data.explanation || '';
    choices.forEach((choice) => addChoice(card, choice));
    questionsContainer.append(card);
    configureQuestionType(card);
    if (data.image_data) setImage(card, 'question', data.image_data);
    if (data.explanation_image_data) setImage(card, 'explanation', data.explanation_image_data);
    if (Number.isInteger(data.correct_index) && card.querySelectorAll('.correct-choice')[data.correct_index]) {
        card.querySelectorAll('.correct-choice')[data.correct_index].checked = true;
    }
    updateQuestionNumbers();
}

function failQuestion(card, text, focusTarget) {
    showMessage(text);
    card.scrollIntoView({behavior: 'smooth', block: 'center'});
    focusTarget?.focus();
    return false;
}

function validateQuestions() {
    const cards = [...questionsContainer.querySelectorAll('.question-card')];
    if (!cards.length) { showMessage('문항을 한 개 이상 추가해 주세요.'); return false; }
    for (const card of cards) {
        const type = card.querySelector('.question-type').value;
        const promptInput = card.querySelector('.question-prompt');
        const choiceInputs = [...card.querySelectorAll('.choice-text:not(:disabled)')];
        const answers = choiceInputs.map((input) => input.value.trim());
        if (!promptInput.value.trim()) return failQuestion(card, '모든 문항의 질문을 입력해 주세요.', promptInput);
        if (type === 'multiple_choice') {
            if (answers.length < 2 || answers.some((answer) => !answer)) return failQuestion(card, '객관식 선택지를 두 개 이상 모두 입력해 주세요.', choiceInputs.find((input) => !input.value.trim()));
            if (!card.querySelector('.correct-choice:checked')) return failQuestion(card, '객관식 문항의 정답을 선택해 주세요.', card.querySelector('.correct-choice'));
        } else if (type === 'true_false' && !card.querySelector('.correct-choice:checked')) {
            return failQuestion(card, 'O/X 문항의 정답을 선택해 주세요.', card.querySelector('.correct-choice'));
        } else if (type === 'flashcard' && !answers[0]) {
            return failQuestion(card, '단어 카드의 뒷면 내용을 입력해 주세요.', choiceInputs[0]);
        } else if (type === 'fill_blank') {
            if (!answers[0]) return failQuestion(card, '빈칸으로 만들 정답을 입력해 주세요.', choiceInputs[0]);
            const prompt = promptInput.value.trim();
            if (!prompt.includes('___') && !prompt.toLocaleLowerCase().includes(answers[0].toLocaleLowerCase())) {
                return failQuestion(card, '빈칸 정답은 입력한 본문 안에 포함되어야 합니다.', choiceInputs[0]);
            }
        }
    }
    showMessage('');
    return true;
}

function validatePanel(step) {
    if (step === 2) return validateQuestions();
    const invalid = document.querySelector(`[data-step="${step}"]`).querySelector(':invalid');
    if (invalid) { invalid.reportValidity(); invalid.focus(); return false; }
    showMessage('');
    return true;
}

function escapeHtml(value) {
    const node = document.createElement('div');
    node.textContent = value;
    return node.innerHTML;
}

function renderReview() {
    const cards = [...questionsContainer.querySelectorAll('.question-card')];
    const types = {multiple_choice: '객관식', true_false: 'O/X', flashcard: '단어 카드', fill_blank: '빈칸 채우기'};
    document.querySelector('#quiz-review').innerHTML = `<dl><div><dt>제목</dt><dd>${escapeHtml(form.elements.title.value)}</dd></div><div><dt>과목</dt><dd>${escapeHtml(form.elements.subject.value)}</dd></div><div><dt>공개 범위</dt><dd>${form.elements.visibility.value === 'public' ? '공개' : '비공개'}</dd></div><div><dt>문항</dt><dd>${cards.length}개</dd></div></dl><ol>${cards.map((card, index) => { const data = questionData(card); const images = [data.image_data && '문제 사진', data.explanation_image_data && '해설 사진'].filter(Boolean).join(' · '); return `<li><strong>${index + 1}. ${escapeHtml(data.prompt)}</strong><span>${types[data.question_type]}${images ? ` · ${images}` : ''}</span></li>`; }).join('')}</ol>`;
}

function goToStep(step) {
    currentStep = step;
    document.querySelectorAll('.wizard-panel').forEach((panel) => { panel.hidden = Number(panel.dataset.step) !== step; });
    document.querySelectorAll('[data-step-indicator]').forEach((item) => {
        item.classList.toggle('active', Number(item.dataset.stepIndicator) <= step);
        item.classList.toggle('current', Number(item.dataset.stepIndicator) === step);
    });
    previousButton.hidden = step === 1;
    nextButton.hidden = step === 3;
    submitButton.hidden = step !== 3;
    if (step === 3) renderReview();
    window.scrollTo({top: 0, behavior: 'smooth'});
}

document.querySelector('#add-question-bottom').addEventListener('click', () => addQuestion());
nextButton.addEventListener('click', () => { if (validatePanel(currentStep)) goToStep(currentStep + 1); });
previousButton.addEventListener('click', () => goToStep(currentStep - 1));

questionsContainer.addEventListener('input', (event) => {
    const card = event.target.closest('.question-card');
    if (card && (event.target.matches('.question-prompt') || event.target.matches('.choice-text'))) updateFillBlankPreview(card);
});

questionsContainer.addEventListener('click', (event) => {
    const card = event.target.closest('.question-card');
    if (!card) return;
    if (event.target.closest('.add-choice')) addChoice(card);
    if (event.target.closest('.remove-choice')) {
        if (card.querySelectorAll('.choice-row').length <= 2) return showMessage('선택지는 최소 2개가 필요합니다.');
        event.target.closest('.choice-row').remove();
    }
    if (event.target.closest('.remove-question')) {
        if (questionsContainer.children.length <= 1) return showMessage('문항은 최소 1개가 필요합니다.');
        card.remove();
    }
    if (event.target.closest('.duplicate-question')) addQuestion(questionData(card));
    if (event.target.closest('.move-up') && card.previousElementSibling) questionsContainer.insertBefore(card, card.previousElementSibling);
    if (event.target.closest('.move-down') && card.nextElementSibling) questionsContainer.insertBefore(card.nextElementSibling, card);
    const removeImage = event.target.closest('.remove-image');
    if (removeImage) {
        const kind = removeImage.dataset.imageKind;
        const key = kind === 'explanation' ? 'explanationImageData' : 'imageData';
        delete card.dataset[key];
        card.querySelector(`.image-input[data-image-kind="${kind}"]`).value = '';
        card.querySelector(`[data-image-preview="${kind}"]`).hidden = true;
    }
    updateQuestionNumbers();
});

questionsContainer.addEventListener('change', (event) => {
    const card = event.target.closest('.question-card');
    if (!card) return;
    if (event.target.matches('.question-type')) configureQuestionType(card);
    if (event.target.matches('.image-input')) {
        const file = event.target.files[0];
        if (!file) return;
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 600 * 1024) {
            event.target.value = '';
            return showMessage('PNG, JPEG, WebP 형식의 600KB 이하 이미지를 선택해 주세요.');
        }
        const kind = event.target.dataset.imageKind;
        const reader = new FileReader();
        reader.onload = () => { setImage(card, kind, reader.result); showMessage(''); };
        reader.readAsDataURL(file);
    }
});

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!validateQuestions()) return goToStep(2);
    const payload = {title: form.elements.title.value, subject: form.elements.subject.value, description: form.elements.description.value, visibility: form.elements.visibility.value, questions: [...questionsContainer.querySelectorAll('.question-card')].map(questionData)};
    submitButton.disabled = true;
    showMessage('퀴즈를 저장하는 중입니다.');
    try {
        await apiRequest(editQuizId ? `/api/quizzes/${encodeURIComponent(editQuizId)}` : '/api/quizzes', {method: editQuizId ? 'PUT' : 'POST', json: payload});
        showMessage('저장했어요. 내 학습실로 이동합니다.', true);
        setTimeout(() => { window.location.href = '/inventory.html'; }, 500);
    } catch (error) {
        showMessage(error.message);
    } finally {
        submitButton.disabled = false;
    }
});

async function initialize() {
    if (!editQuizId) { addQuestion(); return; }
    try {
        const {quiz} = await apiRequest(`/api/quizzes/${encodeURIComponent(editQuizId)}?edit=1`);
        form.elements.title.value = quiz.title;
        form.elements.subject.value = quiz.subject;
        form.elements.description.value = quiz.description;
        form.elements.visibility.value = quiz.visibility;
        quiz.questions.forEach(addQuestion);
        submitButton.textContent = '변경사항 저장하기';
    } catch (error) {
        showMessage(error.message);
    }
}

initialize();
