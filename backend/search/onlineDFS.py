
from backend.puzzles.minesweeper.action import RevealAction, FlagAction
from backend.puzzles.minesweeper.state import UNKNOWN, is_unknown


class OnlineBlindSolver:
    """
    Stack-based online action selection for Minesweeper.

    Uses only the visible state and problem.actions().
    Does not inspect the hidden mine layout or use heuristic scores.

    The environment must execute each chosen action externally.
    """

    def __init__(self, problem):
        self.problem = problem
        self.stack = []
        self.pending = set()

        # Initial deterministic LIFO order.
        for cell in range(len(problem.initial_state.cells)):
            if is_unknown(problem.initial_state.cells[cell]):
                self._push(cell)

    def _push(self, cell):
        if cell not in self.pending:
            self.stack.append(cell)
            self.pending.add(cell)

    def choose_action(self, state):
        candidates = self.problem.actions(state)

        if not candidates:
            return None

        # Keep only actions that are currently available.
        candidate_by_cell = {
            action.cell: action
            for action in candidates
            if isinstance(action, (RevealAction, FlagAction))
        }

        # Discard pending cells that are no longer actionable.
        self.stack = [
            cell for cell in self.stack
            if cell in candidate_by_cell
        ]
        self.pending = set(self.stack)

        # Add newly available cells.
        for cell in candidate_by_cell:
            self._push(cell)

        # LIFO: choose the most recently pushed available action.
        while self.stack:
            cell = self.stack.pop()
            self.pending.discard(cell)

            action = candidate_by_cell.get(cell)
            if action is not None:
                return action

        return None
