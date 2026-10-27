
from backend.puzzles.pipes.problem import PipesProblem
from backend.puzzles.pipes.state import rotate_mask
from backend.search.astar import astar


def main():
    # A valid solved 2x2 tree.
    solved_puzzle = [
        [4, 3],
        [4, 9],
    ]

    solved_problem = PipesProblem(solved_puzzle)
    assert solved_problem.is_goal(solved_problem.initial_state)

    # Scramble exactly one tile: RIGHT (4) -> DOWN (2).
    scrambled_puzzle = [
        [rotate_mask(4, 1), 3],
        [4, 9],
    ]

    problem = PipesProblem(scrambled_puzzle)

    print("Initial state:", problem.initial_state)
    print("Initial is goal:", problem.is_goal(problem.initial_state))

    result = astar(problem)

    if result is None:
        print("FAIL: No solution found.")
        return

    print("\nActions:", result.actions)
    print("Number of actions:", len(result.actions))
    print("Expanded nodes:", result.expanded)
    print("Solution cost:", result.cost)
    print("Status:", result.status)

    print("\nPath:")
    for i, state in enumerate(result.states):
        print(f"State {i}: {state}")

    assert len(result.actions) == 1, "Expected a one-action solution."
    assert problem.is_goal(result.states[-1]), "Final state is not a goal."

    print("\nPASS: Found a one-action solution ending at a goal state.")


if __name__ == "__main__":
    main()
