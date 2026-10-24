import {
    getStatus,
    generatePuzzle,
    solvePuzzle,
    rotatePipes
} from "./api.js";

import { renderBoard } from "./renderer.js";

import {
    setSolution,
    getCurrentStep,
    getCurrentState,
    getTotalSteps,
    hasSolution,
    isPlaying,
    nextStep,
    previousStep,
    goToStep,
    branchHistory,
    play,
    pause
} from "./playback.js";


let currentPuzzle = null;
let currentPuzzleId = null;
let currentState = null;
let currentPlaybackStates = [];
let currentPlaybackActions = [];
let goalStep = null;
let generationRequestId = 0;
let solveRequestId = 0;
let humanActionRequestId = 0;
let playbackLocked = false;
let humanStartedAt = null;
let selectedHistoryButton = null;


// ============================================================
// Elements
// ============================================================

const puzzleName = document.getElementById("puzzle-name");
const puzzleState = document.getElementById("puzzle-state");
const status = document.getElementById("status");
const algorithm = document.getElementById("algorithm");
const steps = document.getElementById("steps");
const generationTime = document.getElementById("generation-time");
const solverTime = document.getElementById("time");
const expandedNodes = document.getElementById("expanded-nodes");
const generatorSelect = document.getElementById("generator-select");
const solverSelect = document.getElementById("solver-select");
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
const moveHistory = document.getElementById("move-history");


// ============================================================
// Shared state and controls
// ============================================================

function formatMilliseconds(seconds) {
    return typeof seconds === "number"
        ? `${(seconds * 1000).toFixed(3)} ms`
        : "-";
}


function isHumanMode() {
    return currentPuzzle === "pipes" && solverSelect.value === "human";
}


function isCurrentStateSolved() {
    return goalStep !== null && getCurrentStep() === goalStep;
}


function renderCurrentBoard() {
    renderBoard(currentState, handleCellClick, {
        puzzleType: currentPuzzle ?? "pipes",
        interactive: Boolean(
            currentState
            && currentPuzzleId
            && isHumanMode()
            && !playbackLocked
            && !isPlaying()
        ),
        solved: isCurrentStateSolved()
    });
}


function updatePuzzleState() {
    if (!currentState) {
        puzzleState.textContent = "State: -";
    } else if (isCurrentStateSolved()) {
        puzzleState.textContent = "State: solved";
    } else if (currentPuzzle === "minesweeper") {
        puzzleState.textContent = "State: generated (solver unavailable)";
    } else if (isHumanMode()) {
        puzzleState.textContent = "State: human solution in progress";
    } else {
        puzzleState.textContent = "State: unsolved / reviewing solution";
    }
}


function updatePlaybackControls() {
    const solutionAvailable = hasSolution();
    const currentStep = getCurrentStep();
    const totalSteps = getTotalSteps();
    const autoPlaying = isPlaying();
    const dfsAvailable = Boolean(
        currentPuzzle === "pipes"
        && currentPuzzleId
        && solverSelect.value === "dfs"
    );

    playbackStep.textContent = solutionAvailable
        ? `Step ${currentStep} / ${totalSteps}`
        : "Step - / -";

    previousStepButton.disabled =
        playbackLocked || autoPlaying || !solutionAvailable || currentStep === 0;
    nextStepButton.disabled =
        playbackLocked || autoPlaying || !solutionAvailable || currentStep === totalSteps;
    playButton.disabled =
        playbackLocked || autoPlaying || !solutionAvailable || currentStep === totalSteps;
    pauseButton.disabled = playbackLocked || !autoPlaying;
    solveInstantlyButton.disabled = playbackLocked || autoPlaying || !dfsAvailable;
    solveStepButton.disabled = playbackLocked || autoPlaying || !dfsAvailable;
    newPuzzleButton.disabled = playbackLocked;
    generatorSelect.disabled = playbackLocked || currentPuzzle !== "pipes";
    solverSelect.disabled = playbackLocked || currentPuzzle !== "pipes";

    moveHistory.classList.toggle("is-locked", playbackLocked || autoPlaying);
    updateMoveHistorySelection();
    updatePuzzleState();
}


