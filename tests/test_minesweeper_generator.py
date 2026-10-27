from time import perf_counter

from backend.puzzles.minesweeper.generator import MinesweeperGenerator
from backend.puzzles.minesweeper.environment import (
    MinesweeperEnvironment,
    MinesweeperState as EnvironmentState,
)
from backend.puzzles.minesweeper.problem import (
    MinesweeperProblem,
    MinesweeperState as ProblemState,
)
from backend.search.onlineDFS import OnlineBlindSolver
from backend.search.greedy import GreedySolver

from backend.puzzles.minesweeper.Pro_implementation.pro_problem import (
    ProMinesweeperProblem,
)
from backend.puzzles.minesweeper.Pro_implementation.pro_state import (
    SAFE,
    MINE,
)

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

ROWS = 10
COLS = 10
MINE_COUNT = 15
SEED = 42


def format_board(cells, rows, cols):
    """Print a visible board without exposing hidden information."""
    symbols = {
        -1: "?",
        -2: "F",
    }

    for row in range(rows):
        values = []

        for col in range(cols):
            value = cells[row * cols + col]
            values.append(symbols.get(value, str(value)))

        print(" ".join(f"{value:>2}" for value in values))


def create_problem(initial_cells):
    """Create a fresh problem for one solver."""
    initial_state = ProblemState(cells=tuple(initial_cells))

    return MinesweeperProblem(
        rows=ROWS,
        cols=COLS,
        initial_state=initial_state,
    )


def run_blind(problem, environment):
    """Run the online blind solver through the real environment."""
    solver = OnlineBlindSolver(problem, environment)

    state = EnvironmentState(cells=tuple(problem.initial_state.cells))
    actions = []
    states = [state]
    start_time = perf_counter()

    while True:
        if state.lost:
            status = "lost"
            break

        if environment.is_win(state):
            status = "won"
            break

        action = solver.choose_action(state)

        if action is None:
            status = "no_actions"
            break

        new_state = environment.execute(state, action)

        actions.append(action)
        states.append(new_state)
        state = new_state

        # Every valid action either changes an unknown cell
        # or ends the game, so the process should terminate.
        if len(actions) > ROWS * COLS:
            status = "step_limit"
            break

    return {
        "actions": actions,
        "states": states,
        "elapsed_seconds": perf_counter() - start_time,
        "status": status,
        "final_state": state,
    }

def run_pro(initial_cells, environment):
    """Run the constraint-propagation solver through the environment."""
    state = EnvironmentState(cells=tuple(initial_cells))
    actions = []
    states = [state]
    start_time = perf_counter()
    status = "stalled"

    while True:
        if state.lost:
            status = "lost"
            break

        if environment.is_win(state):
            status = "won"
            break

        # Rebuild constraints from the current visible board.
        problem = ProMinesweeperProblem(
            rows=ROWS,
            cols=COLS,
            board=state.cells,
        )

        knowledge = problem.initial_state()

        if knowledge is None:
            status = "contradiction"
            break

        # Apply forced assignments, without inspecting hidden mines.
        pending = [
            (cell, value)
            for cell, value in knowledge.assignments.items()
            if state.cells[cell] == -1
        ]

        if not pending:
            unknown_cells = [
                cell
                for cell, value in enumerate(state.cells)
                if value == -1
            ]

            if not unknown_cells:
                status = "stalled"
                break

            # Deduction is exhausted: make a blind guess.
            import random
            cell = random.choice(unknown_cells)

            from backend.puzzles.minesweeper.action import RevealAction
            action = RevealAction(cell=cell)

            new_state = environment.execute(state, action)

            actions.append(action)
            states.append(new_state)
            state = new_state

            continue

        # Apply one deduction, then rebuild the knowledge base.
        # This avoids applying stale deductions after the board changes.
        cell, value = pending[0]

        if value == SAFE:
            from backend.puzzles.minesweeper.action import RevealAction
            action = RevealAction(cell=cell)
        elif value == MINE:
            from backend.puzzles.minesweeper.action import FlagAction
            action = FlagAction(cell=cell)
        else:
            status = "invalid_assignment"
            break

        new_state = environment.execute(state, action)

        if new_state == state:
            status = "no_progress"
            break

        actions.append(action)
        states.append(new_state)
        state = new_state

        if len(actions) > ROWS * COLS:
            status = "step_limit"
            break

    return {
        "actions": actions,
        "states": states,
        "elapsed_seconds": perf_counter() - start_time,
        "status": status,
        "final_state": state,
    }

