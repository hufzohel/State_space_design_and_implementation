import random

from backend.puzzles.minesweeper.generator import MinesweeperGenerator
from backend.puzzles.minesweeper.state import UNKNOWN, FLAGGED, neighbors
from backend.puzzles.minesweeper.Pro_implementation.pro_state import (
    SAFE,
    MINE,
    Constraint,
    KnowledgeState,
)
from backend.search.Minesweeper_pro_solver import ConstraintPropagator


def build_constraints(visible, rows, cols):
    """Build constraints using only visible clues and player flags."""
    constraints = []

    for cell, value in enumerate(visible):
        if not 0 <= value <= 8:
            continue

        unknown = set()
        flagged = 0

        for n in neighbors(cell, rows, cols):
            if visible[n] == UNKNOWN:
                unknown.add(n)
            elif visible[n] == FLAGGED:
                flagged += 1

        remaining_mines = value - flagged

        if not unknown:
            if remaining_mines != 0:
                raise ValueError(f"Inconsistent clue at cell {cell}")
            continue

        constraints.append(
            Constraint(frozenset(unknown), remaining_mines)
        )

    return constraints


def play_one(seed=42, rows=9, cols=9, mine_count=10, verbose=True):
    puzzle = MinesweeperGenerator(
        rows=rows,
        cols=cols,
        mine_count=mine_count,
        seed=seed,
        max_attempts=3000,
    ).generate()

    mines = puzzle["mines"]       # Game simulation only; hidden from solver.
    numbers = puzzle["numbers"]   # Game simulation only; hidden from solver.
    visible = list(puzzle["initial_cells"])

    propagator = ConstraintPropagator(
        max_component_size=20,
        max_search_nodes=500_000,
    )
    rng = random.Random(seed + 1000)

    guesses = 0
    turns = 0
    max_turns = rows * cols * 4

    if verbose:
        print(f"Board: {rows}x{cols}, mines={mine_count}, seed={seed}")

    while turns < max_turns:
        turns += 1

        # Win condition: every safe cell has been revealed.
        if all(mines[i] or 0 <= visible[i] <= 8 for i in range(rows * cols)):
            if verbose:
                print(f"WIN after {turns - 1} turns; guesses={guesses}")
            return True, guesses

        constraints = build_constraints(visible, rows, cols)
        state = KnowledgeState(
            assignments={},
            constraints=tuple(constraints),
        )
        unknown = [
            i for i, value in enumerate(visible)
            if value == UNKNOWN
        ]

        result = propagator.propagate(state)

        if result.contradiction or result.state is None:
            if verbose:
                print("FAIL: inconsistent knowledge.")
            return False, guesses

        # Apply deductions before guessing.
        changed = False

        for cell, value in result.state.assignments.items():
            if visible[cell] != UNKNOWN:
                continue

            if value == SAFE:
                visible[cell] = numbers[cell]
                changed = True
            elif value == MINE:
                visible[cell] = FLAGGED
                changed = True

        if changed:
            continue

        # Propagation is stuck. Guess one remaining unknown cell.
        candidates = sorted(
            set(unknown) - set(result.state.assignments)
        )

        if not candidates:
            if verbose:
                print("FAIL: no unknown cells remain, but board is unfinished.")
            return False, guesses

        guess = rng.choice(candidates)
        guesses += 1

        if mines[guess]:
            if verbose:
                print(f"LOSS: guess #{guesses} hit a mine at cell {guess}.")
            return False, guesses

        visible[guess] = numbers[guess]

        if verbose:
            print(
                f"Guess #{guesses}: cell {guess} was safe; "
                f"revealed clue {numbers[guess]}."
            )

    if verbose:
        print("FAIL: turn limit reached.")
    return False, guesses


def main():
    play_one(seed=42)

    trials = 100
    wins = 0
    total_guesses = 0

    for seed in range(1000, 1000 + trials):
        won, guesses = play_one(seed=seed, verbose=False)
        wins += int(won)
        total_guesses += guesses

    print()
    print(f"Win rate: {wins}/{trials} ({wins / trials:.1%})")
    print(f"Average guesses per game: {total_guesses / trials:.2f}")


if __name__ == "__main__":
    main()