function setBusy(isBusy) {
    playbackLocked = isBusy;
    updatePlaybackControls();
    renderCurrentBoard();
}


function resetPuzzleData() {
    generationRequestId++;
    solveRequestId++;
    humanActionRequestId++;
    pause();
    currentPuzzleId = null;
    currentState = null;
    currentPlaybackStates = [];
    currentPlaybackActions = [];
    goalStep = null;
    humanStartedAt = null;
    playbackLocked = false;
    setSolution([]);
    clearMoveHistory();
    algorithm.textContent = "-";
    steps.textContent = "-";
    generationTime.textContent = "-";
    solverTime.textContent = "-";
    expandedNodes.textContent = "-";
    renderCurrentBoard();
    updatePlaybackControls();
}


function showPlaybackState(state, step, totalSteps) {
    currentState = state;
    renderCurrentBoard();
    playbackStep.textContent = `Step ${step} / ${totalSteps}`;
    updatePuzzleState();
}


function statesAreEqual(firstState, secondState) {
    return JSON.stringify(firstState) === JSON.stringify(secondState);
}


// ============================================================
// Puzzle selection and generation
// ============================================================

pipesButton.addEventListener("click", () => selectPuzzle("pipes"));
minesweeperButton.addEventListener("click", () => selectPuzzle("minesweeper"));


function selectPuzzle(puzzle) {
    currentPuzzle = puzzle;
    resetPuzzleData();
    puzzleName.textContent = puzzle === "pipes" ? "Pipes" : "Minesweeper";
    status.textContent = puzzle === "pipes"
        ? "Puzzle selected. Generate a puzzle."
        : "Minesweeper generation is available; its solver is not ready.";
    updatePlaybackControls();
}


newPuzzleButton.addEventListener("click", async () => {
    if (!currentPuzzle) {
        status.textContent = "Please select a puzzle first.";
        return;
    }

    resetPuzzleData();
    const requestId = generationRequestId;
    const requestedPuzzle = currentPuzzle;
    setBusy(true);

    try {
        status.textContent = "Generating puzzle...";
        const options = requestedPuzzle === "pipes"
            ? { rows: 2, cols: 2, generator: generatorSelect.value }
            : { rows: 5, cols: 5, mine_count: 3 };
        const result = await generatePuzzle(requestedPuzzle, options);

        if (requestId !== generationRequestId || requestedPuzzle !== currentPuzzle) {
            return;
        }

        currentPuzzleId = result.puzzle_id;
        currentState = result.state;
        generationTime.textContent = formatMilliseconds(
            result.generation_time_seconds
        );

        if (isHumanMode()) {
            currentPlaybackStates = [currentState];
            setSolution(currentPlaybackStates);
            renderMoveHistory([], 1);
        }

        status.textContent = requestedPuzzle === "pipes"
            ? `Puzzle generated with the ${result.generator} generator.`
            : "Minesweeper generated. Its hidden mine map remains on the backend.";
    } catch (error) {
        if (requestId === generationRequestId) {
            status.textContent = "Could not generate puzzle: " + error.message;
        }
    } finally {
        if (requestId === generationRequestId) {
            setBusy(false);
        }
    }
});


// ============================================================
// Move history
// ============================================================

function clearMoveHistory() {
    moveHistory.innerHTML = "";
    selectedHistoryButton = null;
}


function describeAction(action, step) {
    if (!action) {
        return `Step ${step}: unknown action`;
    }

    if (Number.isInteger(action.tile_index) && Number.isInteger(action.turns)) {
        const columnCount = currentPlaybackStates[0]?.[0]?.length ?? 1;
        const row = Math.floor(action.tile_index / columnCount) + 1;
        const column = action.tile_index % columnCount + 1;
        const suffix = action.turns === 1 ? "quarter-turn" : "quarter-turns";
        return `Step ${step}: rotate row ${row}, column ${column} — ${action.turns} ${suffix}`;
    }

    return `Step ${step}: action`;
}