def print_results(name, result, environment):
    final_state = result["final_state"]
    won = environment.is_win(final_state)

    print(f"\n========== {name} RESULTS ==========")
    print(f"Actions taken: {len(result['actions'])}")
    print(f"Elapsed time: {result['elapsed_seconds']:.6f} seconds")
    print(f"Final status: {result['status']}")
    print(f"Lost: {final_state.lost}")
    print(f"Won: {won}")
    print("Final visible board:")
    format_board(final_state.cells, ROWS, COLS)


def main():
    # Generate exactly one board.
    generated = MinesweeperGenerator(
        rows=ROWS,
        cols=COLS,
        mine_count=MINE_COUNT,
        seed=SEED,
    ).generate()

    # The generator stores mines as a tuple of booleans.
    # Convert them to indices for the environment.
    mine_positions = {
        cell
        for cell, has_mine in enumerate(generated["mines"])
        if has_mine
    }

    initial_cells = tuple(generated["initial_cells"])

    print("========== GENERATED BOARD ==========")
    print(f"Dimensions: {ROWS} x {COLS}")
    print(f"Mine count: {MINE_COUNT}")
    print(f"Seed: {SEED}")
    print("Initial visible board:")
    format_board(initial_cells, ROWS, COLS)

    # --------------------------------------------------------
    # Run 1: Online blind solver
    # --------------------------------------------------------

    blind_problem = create_problem(initial_cells)
    blind_environment = MinesweeperEnvironment(
        ROWS, COLS, mine_positions
    )

    blind_result = run_blind(
        blind_problem,
        blind_environment,
    )

    print_results(
        "ONLINE BLIND SOLVER",
        blind_result,
        blind_environment,
    )

    # --------------------------------------------------------
    # Run 2: Greedy solver
    # --------------------------------------------------------

    greedy_problem = create_problem(initial_cells)
    greedy_environment = MinesweeperEnvironment(
        ROWS, COLS, mine_positions
    )

    greedy_solver = GreedySolver(
        greedy_problem,
        greedy_environment,
    )

    greedy_start = perf_counter()
    greedy_result = greedy_solver.solve()
    greedy_elapsed = perf_counter() - greedy_start

    greedy_final_state = greedy_result.states[-1]

    greedy_summary = {
        "actions": greedy_result.actions,
        "states": greedy_result.states,
        "elapsed_seconds": greedy_elapsed,
        "status": greedy_result.status,
        "final_state": greedy_final_state,
    }

    print_results(
        "GREEDY SOLVER",
        greedy_summary,
        greedy_environment,
    )
    print(f"Expanded nodes: {greedy_result.expanded_nodes}")

    # --------------------------------------------------------
    # Run 3: Constraint-propagation solver
    # --------------------------------------------------------

    pro_environment = MinesweeperEnvironment(
        ROWS, COLS, mine_positions
    )

    pro_result = run_pro(
        initial_cells,
        pro_environment,
    )

    print_results(
        "CONSTRAINT PROPAGATION SOLVER",
        pro_result,
        pro_environment,
    )
    # --------------------------------------------------------
    # Comparison
    # --------------------------------------------------------

    results = [
        (
            "Online blind",
            blind_result,
            blind_environment,
        ),
        (
            "Greedy",
            greedy_summary,
            greedy_environment,
        ),
        (
            "Constraint propagation",
            pro_result,
            pro_environment,
        ),
    ]

    print("\n========== COMPARISON ==========")
    print(
        f"{'Solver':<26}"
        f"{'Status':<18}"
        f"{'Won':<8}"
        f"{'Actions':<12}"
        f"{'Time (s)':<14}"
    )
    print("-" * 78)

    for name, result, environment in results:
        final_state = result["final_state"]
        won = environment.is_win(final_state)

        print(
            f"{name:<26}"
            f"{result['status']:<18}"
            f"{str(won):<8}"
            f"{len(result['actions']):<12}"
            f"{result['elapsed_seconds']:<14.6f}"
        )

if __name__ == "__main__":
    main()
