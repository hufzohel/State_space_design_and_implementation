export const PUZZLE_SIZES = {
    pipes: { min: 2, max: 4, default: 2 },
    minesweeper: { min: 5, max: 9, default: 5, mineRatio: 0.15 }
};

// 15 % of the cells, rounded, never fewer than 1 mine.
export const mineCountFor = (size, ratio) =>
    Math.max(1, Math.round(size * size * ratio));

export function sizeChoices(puzzle) {
    const cfg = PUZZLE_SIZES[puzzle];
    if (!cfg) return null;

    const choices = [];
    for (let n = cfg.min; n <= cfg.max; n++) {
        const mines = cfg.mineRatio ? ` · ${mineCountFor(n, cfg.mineRatio)} mines` : "";
        choices.push({ id: n, name: `${n} × ${n}${mines}` });
    }
    return choices;
}

// Options merged into the "new puzzle" request.
export function sizeOptions(puzzle, size) {
    const cfg = PUZZLE_SIZES[puzzle];
    if (!cfg) return {};

    const n = size ?? cfg.default;
    const options = { rows: n, cols: n };
    if (cfg.mineRatio) options.mine_count = mineCountFor(n, cfg.mineRatio);
    return options;
}