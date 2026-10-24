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
    getCurrentStep,
    getCurrentState,
    getTotalSteps,
    hasSolution,
    isPlaying,
    nextStep,
    previousStep,
    play,
    pause
} from "./playback.js";


let currentPuzzle = null;
let currentPuzzleId = null;
let currentState = null;
let generationRequestId = 0;
let solveRequestId = 0;
let playbackLocked = false;


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
const previousStepButton = document.getElementById("previous-step-button");
const nextStepButton = document.getElementById("next-step-button");
const playButton = document.getElementById("play-button");
const pauseButton = document.getElementById("pause-button");
const playbackStep = document.getElementById("playback-step");


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
    resetPuzzleData();

    puzzleName.textContent =
        puzzle === "pipes"
            ? "Pipes"
            : "Minesweeper";

    status.textContent =
        "Puzzle selected. Generate a puzzle.";
}


function resetPuzzleData() {
    generationRequestId++;
    solveRequestId++;
    currentPuzzleId = null;
    currentState = null;
    playbackLocked = false;
    solveInstantlyButton.disabled = false;
    solveStepButton.disabled = false;

    setSolution([]);
    updatePlaybackControls();
    renderBoard(null, handleCellClick);

    algorithm.textContent = "-";
    steps.textContent = "-";
    time.textContent = "-";
}


function setSolving(isSolving) {
    playbackLocked = isSolving;
    solveInstantlyButton.disabled = isSolving;
    solveStepButton.disabled = isSolving;
    updatePlaybackControls();
}


function updatePlaybackControls() {
    const solutionAvailable = hasSolution();
    const currentStep = getCurrentStep();
    const totalSteps = getTotalSteps();
    const autoPlaying = isPlaying();

    playbackStep.textContent = solutionAvailable
        ? `Step ${currentStep} / ${totalSteps}`
        : "Step - / -";

    previousStepButton.disabled =
        playbackLocked
        || autoPlaying
        || !solutionAvailable
        || currentStep === 0;

    nextStepButton.disabled =
        playbackLocked
        || autoPlaying
        || !solutionAvailable
        || currentStep === totalSteps;

    playButton.disabled =
        playbackLocked
        || autoPlaying
        || !solutionAvailable
        || currentStep === totalSteps;

    pauseButton.disabled =
        playbackLocked
        || !autoPlaying;

    solveInstantlyButton.disabled =
        playbackLocked
        || autoPlaying;

    solveStepButton.disabled =
        playbackLocked
        || autoPlaying;
}


function showPlaybackState(state, step, totalSteps) {
    currentState = state;
    renderBoard(state, handleCellClick);
    playbackStep.textContent = `Step ${step} / ${totalSteps}`;
}


function statesAreEqual(firstState, secondState) {
    return JSON.stringify(firstState) === JSON.stringify(secondState);
}


// ============================================================
// Generate puzzle
// ============================================================

