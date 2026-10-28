import {
  config,
  getStatus,
  getOptions,
  generatePuzzle,
  solvePuzzle,
  applyMinesweeperAction,
  resetMinesweeper,
} from "./api.js";
import { applyMove, analyze } from "./puzzles.js";
import { PUZZLE_SIZES, sizeChoices, sizeOptions } from "./config.js";
import { renderBoard, renderHistory } from "./renderer.js";

// ---------- Elements ----------
const ui = {};
for (const id of [
  "status",
  "hint",
  "flag-mode",
  "flag-mode-label",
  "generator",
  "size",
  "size-row",
  "solver",
  "generate-button",
  "solve-button",
  "restart-button",
  "stat-gen",
  "stat-time",
  "stat-steps",
  "stat-algo",
  "first",
  "prev",
  "play",
  "next",
  "last",
  "speed",
  "history",
  "mock-toggle",
]) {
  ui[id.replace(/-./g, (m) => m[1].toUpperCase())] =
    document.getElementById(id);
}
const tabs = document.querySelectorAll("[data-puzzle]");

const HINTS = {
  pipes:
    "Click a tile to rotate it. Connect every pipe without forming a loop.",
  minesweeper:
    "Click to reveal a cell. Right-click or Shift+click to flag a mine.",
  kakurasu:
    "Click a cell to toggle black or white. Match every row and column target.",
};

// ---------- State ----------
// One session per puzzle tab, so switching tabs never loses progress.
// session = { snaps, moves, cursor, mode: "human"|"solver", playing, genMs, solveMs, algo, t0, t1 }
const sessions = {};
const prefs = {
  pipes: {
    generator: null,
    solver: "human",
    size: PUZZLE_SIZES.pipes.default,
  },
  minesweeper: {
    generator: null,
    solver: "human",
    size: PUZZLE_SIZES.minesweeper.default,
  },
  kakurasu: {
    generator: null,
    solver: "human",
    size: null,
  },
};
let puzzle = "pipes",
  options = null,
  busy = false,
  notice = null,
  playTimer = null;

const fmt = (ms) =>
  ms == null
    ? "–"
    : ms < 1000
      ? `${Math.round(ms)} ms`
      : `${(ms / 1000).toFixed(1)} s`;

// ---------- Render ----------
function canInteract() {
  const s = sessions[puzzle];
  return (
    !!s &&
    !busy &&
    !s.playing &&
    prefs[puzzle].solver === "human" &&
    s.mode === "human" &&
    s.cursor === s.moves.length &&
    analyze(puzzle, s.snaps[s.cursor]).status === "playing"
  );
}

function render() {
  const s = sessions[puzzle],
    p = prefs[puzzle];
  const total = s?.moves.length ?? 0,
    cur = s?.cursor ?? 0;
  let a = {
    status: "playing",
    loops: new Set(),
    rowSums: [],
    colSums: [],
  };

  if (s) {
    const state = s.snaps[cur];
    a = analyze(puzzle, state);
    renderBoard(puzzle, state, {
      loops: a.loops,
      status: a.status,
      last: cur ? s.moves[cur - 1] : null,
      locked: !canInteract(),
      onCell,
    });
  } else {
    renderBoard(puzzle, null);
  }

  // Status banner
  let text,
    kind = "info";
  if (notice) ({ text, kind } = notice);
  else if (!s) text = "Press “New puzzle” to start.";
  else if (a.status === "solved") {
    text =
      s.mode === "solver"
        ? `Solved by ${s.algo} in ${total} steps`
        : `Solved in ${total} steps`;
    kind = "win";
  } else if (a.status === "lost") {
    text = "You hit a mine – puzzle lost";
    kind = "lose";
  } else if (puzzle === "kakurasu" && a.loops.size) {
    text = "Some row or column totals exceed their targets.";
    kind = "warn";
  } else if (puzzle === "pipes" && a.loops.size) {
    text = "Loop detected – highlighted in red";
    kind = "warn";
  } else if (s.playing) text = "Playing solution…";
  else if (s.mode === "solver") text = `Step ${cur} of ${total}`;
  else if (cur < total)
    text = `Viewing step ${cur} of ${total} – go to the last step to continue`;
  else
    text =
      p.solver === "human" ? "Your move" : "Press “Solve” to run the solver";
  ui.status.textContent = text;
  ui.status.dataset.kind = kind;

  // Controls
  ui.generator.disabled = ui.solver.disabled = ui.size.disabled = busy;
  ui.hint.textContent = HINTS[puzzle];
  ui.flagModeLabel.hidden = puzzle !== "minesweeper";
  tabs.forEach((b) => (b.disabled = busy));
  ui.generateButton.disabled = busy;
  ui.generator.disabled = ui.solver.disabled = busy;
  ui.solveButton.disabled = busy || !s || p.solver === "human";
  ui.restartButton.disabled = busy || !total;
  ui.first.disabled = ui.prev.disabled = busy || !total || cur === 0;
  ui.next.disabled = ui.last.disabled = busy || !total || cur === total;
  ui.play.disabled = busy || !total;
  ui.play.textContent = s?.playing ? "Pause" : "Play";

  renderHistory(ui.history, s ? s.moves : null, cur, go);
  updateStats();
}

