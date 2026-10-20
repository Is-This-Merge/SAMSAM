import {paginateText} from './passage_pages.js';

/** Read long translations in-place without expanding the question card. */
export function mountChoiceReader(container, initialText) {
    const panel = document.createElement('section'); panel.className = 'choice-reader';
    const label = document.createElement('small'); label.textContent = '1번 해석 미리보기 · 번호를 눌러 답을 선택하세요';
    const body = document.createElement('p'); body.className = 'choice-reader-text'; body.tabIndex = 0;
    const controls = document.createElement('div'); controls.className = 'passage-pages choice-pages';
    const previous = document.createElement('button'); previous.type = 'button'; previous.textContent = '← 앞부분';
    const next = document.createElement('button'); next.type = 'button'; next.textContent = '뒷부분 →';
    [previous, next].forEach(button => { button.className = 'button button-secondary'; button.dataset.readingControl = ''; });
    const count = document.createElement('span'); count.setAttribute('aria-live', 'polite');
    controls.append(previous, count, next); panel.append(label, body, controls); container.append(panel);
    let text = initialText, pages = [text], page = 0, disposed = false;
    function display() {
        body.textContent = pages[page] || '';
        previous.disabled = page === 0; next.disabled = page === pages.length - 1;
        count.textContent = `${page + 1} / ${pages.length}`;
        controls.style.visibility = pages.length > 1 ? 'visible' : 'hidden';
    }
    function fit() {
        if (disposed || body.clientHeight < 1) return;
        pages = paginateText(text, part => { body.textContent = part; return body.scrollHeight <= body.clientHeight + 1; });
        page = Math.min(page, pages.length - 1); display();
    }
    previous.addEventListener('click', () => { page--; display(); });
    next.addEventListener('click', () => { page++; display(); });
    const observer = new ResizeObserver(fit); observer.observe(body);
    requestAnimationFrame(fit); document.fonts?.ready.then(fit);
    return {
        showText(value, caption = '정답 해석') { text = value; page = 0; label.textContent = caption; fit(); },
        destroy() { disposed = true; observer.disconnect(); },
    };
}