newPuzzleButton.addEventListener("click", async () => {

    if (!currentPuzzle) {
        status.textContent = "Please select a puzzle first.";
        return;
    }

    resetPuzzleData();
    const requestId = generationRequestId;
    const requestedPuzzle = currentPuzzle;

    try {
        status.textContent = "Generating puzzle...";

        const result =
            await generatePuzzle(requestedPuzzle);

        if (
            requestId !== generationRequestId
            || requestedPuzzle !== currentPuzzle
        ) {
            return;
        }

        currentPuzzleId = result.puzzle_id;
        currentState = result.state;

        renderBoard(
            result.state,
            handleCellClick
        );

        status.textContent = "Puzzle generated.";

    } catch (error) {

        if (requestId !== generationRequestId) {
            return;
        }

        status.textContent =
            "Could not generate puzzle: " + error.message;
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

    if (!currentPuzzleId) {
        status.textContent = "Please generate a puzzle first.";
        return;
    }

    if (currentPuzzle !== "pipes") {
        status.textContent =
            "Solve Instantly is currently available for Pipes only.";
        return;
    }

    const requestId = ++solveRequestId;
    const requestedPuzzle = currentPuzzle;
    const requestedPuzzleId = currentPuzzleId;
    setSolving(true);

    try {
        status.textContent = "Solving...";

        const result =
            await solvePuzzle(
                requestedPuzzle,
                requestedPuzzleId,
                "dfs"
            );

        if (
            requestId !== solveRequestId
            || requestedPuzzle !== currentPuzzle
            || requestedPuzzleId !== currentPuzzleId
        ) {
            return;
        }

        algorithm.textContent =
            result.algorithm ?? "-";

        steps.textContent =
            result.steps ?? "-";

        time.textContent =
            typeof result.execution_time_seconds === "number"
                ? `${(result.execution_time_seconds * 1000).toFixed(3)} ms`
                : "-";

        if (!result.solution_found) {
            setSolution([]);
            updatePlaybackControls();
            status.textContent = "No solution found.";
            return;
        }

        const finalState =
            result.states[result.states.length - 1];

        setSolution(result.states, result.states.length - 1);
        currentState = finalState;
        renderBoard(finalState, handleCellClick);
        updatePlaybackControls();

        status.textContent = "Solved.";

    } catch (error) {

        if (requestId !== solveRequestId) {
            return;
        }

        status.textContent =
            "Could not solve puzzle: " + error.message;

    } finally {

        if (requestId === solveRequestId) {
            setSolving(false);
        }
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

    if (!currentPuzzleId) {
        status.textContent = "Please generate a puzzle first.";
        return;
    }

    if (currentPuzzle !== "pipes") {
        status.textContent =
            "Step-by-step solving is currently available for Pipes only.";
        return;
    }

    const requestId = ++solveRequestId;
    const requestedPuzzle = currentPuzzle;
    const requestedPuzzleId = currentPuzzleId;
    setSolving(true);

    try {
        status.textContent = "Calculating solution...";

        const result =
            await solvePuzzle(
                requestedPuzzle,
                requestedPuzzleId,
                "dfs"
            );

        if (
            requestId !== solveRequestId
            || requestedPuzzle !== currentPuzzle
            || requestedPuzzleId !== currentPuzzleId
        ) {
            return;
        }

        algorithm.textContent =
            result.algorithm ?? "-";

        steps.textContent =
            result.steps ?? "-";

        time.textContent =
            typeof result.execution_time_seconds === "number"
                ? `${(result.execution_time_seconds * 1000).toFixed(3)} ms`
                : "-";

        if (!result.solution_found) {
            setSolution([]);
            updatePlaybackControls();
            status.textContent = "No solution found.";
            return;
        }

        const finalStep = result.states.length - 1;
        const startStep = statesAreEqual(
            currentState,
            result.states[finalStep]
        )
            ? finalStep
            : 0;

        setSolution(result.states, startStep);
        showPlaybackState(
            getCurrentState(),
            getCurrentStep(),
            getTotalSteps()
        );
        updatePlaybackControls();

        status.textContent = startStep === finalStep
            ? "Solution ready. Use Previous to review it."
            : "Solution ready. Use Next and Previous.";

    } catch (error) {

        if (requestId !== solveRequestId) {
            return;
        }

        status.textContent =
            "Could not calculate solution: " + error.message;

    } finally {

        if (requestId === solveRequestId) {
            setSolving(false);
        }
    }
});


nextStepButton.addEventListener("click", () => {
    nextStep(showPlaybackState);
    updatePlaybackControls();
});


previousStepButton.addEventListener("click", () => {
    previousStep(showPlaybackState);
    updatePlaybackControls();
});


playButton.addEventListener("click", async () => {
    const playbackPromise = play(
        (state, step, totalSteps) => {
            showPlaybackState(state, step, totalSteps);
            updatePlaybackControls();
        }
    );

    updatePlaybackControls();
    status.textContent = "Playing solution...";

    const reachedEnd = await playbackPromise;
    updatePlaybackControls();

    if (reachedEnd) {
        status.textContent = "Playback complete.";
    }
});


pauseButton.addEventListener("click", () => {
    if (pause()) {
        status.textContent = "Playback paused.";
    }

    updatePlaybackControls();
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