function updateStats() {
  const s = sessions[puzzle];
  ui.statGen.textContent = fmt(s?.genMs);
  const t =
    s?.mode === "solver"
      ? s.solveMs
      : s?.t0
        ? (s.t1 ?? performance.now()) - s.t0
        : null;
  ui.statTime.textContent = fmt(t);
  ui.statSteps.textContent = s ? s.moves.length : "–";
  ui.statAlgo.textContent = !s ? "–" : s.mode === "solver" ? s.algo : "Human";
}
setInterval(updateStats, 250);

// ---------- Actions ----------
async function run(text, fn) {
  busy = true;
  notice = { text, kind: "info" };
  render();
  try {
    await fn();
    notice = null;
  } catch (e) {
    notice = { text: e.message || "Request failed", kind: "error" };
  }
  busy = false;
  render();
}

async function generate() {
  if (busy) return;
  stopPlay();
  const name = puzzle;
  await run("Generating puzzle…", async () => {
    const r = await generatePuzzle(name, {
      generator: prefs[name].generator,
      ...sizeOptions(name, prefs[name].size),
    });
    sessions[name] = {
      id: r.id,
      snaps: [r.state],
      moves: [],
      cursor: 0,
      mode: "human",
      playing: false,
      genMs: r.time,
      solveMs: null,
      algo: null,
      t0: null,
      t1: null,
    };
  });
}

async function solve() {
  const name = puzzle,
    s = sessions[name],
    id = prefs[name].solver;
  if (busy || !s || id === "human") return;
  stopPlay();
  const label = ui.solver.selectedOptions[0].text,
    start = s.snaps[0];
  await run(`Running ${label}…`, async () => {
    const r = await solvePuzzle(name, {
      id: s.id,
      state: start,
      algorithm: id,
    });

    if (!r.solutionFound && !config.mock) {
      throw new Error(`Solver failed: ${r.status}`);
    }

    const snaps = r.snaps ? [start, ...r.snaps] : [start];

    if (!r.snaps) {
      for (const mv of r.moves) {
        snaps.push(applyMove(name, snaps[snaps.length - 1], mv));
      }
    }

    if (name === "minesweeper" && !r.moves.length) {
      throw new Error(`Solver made no moves (status: ${r.status})`);
    }

    if (
      name !== "minesweeper" &&
      snaps.length > 1 &&
      analyze(name, snaps[snaps.length - 1]).status !== "solved"
    ) {
      throw new Error("Solver returned an invalid solution.");
    }

    Object.assign(s, {
      snaps,
      moves: r.moves,
      cursor: 0,
      mode: "solver",
      solveMs: r.time,
      algo: label,
      t0: null,
      t1: null,
    });
  });
  if (!notice) startPlay();
}

async function onCell(row, col, how) {
  if (!canInteract()) {
    return;
  }

  const s = sessions[puzzle];
  const cur = s.snaps[s.cursor];

  if (puzzle === "kakurasu") {
    const current = cur.cells[row][col];

    const value = current === -1 ? 1 : current === 1 ? 0 : 1;

    const mv = {
      row,
      col,
      action: "assign",
      value,
    };

    const next = applyMove(puzzle, cur, mv);

    s.t0 ??= performance.now();
    s.moves.push(mv);
    s.snaps.push(next);
    s.cursor++;

    if (analyze(puzzle, next).status === "solved") {
      s.t1 = performance.now();
    }

    render();
    return;
  }

  let action = "rotate";

  if (puzzle === "minesweeper") {
    action = how === "flag" || ui.flagMode.checked ? "flag" : "reveal";

    const c = cur.cells[row][col];

    if (c.open || (c.flag && action === "reveal")) {
      return;
    }

    if (c.flag && action === "flag") action = "unflag";
  }

  if (puzzle === "minesweeper" && !config.mock) {
    const cell = row * cur.cols + col;

    await run("Applying move…", async () => {
      const result = await applyMinesweeperAction(s.id, action, cell);

      s.t0 ??= performance.now();
      s.moves.push(result.move);
      s.snaps.push(result.state);
      s.cursor++;

      if (result.status !== "playing") {
        s.t1 = performance.now();
      }
    });

    return;
  }

  const mv = { row, col, action };
  const next = applyMove(puzzle, cur, mv);

  s.t0 ??= performance.now();
  s.moves.push(mv);
  s.snaps.push(next);
  s.cursor++;

  if (analyze(puzzle, next).status !== "playing") {
    s.t1 = performance.now();
  }

  render();
}

