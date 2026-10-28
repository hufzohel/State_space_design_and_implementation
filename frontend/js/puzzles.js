/*
 * Frontend puzzle rules: apply a move + detect solved / lost / loops.
 *
 * Pipes state:       { rows, cols, cells: [[mask]] }
 *   mask bits: N=1, E=2, S=4, W=8 (which sides of the tile have a pipe)
 *   move: { row, col, action: "rotate" }   (rotates 90° clockwise)
 *
 * Minesweeper state: { rows, cols, cells: [[{ mine, adj, open, flag }]] }
 *   move: { row, col, action: "reveal" | "flag" }
 */

export const rotateMask = m => ((m << 1) | (m >> 3)) & 15;
const DIRS = [[-1, 0], [0, 1], [1, 0], [0, -1]]; // N E S W

export function applyMove(puzzle, state, mv) {
    const s = structuredClone(state);

    if (puzzle === "pipes") {
        for (let i = 0; i < (mv.turns ?? 1); i++) {
            s.cells[mv.row][mv.col] = rotateMask(
                s.cells[mv.row][mv.col]
            );
        }

        return s;
    }

    if (puzzle === "kakurasu") {
        if (
            mv.row < 0 ||
            mv.row >= s.rows ||
            mv.col < 0 ||
            mv.col >= s.cols
        ) {
            return s;
        }

        const current = s.cells[mv.row][mv.col];

        if (mv.value === 0 || mv.value === 1) {
            s.cells[mv.row][mv.col] = mv.value;
        } else {
            s.cells[mv.row][mv.col] =
                current === -1 ? 1 : current === 1 ? 0 : -1;
        }

        return s;
    }

    const first = s.cells[mv.row][mv.col];

    if (mv.action === "flag" || mv.action === "unflag") {
        if (!first.open) {
            first.flag = !first.flag;
        }

        return s;
    }

    const stack = [[mv.row, mv.col]];

    while (stack.length) {
        const [r, c] = stack.pop();
        const cell = s.cells[r]?.[c];

        if (!cell || cell.open || cell.flag) {
            continue;
        }

        cell.open = true;

        if (!cell.mine && cell.adj === 0) {
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    if (dr === 0 && dc === 0) {
                        continue;
                    }

                    if (s.cells[r + dr]?.[c + dc]) {
                        stack.push([r + dr, c + dc]);
                    }
                }
            }
        }
    }

    return s;
}

export function analyze(puzzle, s) {
    const none = new Set();

    if (!s) {
        return { status: "playing", loops: none };
    }

    if (puzzle === "minesweeper") {
        if (s.status === "lost") return { status: "lost", loops: none };
        if (s.status === "won") return { status: "solved", loops: none };
        if (s.status) return { status: "playing", loops: none };

        const all = s.cells.flat();

        if (all.some(c => c.open && c.mine)) {
            return { status: "lost", loops: none };
        }

        return {
            status: all.every(c => c.mine || c.open)
                ? "solved"
                : "playing",
            loops: none
        };
    }

    if (puzzle === "kakurasu") {
        return analyzeKakurasu(s);
    }

    const { rows, cols, cells } = s;
    const nb = new Map();
    let dangling = false;
    let edges = 0;

    for (let i = 0; i < rows * cols; i++) {
        nb.set(i, new Set());
    }

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            DIRS.forEach(([dr, dc], d) => {
                if (!(cells[r][c] & (1 << d))) {
                    return;
                }

                const nr = r + dr;
                const nc = c + dc;

                if (
                    nr < 0 ||
                    nc < 0 ||
                    nr >= rows ||
                    nc >= cols ||
                    !(cells[nr][nc] & (1 << ((d + 2) % 4)))
                ) {
                    dangling = true;
                } else if (d === 1 || d === 2) {
                    nb.get(r * cols + c).add(nr * cols + nc);
                    nb.get(nr * cols + nc).add(r * cols + c);
                    edges++;
                }
            });
        }
    }

    const queue = [...nb]
        .filter(([, v]) => v.size <= 1)
        .map(([k]) => k);

    while (queue.length) {
        const k = queue.pop();

        for (const n of nb.get(k)) {
            nb.get(n).delete(k);

            if (nb.get(n).size === 1) {
                queue.push(n);
            }
        }

        nb.delete(k);
    }

    const loops = new Set(nb.keys());

    const solved =
        !dangling &&
        loops.size === 0 &&
        edges === rows * cols - 1;

    return {
        status: solved ? "solved" : "playing",
        loops
    };
}

export function kakurasuState(data) {
    return {
        rows: data.rows,
        cols: data.cols,
        cells: data.state,
        row_hints: data.row_hints,
        col_hints: data.col_hints
    };
}

export function analyzeKakurasu(s) {
    const { rows, cols, cells, row_targets, col_targets } = s;

    const rowSums = Array(rows).fill(0);
    const colSums = Array(cols).fill(0);
    const loops = new Set();

    let complete = true;

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const value = cells[r][c];

            if (value === -1) {
                complete = false;
                continue;
            }

            if (value !== 0 && value !== 1) {
                complete = false;
                continue;
            }

            if (value === 1) {
                rowSums[r] += c + 1;
                colSums[c] += r + 1;
            }
        }
    }

    for (let r = 0; r < rows; r++) {
        if (rowSums[r] > row_targets[r]) {
            for (let c = 0; c < cols; c++) {
                loops.add(r * cols + c);
            }
        }
    }

    for (let c = 0; c < cols; c++) {
        if (colSums[c] > col_targets[c]) {
            for (let r = 0; r < rows; r++) {
                loops.add(r * cols + c);
            }
        }
    }

    const solved =
        complete &&
        rowSums.every((sum, r) => sum === row_targets[r]) &&
        colSums.every((sum, c) => sum === col_targets[c]);

    return {
        status: solved ? "solved" : "playing",
        loops,
        rowSums,
        colSums
    };
}