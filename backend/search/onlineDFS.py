
from dataclasses import dataclass
from time import perf_counter

from backend.puzzles.minesweeper.action import RevealAction, FlagAction
from backend.puzzles.minesweeper.state import is_unknown
from backend.puzzles.minesweeper.environment import MinesweeperState


@dataclass
class OnlineDFSResult:
    actions: list
    states: list
    expanded_nodes: int
    elapsed_seconds: float
    status: str


class OnlineBlindSolver:
    """
    Stack-based online action selection for Minesweeper.

    Uses only the visible state and problem.actions().
    Does not inspect the hidden mine layout or use heuristic scores.

    The environment executes each chosen action externally.
    """

    def __init__(self, problem, environment):
        self.problem = problem
        self.environment = environment
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

        candidate_by_cell = {
            action.cell: action
            for action in candidates
            if isinstance(action, (RevealAction, FlagAction))
        }

        # Discard cells that are no longer actionable.
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

    def solve(self):
        start_time = perf_counter()

        state = MinesweeperState(
            cells=tuple(self.problem.initial_state.cells)
        )

        states = [state]
        actions_taken = []
        expanded_nodes = 0

        while True:
            # Check terminal conditions before selecting another action.
            if state.lost:
                status = "lost"
                break

            if self.environment.is_win(state):
                status = "won"
                break

            chosen = self.choose_action(state)

            if chosen is None:
                status = "no_actions"
                break

            expanded_nodes += 1

            # Execute one real action against the environment.
            new_state = self.environment.execute(state, chosen)

            actions_taken.append(chosen)
            states.append(new_state)
            state = new_state

        return OnlineDFSResult(
            actions=actions_taken,
            states=states,
            expanded_nodes=expanded_nodes,
            elapsed_seconds=perf_counter() - start_time,
            status=status,
        )
