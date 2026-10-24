const boardElement = document.getElementById("board");


export function clearBoard() {
    boardElement.innerHTML = "";
    boardElement.style.removeProperty("grid-template-columns");
}


export function renderBoard(board, onCellClick) {
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

    for (let row = 0; row < board.length; row++) {
        for (let col = 0; col < board[row].length; col++) {

            const cell = document.createElement("button");

            cell.className = "cell";

            cell.textContent = board[row][col];

            cell.addEventListener("click", () => {
                onCellClick(row, col);
            });

            boardElement.appendChild(cell);
        }
    }
}
