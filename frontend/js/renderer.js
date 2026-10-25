const board = document.getElementById("board");
const SVG = "http://www.w3.org/2000/svg";
const ENDS = [[20, 0], [40, 20], [20, 40], [0, 20]]; // N E S W edge midpoints

const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
};
const coord = (r, c) => String.fromCharCode(65 + c) + (r + 1);

export function renderBoard(puzzle, state, { loops = new Set(), status = "playing", last = null, locked = false, onCell = () => {} } = {}) {
    board.replaceChildren();
    board.dataset.status = status;
    board.dataset.puzzle = puzzle;
    board.classList.toggle("locked", locked);
    if (!state) return;
    board.style.setProperty("--cols", state.cols);
    board.style.setProperty("--rows", state.rows);

    state.cells.forEach((row, r) => row.forEach((v, c) => {
        const b = el("button", "cell");
        b.type = "button";
        b.setAttribute("aria-label", coord(r, c));
        if (last && last.row === r && last.col === c) b.classList.add("last");
        b.onclick = e => onCell(r, c, e.shiftKey ? "flag" : "click");
        b.oncontextmenu = e => { e.preventDefault(); onCell(r, c, "flag"); };
        if (puzzle === "pipes") drawPipe(b, v, loops.has(r * state.cols + c));
        else drawMine(b, v, status === "lost");
        board.append(b);
    }));
}

function drawPipe(b, mask, inLoop) {
    b.classList.toggle("loop", inLoop);
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 40 40");
    const add = (tag, attrs) => {
        const n = document.createElementNS(SVG, tag);
        for (const k in attrs) n.setAttribute(k, attrs[k]);
        svg.append(n);
    };
    ENDS.forEach(([x, y], i) => { if (mask & (1 << i)) add("line", { x1: 20, y1: 20, x2: x, y2: y }); });
    add("circle", { cx: 20, cy: 20, r: 6 });
    b.append(svg);
}

function drawMine(b, c, lost) {
    if (c.open) {
        b.classList.add("open");
        if (c.mine) { b.textContent = "●"; b.classList.add("mine", "boom"); }
        else if (c.adj) { b.textContent = c.adj; b.dataset.n = Math.min(c.adj, 3); }
    } else if (c.flag) {
        b.textContent = "⚑";
    } else if (lost && c.mine) {
        b.textContent = "●";
        b.classList.add("mine");
    }
}

export function renderHistory(list, moves, cursor, onSelect) {
    const kept = list.scrollTop;
    list.replaceChildren();
    if (!moves) return;
    const add = (i, text) => {
        const li = el("li"), b = el("button", null, text);
        b.type = "button";
        if (i === cursor) b.setAttribute("aria-current", "step");
        b.onclick = () => onSelect(i);
        li.append(b);
        list.append(li);
    };
    add(0, "Start");
    moves.forEach((m, i) => add(i + 1, `${i + 1}. ${m.action} ${coord(m.row, m.col)}`));
    list.scrollTop = kept;
    const c = list.querySelector("[aria-current]");
    if (c) {
        if (c.offsetTop < list.scrollTop) list.scrollTop = c.offsetTop;
        else if (c.offsetTop + c.offsetHeight > list.scrollTop + list.clientHeight)
            list.scrollTop = c.offsetTop + c.offsetHeight - list.clientHeight;
    }
}