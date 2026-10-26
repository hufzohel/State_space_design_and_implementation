
from dataclasses import dataclass

from .state import UNKNOWN, FLAGGED, is_unknown, is_revealed, neighbors
from .action import RevealAction, FlagAction


@dataclass(frozen=True)
class MinesweeperState:
    cells: tuple[int, ...]
    lost: bool = False


class MinesweeperEnvironment:
    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.mines = frozenset(mines)

    def _neighbors(self, cell):
        return neighbors(cell, self.rows, self.cols)

    def _actual_clue(self, cell):
        return sum(
            n in self.mines
            for n in self._neighbors(cell)
        )

    def execute(self, state, action):
        """Execute one real action. This is not hypothetical search."""
        if state.lost:
            return state

        cells = list(state.cells)
        cell = action.cell

        if not (0 <= cell < len(cells)):
            raise IndexError("Cell index out of range")

        if not is_unknown(cells[cell]):
            return state

        if isinstance(action, FlagAction):
            cells[cell] = FLAGGED
            return MinesweeperState(tuple(cells))

        if isinstance(action, RevealAction):
            if cell in self.mines:
                return MinesweeperState(tuple(cells), lost=True)

            # The environment obtains the actual clue.
            cells[cell] = self._actual_clue(cell)
            return MinesweeperState(tuple(cells))

        raise TypeError(f"Unknown action type: {type(action)}")

    def is_win(self, state):
        if state.lost:
            return False

        for cell, value in enumerate(state.cells):
            if cell in self.mines:
                if value != FLAGGED:
                    return False
            elif not is_revealed(value):
                return False

        return True
