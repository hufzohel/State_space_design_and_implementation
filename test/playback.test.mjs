import assert from "node:assert/strict";
import test from "node:test";

import {
    branchHistory,
    getCurrentState,
    getCurrentStep,
    getTotalSteps,
    goToStep,
    isPlaying,
    nextStep,
    pause,
    play,
    previousStep,
    setSolution
} from "../frontend/js/playback.js";


test("manual playback respects both boundaries", () => {
    const states = ["initial", "middle", "goal"];
    const visited = [];
    const record = (state, step) => visited.push([state, step]);

    setSolution(states);
    previousStep(record);
    assert.equal(getCurrentStep(), 0);

    nextStep(record);
    nextStep(record);
    nextStep(record);
    assert.equal(getCurrentStep(), 2);
    assert.equal(getCurrentState(), "goal");
    assert.equal(getTotalSteps(), 2);

    previousStep(record);
    assert.deepEqual(visited, [
        ["middle", 1],
        ["goal", 2],
        ["middle", 1]
    ]);
});


test("goToStep rejects invalid positions", () => {
    setSolution(["initial", "goal"]);
    const callback = () => assert.fail("callback must not run");

    assert.equal(goToStep(-1, callback), false);
    assert.equal(goToStep(2, callback), false);
    assert.equal(goToStep(0.5, callback), false);
    assert.equal(getCurrentStep(), 0);
});


test("branchHistory removes the abandoned branch", () => {
    const oldStates = ["s0", "s1", "old-s2", "old-s3"];
    const oldActions = ["a0", "old-a1", "old-a2"];

    const branch = branchHistory(
        oldStates,
        oldActions,
        1,
        "new-s2",
        "new-a1"
    );

    assert.deepEqual(branch.states, ["s0", "s1", "new-s2"]);
    assert.deepEqual(branch.actions, ["a0", "new-a1"]);
    assert.equal(branch.actions.length, branch.states.length - 1);
    assert.deepEqual(oldStates, ["s0", "s1", "old-s2", "old-s3"]);
});


test("pause cancels the old play session and resume is singular", async () => {
    setSolution(["s0", "s1", "s2", "s3"]);
    const visited = [];
    const callback = (_state, step) => visited.push(step);

    const firstPlay = play(callback, 20);
    await new Promise(resolve => setTimeout(resolve, 25));
    assert.equal(isPlaying(), true);
    assert.equal(pause(), true);
    const pausedStep = getCurrentStep();
    assert.equal(await firstPlay, false);

    await new Promise(resolve => setTimeout(resolve, 30));
    assert.equal(getCurrentStep(), pausedStep);

    const resumed = await play(callback, 5);
    assert.equal(resumed, true);
    assert.equal(getCurrentStep(), 3);
    assert.equal(isPlaying(), false);
    assert.deepEqual(visited, [1, 2, 3]);
});
