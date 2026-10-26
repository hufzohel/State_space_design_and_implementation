from .state import UNKNOWN, WHITE, BLACK, KakurasuState
from .action import KakurasuAction


class KakurasuProblem:
    def __init__(
        self,
        rows,
        cols,
        row_targets,
        col_targets,
        initial_state=None,
    ):
        if rows <= 0 or cols <= 0:
            raise ValueError("Board dimensions must be positive")

        if len(row_targets) != rows:
            raise ValueError("There must be one target per row")

        if len(col_targets) != cols:
            raise ValueError("There must be one target per column")

        self.rows = rows
        self.cols = cols
        self.row_targets = tuple(row_targets)
        self.col_targets = tuple(col_targets)

        if initial_state is None:
            initial_state = KakurasuState(
                (UNKNOWN,) * (rows * cols)
            )

        if len(initial_state.cells) != rows * cols:
            raise ValueError("Incorrect number of cells")

        if any(v not in (UNKNOWN, WHITE, BLACK)
               for v in initial_state.cells):
            raise ValueError("Invalid cell value")

        self.initial_state = initial_state

    @classmethod
    def from_generated(cls, generated):
        return cls(
            rows=generated["rows"],
            cols=generated["cols"],
            row_targets=generated["row_targets"],
            col_targets=generated["col_targets"],
            initial_state=KakurasuState(
                generated["initial_cells"]
            ),
        )

    def _calculate_sums(self, state):
        row_sums = [0] * self.rows
        col_sums = [0] * self.cols

        for index, value in enumerate(state.cells):
            if value != BLACK:
                continue

            row, col = divmod(index, self.cols)

            # Black cell contributes its 1-based column to its row.
            row_sums[row] += col + 1

            # Black cell contributes its 1-based row to its column.
            col_sums[col] += row + 1

        return row_sums, col_sums

    def _is_feasible(self, state):
        """Can every row and column still reach its target?"""
        row_sums, col_sums = self._calculate_sums(state)

        row_remaining = [0] * self.rows
        col_remaining = [0] * self.cols

        for index, value in enumerate(state.cells):
            if value != UNKNOWN:
                continue

            row, col = divmod(index, self.cols)
            row_remaining[row] += col + 1
            col_remaining[col] += row + 1

        for r in range(self.rows):
            target = self.row_targets[r]

            if row_sums[r] > target:
                return False

            if row_sums[r] + row_remaining[r] < target:
                return False

        for c in range(self.cols):
            target = self.col_targets[c]

            if col_sums[c] > target:
                return False

            if col_sums[c] + col_remaining[c] < target:
                return False

        return True

    def actions(self, state):
        """Assign the first unknown cell, branching white or black."""
        try:
            cell = state.cells.index(UNKNOWN)
        except ValueError:
            return []

        result = []

        # Try black first, then white.
        for value in (BLACK, WHITE):
            cells = list(state.cells)
            cells[cell] = value
            candidate = KakurasuState(tuple(cells))

            if self._is_feasible(candidate):
                result.append(KakurasuAction(cell, value))

        return result

    def result(self, state, action):
        if not 0 <= action.cell < self.rows * self.cols:
            raise IndexError("Cell index out of range")

        if state.cells[action.cell] != UNKNOWN:
            raise ValueError("Cell has already been assigned")

        cells = list(state.cells)
        cells[action.cell] = action.value

        return KakurasuState(tuple(cells))

    def is_goal(self, state):
        # A solution must assign every cell.
        if UNKNOWN in state.cells:
            return False

        row_sums, col_sums = self._calculate_sums(state)

        return (
            tuple(row_sums) == self.row_targets
            and tuple(col_sums) == self.col_targets
        )

    def heuristic(self, state):
        """Lower bound on the number of remaining cell assignments."""
        return state.cells.count(UNKNOWN)

    def to_display_cells(self, state):
        """Convert a state to a 2D grid for the frontend."""
        return [
            list(state.cells[r * self.cols:(r + 1) * self.cols])
            for r in range(self.rows)
        ]