from .pro_state import (
    SAFE,
    MINE,
    Constraint,
    KnowledgeState,
)
from backend.search.Minesweeper_pro_solver import ConstraintPropagator


class ProMinesweeperProblem:

    def __init__(self, rows, cols, board):

        self.rows = rows
        self.cols = cols
        self.board = board

        self.propagator = ConstraintPropagator()

    def initial_state(self):

        constraints = self._build_constraints()

        state = KnowledgeState(
            assignments={},
            constraints=tuple(constraints),
        )

        return self.propagator.propagate(state)

    def _build_constraints(self):

        constraints = []

        for cell, value in enumerate(self.board):

            if not (0 <= value <= 8):
                continue

            unknown = set()

            flagged = 0

            for neighbor in self._neighbors(cell):

                if self.board[neighbor] == -1:
                    unknown.add(neighbor)

                elif self.board[neighbor] == -2:
                    flagged += 1

            remaining_mines = value - flagged

            if unknown:

                constraints.append(
                    Constraint(
                        cells=frozenset(unknown),
                        mines=remaining_mines,
                    )
                )

        return constraints

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
                    result.append(
                        r * self.cols + c
                    )

        return result