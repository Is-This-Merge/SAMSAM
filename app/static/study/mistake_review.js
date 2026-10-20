export const REVIEW_SELECTION_KEY = 'samsam.review.selection.v1';

function shuffle(items, random) {
    for (let i = items.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [items[i], items[j]] = [items[j], items[i]];
    }
    return items;
}

export function reviewQuestion(item, random = Math.random) {
    let type = item.type || 'fill_blank';
    let choices = Array.isArray(item.question?.choices) ? item.question.choices.filter(c => typeof c === 'string') : [];
    let prompt = item.prompt;
    if (type === 'flashcard') type = 'meaning';
    if (type === 'sentence') choices = shuffle(item.answer.trim().split(/\s+/u), random);
    else if (!['meaning', 'fill_blank'].includes(type)) {
        // Older records did not store choices. Keep the original prompt and test recall.
        if (!choices.includes(item.answer) || choices.length < 2) {
            type = 'fill_blank';
            if (item.type === 'comprehension') type = 'flashcard';
            if (item.blankNumber) prompt = `빈칸 ⟦${item.blankNumber}⟧에 들어갈 말을 입력하세요.\n\n${prompt}`;
            choices = [item.answer];
        } else choices = shuffle([...choices], random);
    }
    return {type, prompt, choices, answer: item.answer, correct_index: choices.indexOf(item.answer),
        blank_number: item.blankNumber, blank_count: item.question?.blank_count || 1, group: item.id,
        source: item.source, image_data: item.question?.image_data, explanation: '', reviewRecord: item};
}

function normalize(value) {
    return value.normalize('NFKC').toLowerCase().replace(/\s+/gu, '').replace(/^[.!。]+|[.!。]+$/gu, '');
}
export function checkReviewAnswer(question, answer) {
    let correct, selected = answer;
    if (question.type === 'meaning') {
        const variants = [question.answer, ...question.answer.split(/[,;/\n]/u)]
            .flatMap(part => [part, part.replace(/\([^)]*\)/gu, '')]).map(normalize).filter(Boolean);
        correct = typeof answer === 'string' && !!answer.trim() && variants.includes(normalize(answer));
    } else if (question.type === 'fill_blank') {
        const compact = text => text.toLowerCase().trim().replace(/\s+/gu, ' ');
        correct = typeof answer === 'string' && !!answer.trim() && compact(answer) === compact(question.answer);
    } else if (question.type === 'sentence') {
        const valid = Array.isArray(answer) && answer.length === question.choices.length &&
            [...answer].sort((a, b) => a - b).every((n, i) => n === i);
        selected = valid ? answer.map(i => question.choices[i]).join(' ') : '';
        correct = valid && selected === question.answer.trim().replace(/\s+/gu, ' ');
    } else if (question.type === 'flashcard') {
        correct = answer === true;
        selected = answer ? '알고 있었어요' : '다시 볼래요';
    } else {
        correct = Number.isInteger(answer) && answer === question.correct_index;
        selected = question.choices[answer] || '';
    }
    return {correct: Boolean(correct), selected_answer: question.type === 'sentence' ? selected : answer,
        selected_text: String(selected ?? ''), correct_answer: question.answer, explanation: ''};
}
