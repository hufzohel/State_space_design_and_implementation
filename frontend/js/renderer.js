const boardElement = document.getElementById("board");

const PIPE_DIRECTIONS = [
    { bit: 8, name: "up", opposite: 2, row: -1, col: 0 },
    { bit: 4, name: "right", opposite: 1, row: 0, col: 1 },
    { bit: 2, name: "down", opposite: 8, row: 1, col: 0 },
    { bit: 1, name: "left", opposite: 4, row: 0, col: -1 }
];


export function clearBoard() {
    boardElement.innerHTML = "";
    boardElement.style.removeProperty("grid-template-columns");
    boardElement.className = "";
}


export function renderBoard(
    board,
    onCellClick,
    options = {}
) {
    clearBoard();

    if (!board) {
        return;
    }

    const columnCount = board[0]?.length ?? 0;

    if (columnCount === 0) {
        return;
    }

    boardElement.style.gridTemplateColumns =
        `repeat(${columnCount}, 50px)`;

    const puzzleType = options.puzzleType ?? "pipes";
    const interactive = options.interactive ?? false;
    const loopCells = puzzleType === "pipes"
        ? findLoopCells(board)
        : new Set();

    boardElement.classList.add(`${puzzleType}-board`);
    boardElement.classList.toggle("solved", options.solved ?? false);
    boardElement.classList.toggle("interactive", interactive);

    for (let row = 0; row < board.length; row++) {
        for (let col = 0; col < board[row].length; col++) {
            const cell = document.createElement("button");
            cell.className = "cell";
            cell.type = "button";

            if (puzzleType === "pipes") {
                renderPipeCell(
                    cell,
                    board,
                    row,
                    col,
                    loopCells.has(row * columnCount + col)
                );
            } else {
                renderMinesweeperCell(cell, board[row][col]);
            }

            if (interactive && onCellClick) {
                cell.addEventListener("click", () => {
                    onCellClick(row, col);
                });
            } else {
                cell.tabIndex = -1;
                cell.setAttribute("aria-disabled", "true");
            }

            boardElement.appendChild(cell);
        }
    }
}


function renderPipeCell(cell, board, row, col, isPartOfLoop) {
    const mask = board[row][col];
    const directionNames = [];

    cell.classList.add("pipe-cell");
    cell.classList.toggle("loop", isPartOfLoop);
    cell.dataset.mask = mask;

    const center = document.createElement("span");
    center.className = "pipe-center";
    cell.appendChild(center);

    for (const direction of PIPE_DIRECTIONS) {
        if (!(mask & direction.bit)) {
            continue;
        }

        directionNames.push(direction.name);

        const arm = document.createElement("span");
        arm.className = `pipe-arm pipe-${direction.name}`;
        cell.appendChild(arm);

        if (!hasReciprocalConnection(board, row, col, direction)) {
            cell.classList.add("invalid");
        }
    }

    const description = directionNames.length > 0
        ? directionNames.join(", ")
        : "no connections";

    cell.title = `Pipe: ${description} (mask ${mask})`;
    cell.setAttribute("aria-label", cell.title);
}


function findLoopCells(board) {
    const rows = board.length;
    const cols = board[0]?.length ?? 0;
    const visited = new Set();
    const parents = new Map();
    const depths = new Map();
    const loopCells = new Set();

    function visit(index, parent) {
        visited.add(index);
        parents.set(index, parent);
        depths.set(index, parent === null ? 0 : depths.get(parent) + 1);
        const row = Math.floor(index / cols);
        const col = index % cols;

        for (const direction of PIPE_DIRECTIONS) {
            if (!(board[row][col] & direction.bit)) {
                continue;
            }

            const neighborRow = row + direction.row;
            const neighborCol = col + direction.col;
            if (
                neighborRow < 0
                || neighborRow >= rows
                || neighborCol < 0
                || neighborCol >= cols
                || !(board[neighborRow][neighborCol] & direction.opposite)
            ) {
                continue;
            }

            const neighbor = neighborRow * cols + neighborCol;
            if (neighbor === parent) {
                continue;
            }
            if (!visited.has(neighbor)) {
                visit(neighbor, index);
            } else if (depths.get(neighbor) < depths.get(index)) {
                let current = index;
                loopCells.add(neighbor);
                loopCells.add(current);
                while (current !== neighbor && current !== null) {
                    current = parents.get(current) ?? null;
                    if (current !== null) {
                        loopCells.add(current);
                    }
                }
            }
        }
    }

    for (let index = 0; index < rows * cols; index++) {
        if (!visited.has(index)) {
            visit(index, null);
        }
    }

    return loopCells;
}


function hasReciprocalConnection(board, row, col, direction) {
    const neighborRow = row + direction.row;
    const neighborCol = col + direction.col;

    if (
        neighborRow < 0
        || neighborRow >= board.length
        || neighborCol < 0
        || neighborCol >= board[neighborRow].length
    ) {
        return false;
    }

    return Boolean(
        board[neighborRow][neighborCol] & direction.opposite
    );
}


function renderMinesweeperCell(cell, value) {
    cell.classList.add("minesweeper-cell");

    if (value === -1) {
        cell.classList.add("unknown");
        cell.textContent = "";
        cell.setAttribute("aria-label", "Unknown cell");
    } else if (value === -2) {
        cell.classList.add("flagged");
        cell.textContent = "\u2691";
        cell.setAttribute("aria-label", "Flagged cell");
    } else {
        cell.classList.add("revealed");
        cell.textContent = value === 0 ? "" : value;
        cell.setAttribute("aria-label", `Revealed ${value}`);
    }
}