async function restart() {
  const s = sessions[puzzle];
  if (!s) return;
  stopPlay();
  if (puzzle === "minesweeper" && !config.mock) {
    try {
      await resetMinesweeper(s.id);
    } catch (e) {
      notice = { text: e.message || "Reset failed", kind: "error" };
      render();
      return;
    }
  }
  Object.assign(s, {
    snaps: [s.snaps[0]],
    moves: [],
    cursor: 0,
    mode: "human",
    solveMs: null,
    algo: null,
    t0: null,
    t1: null,
  });
  render();
}

// ---------- History & playback ----------
function go(i) {
  const s = sessions[puzzle];
  if (!s) return;
  stopPlay();
  s.cursor = Math.max(0, Math.min(i, s.moves.length));
  render();
}

function stopPlay() {
  clearTimeout(playTimer);
  Object.values(sessions).forEach((s) => (s.playing = false));
}

function startPlay() {
  const s = sessions[puzzle];
  if (!s || !s.moves.length) return;
  if (s.cursor >= s.moves.length) s.cursor = 0;
  s.playing = true;
  render();
  playTimer = setTimeout(tick, +ui.speed.value);
}

function tick() {
  const s = sessions[puzzle];
  if (!s?.playing) return;
  s.cursor++;
  if (s.cursor >= s.moves.length) s.playing = false;
  render();
  if (s.playing) playTimer = setTimeout(tick, +ui.speed.value);
}

// ---------- Setup ----------
function fillSelects() {
  const o = options[puzzle],
    p = prefs[puzzle];
  const fill = (sel, items, val) => {
    sel.replaceChildren();
    items.forEach((i) => sel.add(new Option(i.name, i.id)));
    sel.value = val;
  };
  p.generator ??= o.generators[0].id;
  fill(ui.generator, o.generators, p.generator);
  fill(ui.solver, [{ id: "human", name: "Human" }, ...o.solvers], p.solver);
  ui.generator.hidden = o.generators.length < 2;
  const sizes = sizeChoices(puzzle);
  ui.sizeRow.style.display = sizes ? "" : "none";
  if (sizes) fill(ui.size, sizes, p.size);
}

function selectPuzzle(name) {
  stopPlay();
  puzzle = name;
  notice = null;
  tabs.forEach((b) =>
    b.setAttribute("aria-selected", b.dataset.puzzle === name),
  );
  fillSelects();
  render();
  if (!sessions[name]) generate();
}

tabs.forEach((b) => (b.onclick = () => selectPuzzle(b.dataset.puzzle)));
ui.generator.onchange = () => {
  prefs[puzzle].generator = ui.generator.value;
};
ui.size.onchange = () => {
  prefs[puzzle].size = +ui.size.value;
  generate();
};
ui.solver.onchange = () => {
  prefs[puzzle].solver = ui.solver.value;
  render();
};
ui.generateButton.onclick = generate;
ui.solveButton.onclick = solve;
ui.restartButton.onclick = restart;
ui.first.onclick = () => go(0);
ui.prev.onclick = () => go(sessions[puzzle].cursor - 1);
ui.next.onclick = () => go(sessions[puzzle].cursor + 1);
ui.last.onclick = () => go(Infinity);
ui.play.onclick = () =>
  sessions[puzzle]?.playing ? (stopPlay(), render()) : startPlay();

document.addEventListener("keydown", (e) => {
  if (/SELECT|INPUT/.test(e.target.tagName) || busy || !sessions[puzzle])
    return;
  if (e.key === "ArrowLeft") {
    go(sessions[puzzle].cursor - 1);
    e.preventDefault();
  }
  if (e.key === "ArrowRight") {
    go(sessions[puzzle].cursor + 1);
    e.preventDefault();
  }
});

async function loadOptions() {
  options = await getOptions();
  fillSelects();
}

ui.mockToggle.onchange = async () => {
  stopPlay();
  config.mock = ui.mockToggle.checked;
  for (const k in sessions) delete sessions[k]; // state formats may differ between mock and backend
  await loadOptions();
  render();
  generate();
};

(async function init() {
  try {
    await getStatus();
    config.mock = false;
  } catch {
    config.mock = true;
  }
  ui.mockToggle.checked = config.mock;
  await loadOptions();
  render();
  generate();
})();
