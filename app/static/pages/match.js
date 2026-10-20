import {apiRequest} from '../shared/api.js';
import {quizUrl} from '../shared/study_modes.js';

const quizId = new URLSearchParams(window.location.search).get('id');
if (quizId) document.querySelector('.back-link').href = quizUrl(quizId);
const board = document.querySelector('#match-board');
const result = document.querySelector('#match-result');
let pairs = [], selected = null, matched = 0, startedAt = 0, timer;
function shuffle(items) {
    const result = [...items];
    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
}
function updateProgress() { document.querySelector('#match-progress').textContent = `${matched} / ${pairs.length}`; }
function startGame() {
    matched = 0; selected = null; startedAt = performance.now(); result.hidden = true; updateProgress();
    const tiles = pairs.flatMap((pair) => [{pair: pair.id, text: pair.term}, {pair: pair.id, text: pair.answer}]);
    board.replaceChildren(...shuffle(tiles).map((tile) => { const button = document.createElement('button'); button.type = 'button'; button.className = 'match-tile'; button.dataset.pair = tile.pair; button.textContent = tile.text; return button; }));
    clearInterval(timer); timer = setInterval(() => { document.querySelector('#match-time').textContent = `${((performance.now() - startedAt) / 1000).toFixed(1)}초`; }, 100);
}
board.addEventListener('click', (event) => {
    const tile = event.target.closest('.match-tile:not(.matched)'); if (!tile) return;
    if (!selected) { selected = tile; tile.classList.add('selected'); return; }
    if (selected === tile) { tile.classList.remove('selected'); selected = null; return; }
    if (selected.dataset.pair === tile.dataset.pair) { selected.classList.add('matched'); tile.classList.add('matched'); matched += 1; updateProgress(); if (matched === pairs.length) { clearInterval(timer); result.hidden = false; document.querySelector('#match-summary').textContent = `${((performance.now() - startedAt) / 1000).toFixed(1)}초 만에 완성했습니다.`; } } else selected.classList.remove('selected');
    selected = null;
});
document.querySelector('#match-retry').addEventListener('click', startGame);
async function load() {
    if (!quizId) { board.textContent = '선택한 퀴즈가 없습니다.'; return; }
    let data;
    try { data = await apiRequest(`/api/quizzes/${encodeURIComponent(quizId)}/match`); }
    catch (error) { board.textContent = error.message; return; }
    pairs = data.pairs; document.querySelector('#match-title').textContent = data.quiz.title;
    if (pairs.length < 2) { board.textContent = '매치 게임에는 문항이 2개 이상 필요합니다.'; return; } startGame();
}
load();
