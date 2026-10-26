
from dataclasses import dataclass
from math import log2

from .state import (
    UNKNOWN,
    FLAGGED,
    is_unknown,
    is_flagged,
    is_revealed,
    neighbors,
)
from .action import RevealAction, FlagAction


@dataclass(frozen=True)
class MinesweeperState:
    """
    Solver-visible state matching the environment's representation.

    UNKNOWN (-1): unresolved cell
    FLAGGED (-2): cell asserted to be a mine
    0..8: original displayed clue
    """

    cells: tuple[int, ...]


@dataclass(frozen=True)
class _ResidualState:
    """
    Internal reasoning state.

    `cells` preserves the original cell markers and displayed clues.
    `requirements[cell]` stores the remaining mine requirement for
    each revealed clue, after accounting for asserted mines.

    None means that the cell is not a revealed clue.

    Keeping requirements separate prevents negative residual values
    from colliding with UNKNOWN (-1) and FLAGGED (-2).
    """

    cells: tuple[int, ...]
    requirements: tuple[int | None, ...]


class MinesweeperProblem:
    """
    Solver-side Minesweeper model.

    Never stores or inspects the actual mine map.

    Public methods accept the original visible state.
    Internal deduction and probability methods use _ResidualState
    after propagation.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        initial_state: MinesweeperState,
    ):
        if rows <= 0 or cols <= 0:
            raise ValueError("rows and cols must be positive")

        if len(initial_state.cells) != rows * cols:
            raise ValueError(
                "State size must equal rows * cols"
            )

        self.rows = rows
        self.cols = cols
        self.initial_state = initial_state

    # ------------------------------------------------------------
    # Basic state helpers
    # ------------------------------------------------------------

    def _neighbors(self, cell):
        return neighbors(cell, self.rows, self.cols)

    def _unknown_neighbors(self, state, cell):
        return [
            n
            for n in self._neighbors(cell)
            if is_unknown(state.cells[n])
        ]

    def _flagged_neighbors(self, state, cell):
        return [
            n
            for n in self._neighbors(cell)
            if is_flagged(state.cells[n])
        ]

    # ------------------------------------------------------------
    # Constraint checking
    # ------------------------------------------------------------

    def _is_contradiction(self, state: _ResidualState):
        """
        Return True if any residual clue is impossible to satisfy.
        """

        for cell, value in enumerate(state.cells):
            if not is_revealed(value):
                continue

            requirement = state.requirements[cell]

            if requirement is None:
                return True

            unknown_count = len(
                self._unknown_neighbors(state, cell)
            )

            if requirement < 0:
                return True

            if requirement > unknown_count:
                return True

        return False

    # ------------------------------------------------------------
    # Forced deduction
    # ------------------------------------------------------------

    def _forced_assignments(self, state: _ResidualState):
        """
        Return {cell: is_mine} for direct logical deductions.

        True  = forced mine
        False = forced safe
        None  = contradictory deductions
        """

        forced = {}

        def assign(cell, is_mine):
            if cell in forced and forced[cell] != is_mine:
                return False

            forced[cell] = is_mine
            return True

        for cell, value in enumerate(state.cells):
            if not is_revealed(value):
                continue

            requirement = state.requirements[cell]

            if requirement is None:
                return None

            unknown = self._unknown_neighbors(state, cell)

            if requirement == 0:
                for n in unknown:
                    if not assign(n, False):
                        return None

            elif requirement == len(unknown):
                for n in unknown:
                    if not assign(n, True):
                        return None

        return forced

    # ------------------------------------------------------------
    # Constraint propagation
    # ------------------------------------------------------------

    def _propagate(self, state: MinesweeperState):
        """
        Convert original displayed clues into residual requirements,
        then repeatedly flag logically forced mines in a temporary
        state until reaching a fixed point.

        Existing flags are treated as asserted mines and subtracted
        exactly once when residual requirements are initialized.

        Newly inferred mines decrement adjacent residual requirements
        exactly once when they are added.

        The input state and environment are never modified.
        """

        cells = list(state.cells)

        # Preserve original clue values in `cells`.
        # Store residual requirements separately to avoid sentinel
        # collisions when a requirement becomes negative.
        requirements = [None] * len(cells)

        for cell, value in enumerate(cells):
            if not is_revealed(value):
                continue

            flagged_count = sum(
                1
                for n in self._neighbors(cell)
                if is_flagged(cells[n])
            )

            requirements[cell] = value - flagged_count

        while True:
            current = _ResidualState(
                cells=tuple(cells),
                requirements=tuple(requirements),
            )

            if self._is_contradiction(current):
                return None

            forced = self._forced_assignments(current)

            if forced is None:
                return None

            changed = False

            for cell, is_mine in forced.items():
                if not is_mine:
                    continue

                if not is_unknown(cells[cell]):
                    continue

                cells[cell] = FLAGGED
                changed = True

                # Account for this newly inferred mine in every
                # adjacent revealed clue's residual requirement.
                for n in self._neighbors(cell):
                    if is_revealed(cells[n]):
                        if requirements[n] is None:
                            return None

                        requirements[n] -= 1

            if not changed:
                result = _ResidualState(
                    cells=tuple(cells),
                    requirements=tuple(requirements),
                )

                if self._is_contradiction(result):
                    return None

                return result

    # ------------------------------------------------------------
    # Forced actions and candidate generation
    # ------------------------------------------------------------

    def forced_actions(self, state: MinesweeperState):
        """
        Return logically forced actions without consulting the
        hidden mine map.
        """

        propagated = self._propagate(state)

        if propagated is None:
            return []

        # Return newly inferred mines that are not yet flagged
        # in the real environment state.
        newly_flagged = [
            cell
            for cell, value in enumerate(propagated.cells)
            if is_unknown(state.cells[cell])
            and value == FLAGGED
        ]

        if newly_flagged:
            return [
                FlagAction(cell)
                for cell in newly_flagged
            ]

        forced = self._forced_assignments(propagated)

        if forced is None:
            return []

        return [
            RevealAction(cell)
            for cell, is_mine in forced.items()
            if not is_mine
            and is_unknown(propagated.cells[cell])
        ]

    def actions(self, state: MinesweeperState):
        """
        Generate the next actions for the player-like solver.

        Priority:
        1. Flag logically forced mines.
        2. Reveal logically forced-safe cells.
        3. If neither exists, return all unknown cells as candidates.

        The heuristic ranks reveal candidates. It never simulates
        the hidden outcome of a reveal.
        """

        propagated = self._propagate(state)

        if propagated is None:
            return []

        forced = self._forced_assignments(propagated)

        if forced is None:
            return []

        newly_flagged = [
            cell
            for cell, value in enumerate(propagated.cells)
            if is_unknown(state.cells[cell])
            and value == FLAGGED
        ]

        if newly_flagged:
            return [
                FlagAction(cell)
                for cell in newly_flagged
            ]

        safe_cells = [
            cell
            for cell, is_mine in forced.items()
            if not is_mine
            and is_unknown(propagated.cells[cell])
        ]

        if safe_cells:
            return [
                RevealAction(cell)
                for cell in safe_cells
            ]

        return [
            RevealAction(cell)
            for cell, value in enumerate(propagated.cells)
            if is_unknown(value)
        ]

    # ------------------------------------------------------------
    # Constraint-consistent configuration enumeration
    # ------------------------------------------------------------

    def _consistent_configurations(
        self,
        state: _ResidualState,
        extra_cells=(),
    ):
        """
        Enumerate assignments consistent with all residual constraints.

        Each assignment maps an unknown cell to:
            0 = safe
            1 = mine

        All FLAGGED cells are treated as asserted mines.
        Revealed clues use their residual requirements.

        `extra_cells` includes additional unknown cells needed to
        calculate a candidate's mine probability or clue outcomes.

        Returns a list of assignments, or [] if inconsistent.
        """

        constraints = []

        for clue_cell, value in enumerate(state.cells):
            if not is_revealed(value):
                continue

            requirement = state.requirements[clue_cell]

            if requirement is None:
                return []

            unknown = self._unknown_neighbors(
                state,
                clue_cell,
            )

            if (
                requirement < 0
                or requirement > len(unknown)
            ):
                return []

            constraints.append(
                (tuple(unknown), requirement)
            )

        variables = set()

        for cell in extra_cells:
            if (
                0 <= cell < len(state.cells)
                and is_unknown(state.cells[cell])
            ):
                variables.add(cell)

        for cells, _ in constraints:
            variables.update(cells)

        variables = sorted(variables)

        assignment = {}
        solutions = []

        def feasible():
            for constrained_cells, requirement in constraints:
                assigned_mines = sum(
                    assignment[cell]
                    for cell in constrained_cells
                    if cell in assignment
                )

                unassigned = sum(
                    1
                    for cell in constrained_cells
                    if cell not in assignment
                )

                if assigned_mines > requirement:
                    return False

                if (
                    assigned_mines + unassigned
                    < requirement
                ):
                    return False

            return True

        def backtrack(index):
            if index == len(variables):
                if feasible():
                    solutions.append(assignment.copy())
                return

            cell = variables[index]

            for is_mine in (0, 1):
                assignment[cell] = is_mine

                if feasible():
                    backtrack(index + 1)

                del assignment[cell]

        backtrack(0)
        return solutions

    # ------------------------------------------------------------
    # Internal probability methods
    # These methods accept an ALREADY-PROPAGATED state.
    # ------------------------------------------------------------

    def _mine_probability_residual(
        self,
        state: _ResidualState,
        cell: int,
    ):
        """Mine probability for a residual state."""

        if not is_unknown(state.cells[cell]):
            return None

        configurations = self._consistent_configurations(
            state,
            extra_cells=(cell,),
        )

        if not configurations:
            return None

        mined = sum(
            configuration[cell]
            for configuration in configurations
        )

        return mined / len(configurations)

    def _outcome_entropy_residual(
        self,
        state: _ResidualState,
        cell: int,
    ):
        """
        Entropy in bits of the clue observed at `cell`,
        conditional on that cell being safe.
        """

        if not is_unknown(state.cells[cell]):
            return None

        adjacent = self._neighbors(cell)

        extra_cells = [cell] + [
            n
            for n in adjacent
            if is_unknown(state.cells[n])
        ]

        configurations = self._consistent_configurations(
            state,
            extra_cells=extra_cells,
        )

        if not configurations:
            return None

        safe_configurations = [
            configuration
            for configuration in configurations
            if configuration[cell] == 0
        ]

        if not safe_configurations:
            return 0.0

        outcome_counts = {}

        for configuration in safe_configurations:
            # Existing flags count as asserted mines.
            clue = sum(
                1
                for n in adjacent
                if is_flagged(state.cells[n])
            )

            # Count mines among unknown neighbors.
            clue += sum(
                configuration.get(n, 0)
                for n in adjacent
                if is_unknown(state.cells[n])
            )

            outcome_counts[clue] = (
                outcome_counts.get(clue, 0) + 1
            )

        total = len(safe_configurations)

        return -sum(
            (count / total) * log2(count / total)
            for count in outcome_counts.values()
            if count > 0
        )

    # ------------------------------------------------------------
    # Public probability methods
    # These accept the ORIGINAL visible state.
    # ------------------------------------------------------------

    def mine_probability(self, state, cell):
        """
        Estimate P(cell is a mine | visible clues).

        Consistent configurations are initially treated as equally
        likely. Returns None if the constraints are inconsistent.
        """

        if not is_unknown(state.cells[cell]):
            return None

        propagated = self._propagate(state)

        if propagated is None:
            return None

        # A forced mine is already represented as FLAGGED internally.
        if not is_unknown(propagated.cells[cell]):
            return 1.0

        return self._mine_probability_residual(
            propagated,
            cell,
        )

    def safety_probability(self, state, cell):
        """Estimate P(cell is safe | visible clues)."""

        probability = self.mine_probability(state, cell)

        if probability is None:
            return None

        return 1.0 - probability

    def outcome_entropy(self, state, cell):
        """
        Estimate the entropy of the clue observed at `cell`,
        conditional on a safe reveal.
        """

        if not is_unknown(state.cells[cell]):
            return None

        propagated = self._propagate(state)

        if propagated is None:
            return None

        if not is_unknown(propagated.cells[cell]):
            # A forced mine cannot safely be revealed.
            return 0.0

        return self._outcome_entropy_residual(
            propagated,
            cell,
        )

    # ------------------------------------------------------------
    # Candidate scoring
    # ------------------------------------------------------------

    def heuristic(
        self,
        state: MinesweeperState,
        cell: int,
        use_entropy=True,
    ) -> float:
        """
        Higher score means a more attractive reveal candidate.

        use_entropy=False:
            Score by estimated safety probability.

        use_entropy=True:
            Score by safety probability * conditional clue entropy.

        Logically known mines are never selected.
        If guaranteed-safe candidates exist, uncertain candidates
        are excluded.
        """

        if not (0 <= cell < len(state.cells)):
            return float("-inf")

        if not is_unknown(state.cells[cell]):
            return float("-inf")

        propagated = self._propagate(state)

        if propagated is None:
            return float("-inf")

        forced = self._forced_assignments(propagated)

        if forced is None or forced.get(cell) is True:
            return float("-inf")

        safe_cells = {
            candidate
            for candidate, is_mine in forced.items()
            if not is_mine
            and is_unknown(propagated.cells[candidate])
        }

        if safe_cells and cell not in safe_cells:
            return float("-inf")

        mine_probability = self._mine_probability_residual(
            propagated,
            cell,
        )

        if mine_probability is None:
            return float("-inf")

        safety = 1.0 - mine_probability

        if not use_entropy:
            return safety

        entropy = self._outcome_entropy_residual(
            propagated,
            cell,
        )

        if entropy is None:
            return float("-inf")

        return safety * entropy
