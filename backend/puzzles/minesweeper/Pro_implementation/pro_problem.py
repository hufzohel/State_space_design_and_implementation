
from backend.puzzles.minesweeper.Pro_implementation.pro_state import (
    Constraint,
    KnowledgeState,
)
from backend.search.Minesweeper_pro_solver import ConstraintPropagator


class ProMinesweeperProblem:
    """
    Converts the visible Minesweeper board into logical constraints
    and runs constraint propagation.

    Board encoding:
        0..8 : revealed clue
        -1   : unresolved cell
        -2   : flagged cell
    """

    def __init__(self, rows, cols, board):
        if rows <= 0 or cols <= 0:
            raise ValueError("Board dimensions must be positive")

        if len(board) != rows * cols:
            raise ValueError(
                "Board length must equal rows * cols"
            )

        self.rows = rows
        self.cols = cols
        self.board = list(board)

        self.propagator = ConstraintPropagator()

        self.last_steps = []
        self.last_result = None

    def initial_state(self):
        """
        Build the initial knowledge state and propagate it.

        Returns:
            KnowledgeState if consistent, otherwise None.
        """
        self.last_steps = []
        self.last_result = None

        try:
            constraints = self._build_constraints()

            state = KnowledgeState(
                assignments={},
                constraints=tuple(constraints),
            )

        except (TypeError, ValueError) as exc:
            self.last_steps = [
                {
                    "type": "contradiction",
                    "reason": "invalid_board",
                    "message": str(exc),
                }
            ]
            return None

        result = self.propagator.propagate(state)

        self.last_result = result
        self.last_steps = result.steps

        if result.contradiction:
            return None

        return result.state

    def _build_constraints(self):
        constraints = []

        for cell, value in enumerate(self.board):
            if value in (-1, -2):
                continue

            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 0 <= value <= 8
            ):
                raise ValueError(
                    f"Invalid board value {value!r} at cell {cell}"
                )

            unknown = set()
            flagged = 0

            for neighbor in self._neighbors(cell):
                neighbor_value = self.board[neighbor]

                if neighbor_value == -1:
                    unknown.add(neighbor)

                elif neighbor_value == -2:
                    flagged += 1

            remaining_mines = value - flagged

            # Every clue must be consistent, including clues whose
            # neighboring cells are already fully resolved.
            if (
                remaining_mines < 0
                or remaining_mines > len(unknown)
            ):
                raise ValueError(
                    f"Inconsistent clue at cell {cell}: "
                    f"value={value}, flagged={flagged}, "
                    f"unknown={len(unknown)}"
                )

            if not unknown:
                # The validation above guarantees remaining_mines == 0.
                continue

            constraints.append(
                Constraint(
                    cells=frozenset(unknown),
                    mines=remaining_mines,
                )
            )

        # Deduplicate identical equations and reject conflicting
        # equations over the same cells.
        by_cells = {}

        for c in constraints:
            previous = by_cells.get(c.cells)

            if previous is not None and previous != c.mines:
                raise ValueError(
                    "Conflicting clues over cells "
                    f"{sorted(c.cells)}: "
                    f"{previous} versus {c.mines} mines"
                )

            by_cells[c.cells] = c.mines

        return [
            Constraint(cells=cells, mines=mines)
            for cells, mines in by_cells.items()
        ]

    def _neighbors(self, cell):
        row = cell // self.cols
        col = cell % self.cols

        result = []

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue

                r = row + dr
                c = col + dc

                if 0 <= r < self.rows and 0 <= c < self.cols:
                    result.append(r * self.cols + c)

        return result
