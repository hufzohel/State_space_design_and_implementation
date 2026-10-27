
from time import perf_counter

from backend.puzzles.kakurasu.generator import KakurasuGenerator
from backend.puzzles.kakurasu.problem import KakurasuProblem
from backend.search.dfs import DFSSolver
from backend.search.astar import astar


def print_board(state, rows, cols):
    for r in range(rows):
        row = state.cells[r * cols:(r + 1) * cols]
        print(" ".join(
            "?" if cell == -1 else ("■" if cell == 1 else "·")
            for cell in row
        ))


def main():
    # Generate one puzzle; both algorithms receive the same problem.
    generated = KakurasuGenerator(rows=5, cols=5, seed=42).generate()
    problem = KakurasuProblem.from_generated(generated)

    print("=== Kakurasu: 5x5 ===")
    print("Row targets:   ", problem.row_targets)
    print("Column targets:", problem.col_targets)
    print("\nInitial board:")
    print_board(problem.initial_state, problem.rows, problem.cols)

    # DFS
    print("\n=== DFS ===")
    start = perf_counter()
    dfs_result = DFSSolver(problem).solve()
    dfs_time = perf_counter() - start

    if dfs_result is None:
        print("Status: No solution found")
    else:
        print("Status: Solved")
        print("Actions:", len(dfs_result.actions))
        print("Expanded nodes:", dfs_result.expanded_nodes)
        print(f"Elapsed: {dfs_time:.6f} seconds")
        print("Solution board:")
        print_board(dfs_result.states[-1], problem.rows, problem.cols)

    # A* on the exact same initial puzzle
    print("\n=== A* ===")
    astar_result = astar(problem)

    print("Status:", astar_result.status)
    print("Found:", astar_result.found)
    print("Actions:", len(astar_result.actions))
    print("Cost:", astar_result.cost)
    print("Expanded nodes:", astar_result.expanded)
    print("Generated nodes:", astar_result.generated)
    print(f"Elapsed: {astar_result.elapsed_seconds:.6f} seconds")

    if astar_result.found:
        print("Solution board:")
        print_board(astar_result.states[-1], problem.rows, problem.cols)

    # Validate solutions using the actual problem rules.
    if dfs_result is not None:
        assert problem.is_goal(dfs_result.states[-1])

    if astar_result.found:
        assert problem.is_goal(astar_result.states[-1])

    print("\nSearch tests completed.")


if __name__ == "__main__":
    main()
