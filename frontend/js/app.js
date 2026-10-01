import {
    getStatus,
    generatePuzzle,
    solvePuzzle
} from "./api.js";

import {
    renderBoard
} from "./renderer.js";

import {
    setSolution,
    nextStep,
    previousStep,
    play,
    pause
} from "./playback.js";


let currentPuzzle = null;
let currentState = null;


// ============================================================
// Elements
// ============================================================

const puzzleName = document.getElementById("puzzle-name");
const status = document.getElementById("status");

const algorithm = document.getElementById("algorithm");
const steps = document.getElementById("steps");
const time = document.getElementById("time");

const pipesButton = document.getElementById("pipes-button");
const minesweeperButton = document.getElementById("minesweeper-button");

const newPuzzleButton = document.getElementById("new-puzzle-button");
const solveInstantlyButton = document.getElementById("solve-instantly-button");
const solveStepButton = document.getElementById("solve-step-button");


// ============================================================
// Puzzle selection
// ============================================================

pipesButton.addEventListener("click", () => {
    selectPuzzle("pipes");
});


minesweeperButton.addEventListener("click", () => {
    selectPuzzle("minesweeper");
});


function selectPuzzle(puzzle) {
    currentPuzzle = puzzle;

    puzzleName.textContent =
        puzzle === "pipes"
            ? "Pipes"
            : "Minesweeper";

    status.textContent =
        "Puzzle selected. Generate a puzzle.";
}


// ============================================================
// Generate puzzle
// ============================================================

newPuzzleButton.addEventListener("click", async () => {

    if (!currentPuzzle) {
        status.textContent = "Please select a puzzle first.";
        return;
    }

    try {

        status.textContent = "Generating puzzle...";

        const result =
            await generatePuzzle(currentPuzzle);

        /*
         * Eventually the backend will return the actual
         * puzzle state here.
         */
        currentState = result.state;

        renderBoard(
            result.board,
            handleCellClick
        );

        status.textContent = "Puzzle generated.";

    } catch (error) {

        status.textContent =
            "Backend: " + error.message;
    }
});


// ============================================================
// Human interaction
// ============================================================

function handleCellClick(row, col) {

    if (!currentPuzzle) {
        return;
    }

    /*
     * Later:
     *
     * This will modify the current puzzle state.
     *
     * Pipes:
     *     rotate tile
     *
     * Minesweeper:
     *     reveal / flag cell
     */

    console.log(
        "Clicked:",
        currentPuzzle,
        row,
        col
    );
}


// ============================================================
// Solve instantly
// ============================================================

solveInstantlyButton.addEventListener("click", async () => {

    if (!currentPuzzle) {
        status.textContent = "Please select a puzzle first.";
        return;
    }

    try {

        status.textContent = "Solving...";

        const result =
            await solvePuzzle(
                currentPuzzle,
                currentState,
                "astar"
            );

        algorithm.textContent =
            result.algorithm ?? "-";

        steps.textContent =
            result.steps ?? "-";

        time.textContent =
            result.time ?? "-";

        /*
         * Eventually:
         *
         * render the final solved state
         */

        status.textContent = "Solved.";

    } catch (error) {

        status.textContent =
            "Backend: " + error.message;
    }
});


// ============================================================
// Solve step by step
// ============================================================

solveStepButton.addEventListener("click", async () => {

    if (!currentPuzzle) {
        status.textContent = "Please select a puzzle first.";
        return;
    }

    try {

        status.textContent = "Calculating solution...";

        const result =
            await solvePuzzle(
                currentPuzzle,
                currentState,
                "astar"
            );

        algorithm.textContent =
            result.algorithm ?? "-";

        steps.textContent =
            result.steps ?? "-";

        time.textContent =
            result.time ?? "-";

        setSolution(result.solution);

        status.textContent =
            "Solution ready. Use playback.";

    } catch (error) {

        status.textContent =
            "Backend: " + error.message;
    }
});


// ============================================================
// Backend connection test
// ============================================================

async function checkBackend() {

    try {

        const result = await getStatus();

        console.log(
            "Backend:",
            result.status
        );

    } catch (error) {

        status.textContent =
            "Backend is not running.";

        console.error(error);
    }
}


checkBackend();