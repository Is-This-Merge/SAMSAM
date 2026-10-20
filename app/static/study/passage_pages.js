// Prefer word boundaries; split an unusually long token only when necessary.
export function paginateText(text, fits) {
    const pages = [];
    let remaining = text;
    while (remaining.length) {
        if (fits(remaining)) { pages.push(remaining); break; }
        let low = 1;
        let high = remaining.length;
        let end = 1;
        while (low <= high) {
            const middle = Math.floor((low + high) / 2);
            if (fits(remaining.slice(0, middle))) { end = middle; low = middle + 1; }
            else high = middle - 1;
        }
        const prefix = remaining.slice(0, end);
        const boundary = Math.max(prefix.lastIndexOf(' '), prefix.lastIndexOf('\n'));
        if (boundary > 0) end = boundary + 1;
        // Do not cut a UTF-16 surrogate pair in half.
        if (end > 1 && /[\uD800-\uDBFF]/.test(remaining[end - 1])) end--;
        pages.push(remaining.slice(0, end));
        remaining = remaining.slice(end);
    }
    return pages.length ? pages : [''];
}
