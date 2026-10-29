
from dataclasses import dataclass
from time import perf_counter

from backend.puzzles.minesweeper.action import RevealAction, FlagAction
from backend.puzzles.minesweeper.environment import (
    MinesweeperState,
)


@dataclass
class GreedyResult:
    actions: list
    states: list
    expanded_nodes: int
    elapsed_seconds: float
    status: str


class GreedySolver:
    """
    Greedy online solver for Minesweeper.

    Uses only the visible state and the problem's heuristic.
    The environment executes each real action and returns the
    resulting state. The solver never reads the hidden mine layout.
    """

    def __init__(self, problem, environment):
        self.problem = problem
        self.environment = environment

    def solve(self):
        start_time = perf_counter()

        state = MinesweeperState(
            cells=tuple(self.problem.initial_state.cells)
        )
        states = [state]
        actions_taken = []
        expanded_nodes = 0

        while True:
            # Check terminal conditions using the actual environment API.
            if state.lost:
                status = "lost"
                break

            if self.environment.is_win(state):
                status = "won"
                break

            candidates = self.problem.actions(state)

            if not candidates:
                status = "no_actions"
                break

            expanded_nodes += 1

            # Forced flags take priority over reveal candidates.
            flag_actions = [
                action
                for action in candidates
                if isinstance(action, FlagAction)
            ]

            if flag_actions:
                chosen = flag_actions[0]

            else:
                reveal_actions = [
                    action
                    for action in candidates
                    if isinstance(action, RevealAction)
                ]

                if not reveal_actions:
                    status = "no_actions"
                    break

                # print("Candidate scores:")
                # for action in reveal_actions:
                #     print(
                #         f"  cell={action.cell}, "
                #         f"safety={self.problem.safety_probability(state, action.cell)}, "
                #         f"entropy={self.problem.outcome_entropy(state, action.cell)}, "
                #         f"score={self.problem.heuristic(state, action.cell, use_entropy=True)}"
                #     )
                
                chosen = max(
                    reveal_actions,
                    key=lambda action: self.problem.heuristic(
                        state,
                        action.cell,
                        use_entropy=False,
                    ),
                )

            # Execute one real action against the current visible state.
            new_state = self.environment.execute(state, chosen)

            actions_taken.append(chosen)
            states.append(new_state)
            state = new_state

            # The next loop iteration detects a win or loss.

        return GreedyResult(
            actions=actions_taken,
            states=states,
            expanded_nodes=expanded_nodes,
            elapsed_seconds=perf_counter() - start_time,
            status=status,
        )
