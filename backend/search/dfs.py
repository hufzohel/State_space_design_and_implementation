from dataclasses import dataclass

@dataclass
class SearchResult:
    actions: list
    states: list
    expanded_nodes: int


class DFSSolver:
    def __init__(self, problem):
        self.problem = problem

    def solve(self):
        initial_state = self.problem.initial_state

        stack = [initial_state]

        visited = {initial_state}

        parent = {
            initial_state: None
        }

        action_taken = {
            initial_state: None
        }

        expanded_nodes = 0

        while stack:
            state = stack.pop()
            expanded_nodes += 1

            if self.problem.is_goal(state):
                return self._build_result(
                    state,
                    parent,
                    action_taken,
                    expanded_nodes
                )

            for action in self.problem.actions(state):
                next_state = self.problem.result(
                    state,
                    action
                )

                if next_state in visited:
                    continue

                visited.add(next_state)

                parent[next_state] = state
                action_taken[next_state] = action

                stack.append(next_state)

        return None

    def _build_result(
        self,
        goal_state,
        parent,
        action_taken,
        expanded_nodes
    ):
        actions = []
        states = []

        current = goal_state

        while current is not None:
            states.append(current)

            action = action_taken[current]

            if action is not None:
                actions.append(action)

            current = parent[current]

        states.reverse()
        actions.reverse()

        return SearchResult(
            actions=actions,
            states=states,
            expanded_nodes=expanded_nodes
        )