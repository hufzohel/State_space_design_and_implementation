import * as Mock from "./mock.js";

/*
 * API layer – the ONLY file that talks to the backend.
 *
 *   GET  /status
 *   GET  /options                  (optional – falls back to DEFAULT_OPTIONS)
 *   POST /{puzzle}/new             body: options   (e.g. { generator })
 *   POST /{puzzle}/solve           body: { state, algorithm }
 *   POST /{puzzle}/validate        body: { state }
 *
 * What the UI expects back (frontend state formats: see top of puzzles.js):
 *   new   -> { state, time }                          time in ms
 *   solve -> { moves: [{ row, col, action }], time }  time in ms
 */

const API_BASE_URL = "http://127.0.0.1:8000/api";

// Mock mode = offline demo (js/mock.js). Auto-switched off in app.js if the backend responds.
export const config = { mock: true };

const DEFAULT_OPTIONS = {
    pipes: {
        generators: [{ id: "random", name: "Random" }],
        solvers: [{ id: "dfs", name: "DFS" }, { id: "astar", name: "Heuristic (A*)" }]
    },
    minesweeper: {
        generators: [{ id: "random", name: "Random" }],
        solvers: [{ id: "dfs", name: "DFS" }, { id: "astar", name: "Heuristic (A*)" }]
    }
};

// ============================================================
// Adapters – the backend deliberately uses numeric boards while the
// frontend uses richer state objects for rendering and playback.
// Keep this conversion in one place so app.js stays backend-agnostic.
// ============================================================
function pipesState(data) {
    const cells = data.state ?? data.cells;
    return {
        rows: data.rows ?? cells.length,
        cols: data.cols ?? cells[0].length,
        // Backend bits: N=8, E=4, S=2, W=1.
        // Frontend bits: N=1, E=2, S=4, W=8.
        cells: cells.map(row => row.map(mask =>
            ((mask & 8) ? 1 : 0) |
            ((mask & 4) ? 2 : 0) |
            ((mask & 2) ? 4 : 0) |
            ((mask & 1) ? 8 : 0)
        ))
    };
}

function pipesMaskToBackend(mask) {
    return ((mask & 1) ? 8 : 0) |
        ((mask & 2) ? 4 : 0) |
        ((mask & 4) ? 2 : 0) |
        ((mask & 8) ? 1 : 0);
}

function minesweeperState(data) {
    const cells = data.state ?? data.cells;
    const mines = new Set(data.mine_positions ?? []);
    return {
        rows: data.rows ?? cells.length,
        cols: data.cols ?? cells[0].length,
        cells: cells.map((row, r) => row.map((value, c) => ({
            open: value >= 0,
            flag: value === -2,
            mine: mines.has(r * (data.cols ?? cells[0].length) + c),
            adj: value >= 0 ? value : 0
        })))
    };
}

function optionsShape(data) {
    const normalize = values => values.map(item => typeof item === "string"
        ? { id: item, name: item }
        : item);
    return Object.fromEntries(Object.entries(data).map(([key, value]) => [key, {
        generators: normalize(value.generators),
        solvers: normalize(value.solvers)
    }]));
}

function fromBackend(puzzle, data, kind = "") {
    if (kind === "new") {
        return {
            id: data.puzzle_id ?? data.game_id,
            state: puzzle === "pipes" ? pipesState(data) : minesweeperState(data),
            time: (data.generation_time_seconds ?? 0) * 1000
        };
    }

    if (kind === "solve") {
        const moves = [];
        for (const step of data.steps ?? []) {
            const action = step.action ?? {};
            if (puzzle === "pipes") {
                const cols = data.cols ?? step.state?.[0]?.length ?? 1;
                const tile = action.tile_index ?? 0;
                moves.push({
                    row: Math.floor(tile / cols),
                    col: tile % cols,
                    action: "rotate",
                    turns: action.turns ?? 1
                });
            } else {
                const cols = data.cols ?? step.state?.[0]?.length ?? 1;
                const cell = action.cell ?? 0;
                moves.push({
                    row: Math.floor(cell / cols),
                    col: cell % cols,
                    action: action.action ?? "reveal"
                });
            }
        }
        return {
            moves,
            time: (data.stats?.elapsed ?? 0) * 1000,
            status: data.status,
            minePositions: data.mine_positions ?? []
        };
    }
    if (kind === "action") {
        const action = data.action ?? {};
        const cols = data.cols ?? data.state?.[0]?.length ?? 1;
        const cell = action.cell ?? 0;
        const state = minesweeperState(data);
        if (data.status === "lost") {
            state.cells[Math.floor(cell / cols)][cell % cols].open = true;
            state.cells[Math.floor(cell / cols)][cell % cols].mine = true;
        }
        return {
            state,
            status: data.status,
            move: {
                row: Math.floor(cell / cols),
                col: cell % cols,
                action: action.action ?? "reveal"
            }
        };
    }
    return data;
}

// ============================================================
// Request helper
// ============================================================
async function request(endpoint, options = {}) {
    const response = await fetch(API_BASE_URL + endpoint, {
        headers: { "Content-Type": "application/json" },
        ...options
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Request failed");
    return data;
}

// ============================================================
// Status & options
// ============================================================
export const getStatus = () => request("/status");

export async function getOptions() {
    if (config.mock) return DEFAULT_OPTIONS;
    try { return optionsShape(await request("/options")); }
    catch { return DEFAULT_OPTIONS; }
}

// ============================================================
// Puzzle generation
// ============================================================
export async function generatePuzzle(puzzle, options = {}) {
    if (config.mock) return Mock.generate(puzzle, options);
    const body = { ...options };
    if (body.generator == null) delete body.generator;
    const data = await request(`/${puzzle}/new`, {
        method: "POST",
        body: JSON.stringify(body)
    });
    return fromBackend(puzzle, data, "new");
}

// ============================================================
// Solving
// ============================================================
export async function solvePuzzle(puzzle, body = {}) {
    if (config.mock) return Mock.solve(puzzle, body);
    const payload = puzzle === "pipes"
        ? {
            puzzle_id: body.id,
            algorithm: body.algorithm,
            state: body.state?.cells?.map(row => row.map(pipesMaskToBackend))
        }
        : {
            game_id: body.id,
            algorithm: body.algorithm
        };
    const data = await request(`/${puzzle}/solve`, {
        method: "POST",
        body: JSON.stringify(payload)
    });
    return fromBackend(puzzle, data, "solve");
}

export async function applyMinesweeperAction(gameId, action, cell) {
    if (config.mock) return null;
    const data = await request("/minesweeper/action", {
        method: "POST",
        body: JSON.stringify({ game_id: gameId, action, cell })
    });
    return fromBackend("minesweeper", data, "action");
}

// ============================================================
// Validation (optional future endpoint)
// The UI currently validates on the frontend (puzzles.js → analyze).
// ============================================================
export async function validateState(puzzle, state) {
    if (config.mock) return null;
    return request(`/${puzzle}/validate`, {
        method: "POST",
        body: JSON.stringify({ state: state?.cells ?? state })
    });
}
