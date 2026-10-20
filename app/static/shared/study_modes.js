export const QUESTION_LABELS = Object.freeze({multiple_choice: '객관식', true_false: 'O/X', flashcard: '단어 카드', fill_blank: '빈칸'});
export const STUDY_LABELS = Object.freeze({standard: '기본 카드', meaning: '뜻 입력', article: '랜덤 빈칸', sentence: '문장 배열', comprehension: '문단 해석 매칭'});
export function quizUrl(id, page = 'quiz', mode) {
    const params = new URLSearchParams({id});
    if (mode) params.set('mode', mode);
    return `/${page}.html?${params}`;
}