function renderMoveHistory(actions, stateCount) {
    clearMoveHistory();

    for (let step = 0; step < stateCount; step++) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.className = "history-step";
        button.dataset.step = step;
        button.textContent = step === 0
            ? "Step 0: Initial State"
            : describeAction(actions[step - 1], step);

        button.addEventListener("click", () => {
            if (playbackLocked || isPlaying()) {
                return;
            }
            if (goToStep(step, showPlaybackState)) {
                updatePlaybackControls();
                status.textContent = `Viewing step ${step}.`;
            }
        });

        item.appendChild(button);
        moveHistory.appendChild(item);
    }

    updateMoveHistorySelection();
}


function updateMoveHistorySelection() {
    const currentButton = moveHistory.querySelector(
        `[data-step="${getCurrentStep()}"]`
    );

    if (currentButton === selectedHistoryButton) {
        return;
    }
    if (selectedHistoryButton) {
        selectedHistoryButton.classList.remove("selected");
        selectedHistoryButton.removeAttribute("aria-current");
    }
    selectedHistoryButton = currentButton;
    if (selectedHistoryButton) {
        selectedHistoryButton.classList.add("selected");
        selectedHistoryButton.setAttribute("aria-current", "step");
        selectedHistoryButton.scrollIntoView({ block: "nearest" });
    }
}


// ============================================================
// Human Pipes mode
// ============================================================

solverSelect.addEventListener("change", () => {
    if (isHumanMode() && currentState && !hasSolution()) {
        currentPlaybackStates = [currentState];
        currentPlaybackActions = [];
        setSolution(currentPlaybackStates);
        renderMoveHistory([], 1);
    }
    renderCurrentBoard();
    updatePlaybackControls();
    status.textContent = isHumanMode()
        ? "Human mode selected. Click a pipe to rotate it."
        : "DFS selected. The current puzzle has been preserved.";
});


async function handleCellClick(row, col) {
    if (!isHumanMode() || !currentPuzzleId || playbackLocked || isPlaying()) {
        return;
    }

    const requestId = ++humanActionRequestId;
    const requestedPuzzleId = currentPuzzleId;
    const columnCount = currentState[0].length;
    const tileIndex = row * columnCount + col;
    const stateBeforeAction = currentState;

    if (humanStartedAt === null) {
        humanStartedAt = performance.now();
    }
    setBusy(true);
    status.textContent = "Checking rotation with the backend...";

    try {
        const result = await rotatePipes(
            requestedPuzzleId,
            stateBeforeAction,
            tileIndex
        );

        if (
            requestId !== humanActionRequestId
            || requestedPuzzleId !== currentPuzzleId
            || currentPuzzle !== "pipes"
        ) {
            return;
        }

        const branchStep = hasSolution() ? getCurrentStep() : 0;
        const history = branchHistory(
            hasSolution() ? currentPlaybackStates : [stateBeforeAction],
            hasSolution() ? currentPlaybackActions : [],
            branchStep,
            result.state,
            result.action
        );
        currentPlaybackStates = history.states;
        currentPlaybackActions = history.actions;
        goalStep = result.is_goal ? currentPlaybackStates.length - 1 : null;
        setSolution(currentPlaybackStates, currentPlaybackStates.length - 1);
        currentState = result.state;
        renderMoveHistory(currentPlaybackActions, currentPlaybackStates.length);

        algorithm.textContent = "human";
        steps.textContent = currentPlaybackActions.length;
        solverTime.textContent = `${(performance.now() - humanStartedAt).toFixed(1)} ms`;
        expandedNodes.textContent = "not applicable";
        status.textContent = result.is_goal
            ? "Solved in Human mode."
            : "Pipe rotated. Continue solving.";
    } catch (error) {
        if (requestId === humanActionRequestId) {
            status.textContent = "Could not rotate pipe: " + error.message;
        }
    } finally {
        if (requestId === humanActionRequestId) {
            setBusy(false);
        }
    }
}


// ============================================================
// DFS solving
// ============================================================

