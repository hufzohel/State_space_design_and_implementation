let states = [];
let currentStep = 0;
let playing = false;
let playbackSessionId = 0;
let pendingTimer = null;
let pendingDelayResolve = null;


export function setSolution(newStates, initialStep = 0) {
    pause();
    states = Array.isArray(newStates) ? newStates : [];

    if (states.length === 0) {
        currentStep = 0;
        return;
    }

    currentStep = Math.min(
        Math.max(initialStep, 0),
        states.length - 1
    );
}


export function getCurrentStep() {
    return currentStep;
}


export function getCurrentState() {
    return states[currentStep] ?? null;
}


export function getTotalSteps() {
    return Math.max(states.length - 1, 0);
}


export function hasSolution() {
    return states.length > 0;
}


export function isPlaying() {
    return playing;
}


export function nextStep(callback) {
    if (currentStep >= states.length - 1) {
        return;
    }

    currentStep++;

    callback(
        states[currentStep],
        currentStep,
        getTotalSteps()
    );
}


export function previousStep(callback) {
    if (currentStep <= 0) {
        return;
    }

    currentStep--;

    callback(
        states[currentStep],
        currentStep,
        getTotalSteps()
    );
}


export function goToStep(index, callback) {
    if (
        playing
        || !Number.isInteger(index)
        || index < 0
        || index >= states.length
    ) {
        return false;
    }

    currentStep = index;

    callback(
        states[currentStep],
        currentStep,
        getTotalSteps()
    );

    return true;
}


export function branchHistory(
    historyStates,
    historyActions,
    branchStep,
    nextState,
    nextAction
) {
    if (
        !Array.isArray(historyStates)
        || !Array.isArray(historyActions)
        || !Number.isInteger(branchStep)
        || branchStep < 0
        || branchStep >= historyStates.length
    ) {
        throw new Error("Invalid playback branch.");
    }

    return {
        states: [
            ...historyStates.slice(0, branchStep + 1),
            nextState
        ],
        actions: [
            ...historyActions.slice(0, branchStep),
            nextAction
        ]
    };
}


function waitForDelay(delay) {
    return new Promise(resolve => {
        const timerId = setTimeout(() => {
            if (pendingTimer === timerId) {
                pendingTimer = null;
                pendingDelayResolve = null;
            }

            resolve();
        }, delay);

        pendingTimer = timerId;
        pendingDelayResolve = resolve;
    });
}


export async function play(callback, delay = 500) {
    if (
        playing
        || !hasSolution()
        || currentStep >= getTotalSteps()
    ) {
        return false;
    }

    playing = true;
    const sessionId = ++playbackSessionId;

    while (
        playing
        && sessionId === playbackSessionId
        && currentStep < getTotalSteps()
    ) {
        await waitForDelay(delay);

        if (
            !playing
            || sessionId !== playbackSessionId
        ) {
            return false;
        }

        nextStep(callback);
    }

    if (sessionId === playbackSessionId) {
        playing = false;
    }

    return currentStep === getTotalSteps();
}


export function pause() {
    const wasPlaying = playing;

    playing = false;
    playbackSessionId++;

    if (pendingTimer !== null) {
        clearTimeout(pendingTimer);
        pendingTimer = null;
    }

    if (pendingDelayResolve !== null) {
        const resolve = pendingDelayResolve;
        pendingDelayResolve = null;
        resolve();
    }

    return wasPlaying;
}
