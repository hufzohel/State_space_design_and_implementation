from backend.puzzles.kakurasu import (
    KakurasuGenerator,
    KakurasuProblem,
)


def main():
    generated = KakurasuGenerator(
        rows=5,
        cols=5,
        seed=42,
    ).generate()

    problem = KakurasuProblem.from_generated(generated)
    state = problem.initial_state

    print("Row targets:", problem.row_targets)
    print("Column targets:", problem.col_targets)
    print("Initial state:", state)

    actions = problem.actions(state)
    print("Initial actions:", actions)

    assert actions
    next_state = problem.result(state, actions[0])
    assert next_state != state

    # The generated hidden solution must satisfy the generated clues.
    from backend.puzzles.kakurasu import KakurasuState

    hidden = KakurasuState(generated["solution"])
    assert problem.is_goal(hidden)

    print("Basic Kakurasu checks passed.")


if __name__ == "__main__":
    main()