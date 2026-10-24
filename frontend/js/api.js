const API_BASE_URL = "http://127.0.0.1:8000/api";


async function request(endpoint, options = {}) {
    const response = await fetch(
        API_BASE_URL + endpoint,
        {
            headers: {
                "Content-Type": "application/json"
            },
            ...options
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Request failed");
    }

    return data;
}


export async function getStatus() {
    return request("/status");
}


export async function generatePuzzle(puzzle, options = {}) {
    return request(`/${puzzle}/new`, {
        method: "POST",
        body: JSON.stringify(options)
    });
}


export async function solvePuzzle(
    puzzle,
    puzzleId,
    algorithm,
    state = null
) {
    return request(`/${puzzle}/solve`, {
        method: "POST",

        body: JSON.stringify({
            puzzle_id: puzzleId,
            algorithm: algorithm,
            state: state
        })
    });
}


export async function rotatePipes(
    puzzleId,
    state,
    tileIndex,
    turns = 1
) {
    return request("/pipes/rotate", {
        method: "POST",

        body: JSON.stringify({
            puzzle_id: puzzleId,
            state: state,
            tile_index: tileIndex,
            turns: turns
        })
    });
}
