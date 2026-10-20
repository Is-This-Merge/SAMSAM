import {mountChoiceReader} from './choice_reader.js';

/** Render only the answer controls; the page owns round state and networking. */
export function renderAnswer({question, answer, container, nextButton, isLocked, onChange, onSubmit}) {
    if (question.type === 'sentence') {
        const selected = answer || [];
        const box = document.createElement('div');
        box.className = 'sentence-builder';
        const heading = document.createElement('p');
        heading.textContent = `만든 문장 · ${selected.length} / ${question.choices.length} 단어`;
        const tray = document.createElement('div');
        tray.className = 'sentence-tray';
        tray.setAttribute('aria-label', '선택한 단어: 누르면 선택 취소');
        if (!selected.length) tray.textContent = '아래 단어를 순서대로 선택하세요.';
        selected.forEach((wordIndex, position) => {
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'word-token chosen';
            button.textContent = question.choices[wordIndex];
            button.setAttribute('aria-label', `${position + 1}번째 ${question.choices[wordIndex]} 취소`);
            button.addEventListener('click', () => {
                if (isLocked()) return;
                answer = selected.filter((_, i) => i !== position);
                onChange(answer);
            });
            tray.append(button);
        });
        const bank = document.createElement('div');
        bank.className = 'sentence-bank';
        bank.setAttribute('aria-label', '배열할 단어');
        question.choices.forEach((word, index) => {
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'word-token';
            button.textContent = word; button.disabled = selected.includes(index);
            button.addEventListener('click', () => {
                if (isLocked()) return;
                answer = [...selected, index];
                onChange(answer);
            });
            bank.append(button);
        });
        const reset = document.createElement('button');
        reset.type = 'button'; reset.className = 'button button-secondary';
        reset.textContent = '배열 초기화'; reset.disabled = !selected.length;
        reset.addEventListener('click', () => { if (!isLocked()) { answer = []; onChange(answer); } });
        box.append(heading, tray, bank, reset);
        container.replaceChildren(box);
        nextButton.disabled = selected.length !== question.choices.length;
        return;
    }

    if (question.type === 'fill_blank' || question.type === 'meaning') {
        const label = document.createElement('label');
        label.className = 'fill-answer';
        const span = document.createElement('span');
        span.textContent = question.type === 'meaning' ? '단어의 뜻 (등록된 뜻 중 하나)' : '빈칸 정답';
        const input = document.createElement('input');
        input.type = 'text';
        input.autocomplete = 'off';
        input.maxLength = 300;
        input.value = answer || '';
        input.placeholder = '정답을 입력하세요';
        input.addEventListener('input', () => {
            answer = input.value;
            onChange(answer, false);
            nextButton.disabled = !input.value.trim();
        });
        label.append(span, input);
        container.replaceChildren(label);
        input.focus({preventScroll: true});
        return;
    }

    if (question.type === 'flashcard') {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'flash-answer';
        card.textContent = '카드를 눌러 뒷면 확인';
        card.addEventListener('click', () => {
            card.textContent = question.choices[0];
            card.classList.add('revealed');
            const knew = document.createElement('button');
            knew.type = 'button';
            knew.className = 'button button-primary';
            knew.textContent = '알고 있었어요';
            const review = document.createElement('button');
            review.type = 'button';
            review.className = 'button button-secondary';
            review.textContent = '다시 볼래요';
            [knew, review].forEach((button, index) => button.addEventListener('click', () => {
                if (isLocked()) return;
                answer = index === 0;
                nextButton.disabled = false;
                onSubmit(answer);
            }));
            container.append(knew, review);
        }, {once: true});
        container.replaceChildren(card);
        return;
    }

    const options = question.choices.map((choice, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'answer-option';
        button.classList.toggle('selected', answer === index);
        button.setAttribute('aria-pressed', String(answer === index));
        const letter = document.createElement('span');
        letter.className = 'answer-letter';
        letter.textContent = String(index + 1);
        button.setAttribute('aria-keyshortcuts', String(index + 1));
        const text = document.createElement('span');
        text.textContent = question.type === 'comprehension' ? '해석 보기' : choice;
        button.append(letter, text);
        button.addEventListener('click', () => {
            if (isLocked()) return;
            answer = index;
            onChange(answer);
        });
        return button;
    });
    container.replaceChildren(...options);
    if (question.type === 'comprehension') {
        const index = answer ?? 0;
        const reader = mountChoiceReader(container, question.choices[index]);
        if (answer !== undefined) reader.showText(question.choices[index], `${index + 1}번 해석 선택됨 · 읽고 정답을 확인하세요`);
        return reader;
    }
}
