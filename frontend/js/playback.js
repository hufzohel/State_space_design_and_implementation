let solution = [];
let currentStep = 0;
let playing = false;


export function setSolution(newSolution) {
    solution = newSolution || [];
    currentStep = 0;
}


export function getCurrentStep() {
    return currentStep;
}


export function nextStep(callback) {
    if (currentStep >= solution.length) {
        return;
    }

    const action = solution[currentStep];

    currentStep++;

    callback(action);
}


export function previousStep(callback) {
    if (currentStep <= 0) {
        return;
    }

    currentStep--;

    const action = solution[currentStep];

    callback(action);
}


export async function play(callback, delay = 500) {
    if (playing) {
        return;
    }

    playing = true;

    while (playing && currentStep < solution.length) {
        const action = solution[currentStep];

        currentStep++;

        callback(action);

        await new Promise(resolve => setTimeout(resolve, delay));
    }

    playing = false;
}


export function pause() {
    playing = false;
}