
from backend.puzzles.minesweeper.action import FlagAction
from backend.puzzles.minesweeper.environment import (
    MinesweeperEnvironment,
    MinesweeperState,
)
from backend.puzzles.minesweeper.problem import MinesweeperProblem
from backend.puzzles.minesweeper.state import UNKNOWN
from backend.search.onlineDFS import OnlineBlindSolver


ROWS = 2
COLS = 2
MINES = {0}

# Cell layout:
#   0  1
#   2  3
#
# Cell 3 is already revealed with clue 1.
INITIAL_CELLS = (
    UNKNOWN,
    UNKNOWN,
    UNKNOWN,
    1,
)


def main():
    initial_state = MinesweeperState(cells=INITIAL_CELLS)

    # Only the environment knows the actual mine positions.
    environment = MinesweeperEnvironment(
        rows=ROWS,
        cols=COLS,
        mines=MINES,
    )

    problem = MinesweeperProblem(
        rows=ROWS,
        cols=COLS,
        initial_state=initial_state,
    )
    solver = OnlineBlindSolver(problem)

    state = initial_state
    actions_taken = []

    print("Initial visible board:", state.cells)
    print("Starting blind online search...\n")

    max_steps = ROWS * COLS * 2

    for step in range(max_steps):
        if state.lost or environment.is_win(state):
            break

        action = solver.choose_action(state)

        if action is None:
            print("No available actions.")
            break

        print(f"Step {step + 1}: {action}")

        state = environment.execute(state, action)
        actions_taken.append(action)

        print("Visible board:", state.cells)

    won = environment.is_win(state)

    print("\n========== RESULTS ==========")
    print("Actions taken:", len(actions_taken))
    print("Final visible board:", state.cells)
    print("Lost:", state.lost)
    print("Won:", won)

    if won:
        print("SUCCESS: The solver completed the puzzle.")
    else:
        print("FAILED: The solver did not complete the puzzle.")


if __name__ == "__main__":
    main()
