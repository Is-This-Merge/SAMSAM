// One handler prevents Enter's native button click from firing a second action.
export function handleStudyKey(event, {active, busy, checked, nextButton, options}) {
    if (!active || busy || event.isComposing || event.keyCode === 229 ||
        event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.repeat) {
        if (event.key === 'Enter') event.preventDefault();
        return;
    }
    const target = event.target;
    const typing = target?.matches?.('input, textarea, select, [contenteditable="true"]');
    if (event.key === 'Enter') {
        // Preserve Enter on navigation links and unrelated controls.
        if (target?.closest?.('a') || (target?.tagName === 'BUTTON' &&
            target !== nextButton && !target.classList.contains('answer-option'))) return;
        if (!nextButton.disabled) {
            event.preventDefault();
            nextButton.click();
        }
        return;
    }
    if (typing || checked || !/^[1-6]$/.test(event.key)) return;
    const option = options[Number(event.key) - 1];
    if (option && !option.disabled) {
        event.preventDefault();
        option.click();
    }
}
