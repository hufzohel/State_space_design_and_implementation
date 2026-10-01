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


export async function generatePuzzle(puzzle) {
    return request(`/${puzzle}/new`, {
        method: "POST"
    });
}


export async function solvePuzzle(puzzle, state, algorithm) {
    return request(`/${puzzle}/solve`, {
        method: "POST",

        body: JSON.stringify({
            state: state,
            algorithm: algorithm
        })
    });
}