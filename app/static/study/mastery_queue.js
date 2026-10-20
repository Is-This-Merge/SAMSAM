// Keep original question positions stable for server grading and review.
export class MasteryQueue {
    constructor(size, {shuffle = false, random = Math.random} = {}) {
        this.shuffle = shuffle;
        this.random = random;
        this.total = size;
        this.pending = Array.from({length: size}, (_, i) => i);
        this.shufflePending();
        this.missed = [];
        this.mastered = new Set();
        this.cursor = 0;
        this.round = 1;
        this.responses = 0;
        this.recorded = false;
    }
    get current() { return this.pending[this.cursor] ?? null; }
    get complete() { return this.mastered.size === this.total; }
    shufflePending() {
        if (!this.shuffle) return;
        for (let i = this.pending.length - 1; i > 0; i--) {
            const j = Math.floor(this.random() * (i + 1));
            [this.pending[i], this.pending[j]] = [this.pending[j], this.pending[i]];
        }
    }
    record(correct) {
        if (this.recorded || this.current === null) throw new Error('Question already checked');
        if (correct) this.mastered.add(this.current);
        else this.missed.push(this.current);
        this.responses++;
        this.recorded = true;
    }
    advance() {
        if (!this.recorded) throw new Error('Check the answer before continuing');
        this.cursor++;
        this.recorded = false;
        if (this.cursor >= this.pending.length && this.missed.length) {
            this.pending = this.missed;
            this.shufflePending();
            this.missed = [];
            this.cursor = 0;
            this.round++;
        }
        return this.current;
    }
}
