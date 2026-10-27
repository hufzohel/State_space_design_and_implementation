
from backend.puzzles.minesweeper.environment import (
    MinesweeperEnvironment,
    MinesweeperState,
)
from backend.puzzles.minesweeper.problem import MinesweeperProblem
from backend.puzzles.minesweeper.state import UNKNOWN
from backend.search.greedy import GreedySolver


ROWS = 2
COLS = 2
MINES = {0}

# Same puzzle as the blind-search test:
#
#   M  1
#   1  1
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

    solver = GreedySolver(problem, environment)
    result = solver.solve()

    print("Initial visible board:", initial_state.cells)
    print("\n========== ACTIONS ==========")

    for index, action in enumerate(result.actions, start=1):
        print(f"Step {index}: {action}")
        print("Visible board:", result.states[index].cells)

    final_state = result.states[-1]
    won = environment.is_win(final_state)

    print("\n========== RESULTS ==========")
    print("Actions taken:", len(result.actions))
    print("Expanded nodes:", result.expanded_nodes)
    print(f"Elapsed time: {result.elapsed_seconds:.6f} seconds")
    print("Final visible board:", final_state.cells)
    print("Lost:", final_state.lost)
    print("Status:", result.status)
    print("Won:", won)

    if won:
        print("SUCCESS: Greedy completed the puzzle.")
    else:
        print("FAILED: Greedy did not complete the puzzle.")


if __name__ == "__main__":
    main()
