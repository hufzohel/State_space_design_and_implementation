
import random

from backend.puzzles.pipes.generator import PuzzleGenerator
from backend.puzzles.pipes.problem import PipesProblem
from backend.search.astar import astar


def test_generator():
    random.seed(42)
    generator = PuzzleGenerator()

    # Small boards keep solver tests inexpensive.
    cases = [
        (2, 2, "tree"),
        (2, 2, "tile"),
        (2, 3, "tree"),
        (2, 3, "tile"),
    ]

    for rows, cols, method in cases:
        print(f"\nTesting {method} generator on {rows}x{cols}...")

        puzzle, solution = generator.generate_puzzle(
            rows, cols, method=method
        )

        # 1. Dimensions
        assert len(puzzle) == rows
        assert len(solution) == rows
        assert all(len(row) == cols for row in puzzle)
        assert all(len(row) == cols for row in solution)

        # 2. The generated solution must satisfy the real goal test.
        solution_problem = PipesProblem(solution)
        assert solution_problem.is_goal(solution_problem.initial_state), (
            f"{method}: generated solution is not a valid goal"
        )

        # 3. A nontrivial board should be scrambled.
        if rows * cols > 1:
            assert puzzle != solution, (
                f"{method}: puzzle was not scrambled"
            )

        # 4. Solve from the scrambled puzzle alone.
        problem = PipesProblem(puzzle)
        result = astar(problem)

        assert result.found, (
            f"{method}: A* failed; status={result.status}"
        )
        assert problem.is_goal(result.states[-1]), (
            f"{method}: final search state is not a goal"
        )
        assert result.cost == len(result.actions), (
            "Expected unit-cost actions"
        )

        print("  Solution is valid.")
        print(f"  Actions: {len(result.actions)}")
        print(f"  Expanded: {result.expanded}")
        print(f"  Status: {result.status}")

    print("\nPASS: All generator tests passed.")


if __name__ == "__main__":
    test_generator()
