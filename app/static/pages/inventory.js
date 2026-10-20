import {apiRequest} from '../shared/api.js';

document.querySelector('#owned-quizzes')?.addEventListener('click', async (event) => {
    const button = event.target.closest('.delete-quiz');
    if (!button) return;
    const card = button.closest('[data-quiz-id]');
    if (!window.confirm('이 퀴즈와 관련 학습 기록을 삭제할까요?')) return;
    button.disabled = true;
    try {
        await apiRequest(`/api/quizzes/${encodeURIComponent(card.dataset.quizId)}`, {method: 'DELETE'});
        card.remove();
        const count = document.querySelectorAll('#owned-quizzes [data-quiz-id]').length;
        document.querySelector('#owned-count').textContent = `${count}개`;
        document.querySelector('#owned-empty').hidden = count !== 0;
    } catch (error) {
        button.disabled = false;
        card.querySelector('.share-message').textContent = error.message;
    }
});

document.querySelector('#owned-quizzes')?.addEventListener('submit', async (event) => {
    const form = event.target.closest('.share-form');
    if (!form) return;
    event.preventDefault();
    const card = form.closest('[data-quiz-id]');
    const input = form.querySelector('input');
    const message = form.querySelector('.share-message');
    const button = form.querySelector('button');
    button.disabled = true;
    message.textContent = '공유하는 중…';
    try {
        const result = await apiRequest(`/api/quizzes/${encodeURIComponent(card.dataset.quizId)}/collaborators`, {
            method: 'POST', json: {email: input.value},
        });
        message.textContent = `${result.collaborator.display_name}님에게 공동 편집 권한을 공유했습니다.`;
        form.reset();
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});
