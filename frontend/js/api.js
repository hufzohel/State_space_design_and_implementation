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

// TODO: remove once GET /options exists.
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
// Adapters – the only place to convert between backend and
// frontend formats (e.g. flat array <-> 2D grid, field names).
// Identity for now; fill in once the real response shapes are known.
// ============================================================
const toBackend = (puzzle, body) => body;
const fromBackend = (puzzle, data) => data;

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
    try { return await request("/options"); }
    catch { return DEFAULT_OPTIONS; }
}

// ============================================================
// Puzzle generation
// ============================================================
export async function generatePuzzle(puzzle, options = {}) {
    if (config.mock) return Mock.generate(puzzle, options);
    const data = await request(`/${puzzle}/new`, {
        method: "POST",
        body: JSON.stringify(toBackend(puzzle, options))
    });
    return fromBackend(puzzle, data);
}

// ============================================================
// Solving
// ============================================================
export async function solvePuzzle(puzzle, body = {}) {
    if (config.mock) return Mock.solve(puzzle, body);
    const data = await request(`/${puzzle}/solve`, {
        method: "POST",
        body: JSON.stringify(toBackend(puzzle, body))
    });
    return fromBackend(puzzle, data);
}

// ============================================================
// Validation (optional future endpoint)
// The UI currently validates on the frontend (puzzles.js → analyze).
// ============================================================
export async function validateState(puzzle, state) {
    if (config.mock) return null;
    return request(`/${puzzle}/validate`, {
        method: "POST",
        body: JSON.stringify(toBackend(puzzle, { state }))
    });
}