function validateSolveRequest() {
    if (!currentPuzzle) {
        status.textContent = "Please select a puzzle first.";
        return false;
    }
    if (!currentPuzzleId) {
        status.textContent = "Please generate a puzzle first.";
        return false;
    }
    if (currentPuzzle !== "pipes" || solverSelect.value !== "dfs") {
        status.textContent = "DFS solving is currently available for Pipes only.";
        return false;
    }
    return true;
}


function applySolveStatistics(result) {
    algorithm.textContent = result.algorithm ?? "-";
    steps.textContent = result.steps ?? "-";
    solverTime.textContent = formatMilliseconds(result.execution_time_seconds);
    expandedNodes.textContent = result.expanded_nodes ?? "not available";
}


async function runDfs(startAtFinalState) {
    if (!validateSolveRequest()) {
        return;
    }

    const requestId = ++solveRequestId;
    const requestedPuzzle = currentPuzzle;
    const requestedPuzzleId = currentPuzzleId;
    const requestedState = currentState;
    setBusy(true);
    status.textContent = startAtFinalState ? "Solving..." : "Calculating solution...";

    try {
        const result = await solvePuzzle(
            requestedPuzzle,
            requestedPuzzleId,
            "dfs",
            requestedState
        );

        if (
            requestId !== solveRequestId
            || requestedPuzzle !== currentPuzzle
            || requestedPuzzleId !== currentPuzzleId
        ) {
            return;
        }

        applySolveStatistics(result);
        if (!result.solution_found) {
            currentPlaybackStates = [];
            currentPlaybackActions = [];
            goalStep = null;
            setSolution([]);
            clearMoveHistory();
            status.textContent = "No solution found.";
            return;
        }

        currentPlaybackStates = result.states;
        currentPlaybackActions = result.actions;
        goalStep = result.states.length - 1;
        let initialStep = startAtFinalState ? goalStep : 0;
        if (!startAtFinalState && statesAreEqual(currentState, result.states[goalStep])) {
            initialStep = goalStep;
        }
        setSolution(currentPlaybackStates, initialStep);
        renderMoveHistory(currentPlaybackActions, currentPlaybackStates.length);
        showPlaybackState(getCurrentState(), getCurrentStep(), getTotalSteps());
        status.textContent = initialStep === goalStep
            ? "Solved. Use Previous to review the path."
            : "Solution ready. Use Next, Previous, or Play.";
    } catch (error) {
        if (requestId === solveRequestId) {
            status.textContent = "Could not solve puzzle: " + error.message;
        }
    } finally {
        if (requestId === solveRequestId) {
            setBusy(false);
        }
    }
}


solveInstantlyButton.addEventListener("click", () => runDfs(true));
solveStepButton.addEventListener("click", () => runDfs(false));


// ============================================================
// Playback
// ============================================================

nextStepButton.addEventListener("click", () => {
    nextStep(showPlaybackState);
    updatePlaybackControls();
});

previousStepButton.addEventListener("click", () => {
    previousStep(showPlaybackState);
    updatePlaybackControls();
});

playButton.addEventListener("click", async () => {
    const playbackPromise = play((state, step, totalSteps) => {
        showPlaybackState(state, step, totalSteps);
        updatePlaybackControls();
    });
    updatePlaybackControls();
    renderCurrentBoard();
    status.textContent = "Playing solution...";
    const reachedEnd = await playbackPromise;
    updatePlaybackControls();
    renderCurrentBoard();
    if (reachedEnd) {
        status.textContent = "Playback complete.";
    }
});

pauseButton.addEventListener("click", () => {
    if (pause()) {
        status.textContent = "Playback paused.";
    }
    updatePlaybackControls();
    renderCurrentBoard();
});


// ============================================================
// Backend connection test
// ============================================================

async function checkBackend() {
    try {
        const result = await getStatus();
        console.log("Backend:", result.status);
    } catch (error) {
        status.textContent = "Backend is not running.";
        console.error(error);
    }
}


updatePlaybackControls();
checkBackend();
