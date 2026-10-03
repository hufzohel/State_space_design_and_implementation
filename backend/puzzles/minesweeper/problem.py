from dataclasses import dataclass

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
    Immutable knowledge state.

    Cell meanings:
        UNKNOWN  (-1): unresolved
        FLAGGED  (-2): asserted mine
        0..8: revealed clue / residual mine requirement
    """

    cells: tuple[int, ...]


class MinesweeperProblem:
    def __init__(
        self,
        rows: int,
        cols: int,
        initial_state: MinesweeperState,
        mines: frozenset[int],
    ):
        self.rows = rows
        self.cols = cols
        self.initial_state = initial_state

        # Hidden environment information.
        # The solver itself should not inspect this when choosing actions.
        self.mines = mines

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

    def _is_contradiction(self, state):
        """
        A revealed clue is represented by its remaining mine requirement.

        Therefore:

            residual < 0
                impossible

            residual > number of unresolved neighbors
                impossible
        """

        for cell, value in enumerate(state.cells):
            if not is_revealed(value):
                continue

            unknown_count = len(self._unknown_neighbors(state, cell))

            if value < 0:
                return True

            if value > unknown_count:
                return True

        return False

    # ------------------------------------------------------------
    # Forced deduction
    # ------------------------------------------------------------

    def _forced_assignments(self, state):
        """
        Return assignments forced by the current residual constraints.

        Each result is:

            (cell, is_mine)

        where:

            is_mine=True   -> cell must be a mine
            is_mine=False  -> cell must be safe

        Only direct local deductions are implemented here.
        """

        forced = {}

        for cell, value in enumerate(state.cells):
            if not is_revealed(value):
                continue

            unknown = self._unknown_neighbors(state, cell)

            if value == 0:
                for n in unknown:
                    forced[n] = False

            elif value == len(unknown):
                for n in unknown:
                    forced[n] = True

        return forced

    # ------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------

    def _propagate(self, state):
        """
        Repeatedly apply forced deductions until reaching a fixed point.

        Returns:
            propagated state
            None if contradiction occurs
        """

        cells = list(state.cells)

        changed = True

        while changed:
            changed = False

            current = MinesweeperState(tuple(cells))

            if self._is_contradiction(current):
                return None

            forced = self._forced_assignments(current)

            for cell, is_mine in forced.items():
                current_value = cells[cell]

                if is_mine:
                    # Already known to be a mine.
                    if current_value == FLAGGED:
                        continue

                    # A revealed number cannot suddenly become a mine.
                    if is_revealed(current_value):
                        return None

                    # Unknown -> flagged.
                    cells[cell] = FLAGGED
                    changed = True

                    # Flagging a mine consumes one remaining mine
                    # from every neighboring clue.
                    for n in self._neighbors(cell):
                        if is_revealed(cells[n]):
                            cells[n] -= 1

                else:
                    # Safe cells remain UNKNOWN until we actually reveal
                    # them through RevealAction.
                    #
                    # We deliberately do not encode "known safe" as another
                    # board value yet.
                    if current_value == FLAGGED:
                        return None

                    # Nothing to mutate here.
                    # The deduction is represented by the forced result,
                    # but actual information acquisition happens through
                    # RevealAction.
                    continue

            # Check again after all mine assignments.
            current = MinesweeperState(tuple(cells))

            if self._is_contradiction(current):
                return None

        return MinesweeperState(tuple(cells))

    # ------------------------------------------------------------
    # Public deduction interface
    # ------------------------------------------------------------

    def forced_actions(self, state):
        """
        Convert current logical deductions into actual game actions.

        A forced mine becomes FlagAction.

        A forced safe cell becomes RevealAction.
        """

        forced = self._forced_assignments(state)

        actions = []

        for cell, is_mine in forced.items():
            if is_mine:
                if is_unknown(state.cells[cell]):
                    actions.append(FlagAction(cell))

            else:
                if is_unknown(state.cells[cell]):
                    actions.append(RevealAction(cell))

        return actions

    # ------------------------------------------------------------
    # Search actions
    # ------------------------------------------------------------

    def actions(self, state):
        """
        Return applicable actions.

        First prefer forced actions.

        If there are no forced actions, branch on one unresolved cell.
        """

        propagated = self._propagate(state)

        if propagated is None:
            return []

        forced = self.forced_actions(propagated)

        if forced:
            return forced

        # No forced move remains.
        #
        # We need to make a search assumption.
        #
        # For now choose the first unknown cell and branch:
        #
        #   Flag(X)
        #   Reveal(X)
        #
        # This is our blind-search branching mechanism.
        for cell, value in enumerate(propagated.cells):
            if value == UNKNOWN:
                return [
                    FlagAction(cell),
                    RevealAction(cell),
                ]

        return []

    # ------------------------------------------------------------
    # State transition
    # ------------------------------------------------------------

    def result(self, state, action):
        """
        Apply one action and return the resulting state.

        Returns None if the action produces a contradiction
        or reveals a mine.
        """

        cells = list(state.cells)

        # --------------------------------------------------------
        # Flag
        # --------------------------------------------------------

        if isinstance(action, FlagAction):
            cell = action.cell

            if not is_unknown(cells[cell]):
                return None

            cells[cell] = FLAGGED

            # A newly asserted mine reduces the remaining mine
            # requirement of neighboring clues.
            for n in self._neighbors(cell):
                if is_revealed(cells[n]):
                    cells[n] -= 1

            next_state = MinesweeperState(tuple(cells))

            return self._propagate(next_state)

        # --------------------------------------------------------
        # Reveal
        # --------------------------------------------------------

        if isinstance(action, RevealAction):
            cell = action.cell

            if not is_unknown(cells[cell]):
                return None

            # The solver does not know this beforehand.
            # The environment reveals the truth here.
            if cell in self.mines:
                return None

            clue = self._actual_clue(cell)

            cells[cell] = clue

            next_state = MinesweeperState(tuple(cells))

            # Zero expansion is an environmental consequence of
            # revealing a zero.
            if clue == 0:
                cells = self._expand_zero_region(cells, cell)

            next_state = MinesweeperState(tuple(cells))

            return self._propagate(next_state)

        raise TypeError(f"Unknown action type: {type(action)}")

    # ------------------------------------------------------------
    # Environment information
    # ------------------------------------------------------------

    def _actual_clue(self, cell):
        """
        Calculate the true Minesweeper clue from the hidden mine map.
        """

        return sum(
            neighbor in self.mines
            for neighbor in self._neighbors(cell)
        )

    def _expand_zero_region(self, cells, start):
        """
        Reveal the zero-connected region and its numbered boundary.

        This is an environment operation, not a search operation.
        """

        queue = [start]
        visited = set()

        while queue:
            cell = queue.pop()

            if cell in visited:
                continue

            visited.add(cell)

            # Never expand through a mine.
            if cell in self.mines:
                continue

            clue = self._actual_clue(cell)

            # Only overwrite unresolved cells.
            if cells[cell] == UNKNOWN:
                cells[cell] = clue

            if clue != 0:
                continue

            for n in self._neighbors(cell):
                if n in visited:
                    continue

                if n in self.mines:
                    continue

                if cells[n] == UNKNOWN:
                    neighbor_clue = self._actual_clue(n)
                    cells[n] = neighbor_clue

                    if neighbor_clue == 0:
                        queue.append(n)

        return cells

    # ------------------------------------------------------------
    # Goal
    # ------------------------------------------------------------

    def is_goal(self, state):
        """
        Goal for this simulated puzzle:

        Every non-mine cell has been revealed and every mine
        has been correctly identified.
        """

        for cell, value in enumerate(state.cells):
            if cell in self.mines:
                if value != FLAGGED:
                    return False
            else:
                if not is_revealed(value):
                    return False

        return True