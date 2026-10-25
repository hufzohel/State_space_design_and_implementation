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
        s.cells[mv.row][mv.col] = rotateMask(s.cells[mv.row][mv.col]);
        return s;
    }
    const first = s.cells[mv.row][mv.col];
    if (mv.action === "flag") { if (!first.open) first.flag = !first.flag; return s; }
    const stack = [[mv.row, mv.col]];
    while (stack.length) {
        const [r, c] = stack.pop();
        const cell = s.cells[r][c];
        if (cell.open || cell.flag) continue;
        cell.open = true;
        if (!cell.mine && cell.adj === 0) {
            for (let dr = -1; dr <= 1; dr++)
                for (let dc = -1; dc <= 1; dc++)
                    if (s.cells[r + dr]?.[c + dc]) stack.push([r + dr, c + dc]);
        }
    }
    return s;
}

export function analyze(puzzle, s) {
    const none = new Set();
    if (puzzle === "minesweeper") {
        const all = s.cells.flat();
        if (all.some(c => c.open && c.mine)) return { status: "lost", loops: none };
        return { status: all.every(c => c.mine || c.open) ? "solved" : "playing", loops: none };
    }

    const { rows, cols, cells } = s;
    const nb = new Map();
    let dangling = false, edges = 0;
    for (let i = 0; i < rows * cols; i++) nb.set(i, new Set());

    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
        DIRS.forEach(([dr, dc], d) => {
            if (!(cells[r][c] & (1 << d))) return;
            const nr = r + dr, nc = c + dc;
            if (nr < 0 || nc < 0 || nr >= rows || nc >= cols || !(cells[nr][nc] & (1 << ((d + 2) % 4)))) {
                dangling = true;
            } else if (d === 1 || d === 2) { // count each connection once
                nb.get(r * cols + c).add(nr * cols + nc);
                nb.get(nr * cols + nc).add(r * cols + c);
                edges++;
            }
        });
    }

    // Prune dead ends; whatever remains lies on a loop.
    const queue = [...nb].filter(([, v]) => v.size <= 1).map(([k]) => k);
    while (queue.length) {
        const k = queue.pop();
        for (const n of nb.get(k)) {
            nb.get(n).delete(k);
            if (nb.get(n).size === 1) queue.push(n);
        }
        nb.delete(k);
    }
    const loops = new Set(nb.keys());
    const solved = !dangling && loops.size === 0 && edges === rows * cols - 1;
    return { status: solved ? "solved" : "playing", loops };
}