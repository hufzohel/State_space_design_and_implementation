// Offline demo backend. Not used when the real API is available.
import { rotateMask, applyMove } from "./puzzles.js";

const wait = ms => new Promise(r => setTimeout(r, ms));
const rnd = n => Math.floor(Math.random() * n);
const D = [[-1, 0], [0, 1], [1, 0], [0, -1]];

export async function generate(puzzle, options = {}) {
    const t = performance.now();

    await wait(150);

    let state;

    if (puzzle === "pipes") {
        state = genPipes(6, 6);
    } else if (puzzle === "minesweeper") {
        state = genMines(9, 9, 10);
    } else if (puzzle === "kakurasu") {
        state = genKakurasu(
            options.rows ?? 5,
            options.cols ?? 5
        );
    } else {
        throw new Error(`Unsupported puzzle: ${puzzle}`);
    }

    return {
        id: `mock-${puzzle}-${Date.now()}`,
        state,
        time: performance.now() - t
    };
}

export async function solve(puzzle, { state, algorithm }) {
    const t = performance.now();
    await wait(algorithm === "dfs" ? 700 : 300);
    const moves = [];
    if (puzzle === "pipes") {
        state.cells.forEach((row, r) => row.forEach((m, c) => {
            let k = 0;
            while (m !== state._answer[r][c] && k++ < 4) m = rotateMask(m);
            for (; k > 0; k--) moves.push({ row: r, col: c, action: "rotate" });
        }));
    } else {
        let s = state;
        s.cells.forEach((row, r) => row.forEach((cell, c) => {
            if (cell.mine || s.cells[r][c].open) return;
            const mv = { row: r, col: c, action: "reveal" };
            moves.push(mv);
            s = applyMove("minesweeper", s, mv);
        }));
    }
    return { moves, time: performance.now() - t };
}

function genPipes(R, C) {
    const answer = Array.from({ length: R }, () => Array(C).fill(0));
    const seen = new Set([0]), stack = [[0, 0]];
    while (stack.length) {
        const [r, c] = stack[stack.length - 1];
        const opts = D.map(([dr, dc], i) => [r + dr, c + dc, i])
            .filter(([a, b]) => a >= 0 && b >= 0 && a < R && b < C && !seen.has(a * C + b));
        if (!opts.length) { stack.pop(); continue; }
        const [a, b, i] = opts[rnd(opts.length)];
        answer[r][c] |= 1 << i;
        answer[a][b] |= 1 << ((i + 2) % 4);
        seen.add(a * C + b);
        stack.push([a, b]);
    }
    const cells = answer.map(row => row.map(m => { for (let k = rnd(4); k > 0; k--) m = rotateMask(m); return m; }));
    return { rows: R, cols: C, cells, _answer: answer }; // _answer: mock only
}

function genMines(R, C, n) {
    const cells = Array.from({ length: R }, () => Array.from({ length: C }, () => ({ mine: false, adj: 0, open: false, flag: false })));
    for (let placed = 0; placed < n;) {
        const r = rnd(R), c = rnd(C);
        if (!cells[r][c].mine) { cells[r][c].mine = true; placed++; }
    }
    cells.forEach((row, r) => row.forEach((cell, c) => {
        for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++)
            if (cells[r + dr]?.[c + dc]?.mine) cell.adj++;
    }));
    return { rows: R, cols: C, cells };
}

function genKakurasu(R, C) {
    const solution = Array.from(
        { length: R },
        () => Array.from({ length: C }, () => rnd(2))
    );

    const row_targets = solution.map(row =>
        row.reduce(
            (sum, value, c) => sum + value * (c + 1),
            0
        )
    );

    const col_targets = Array.from(
        { length: C },
        (_, c) =>
            solution.reduce(
                (sum, row, r) => sum + row[c] * (r + 1),
                0
            )
    );

    return {
        rows: R,
        cols: C,
        cells: Array.from(
            { length: R },
            () => Array(C).fill(-1)
        ),
        row_targets,
        col_targets,
        _solution: solution
    };
}