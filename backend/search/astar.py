
# search/astar.py

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from time import perf_counter


@dataclass
class SearchResult:
    found: bool
    states: list
    actions: list
    cost: float
    expanded: int
    generated: int
    elapsed_seconds: float
    status: str


def astar(problem, cost_fn=None, max_expansions=None):
    """
    Generic A* search.

    Required problem interface:
        problem.initial_state
        problem.actions(state)
        problem.result(state, action)
        problem.is_goal(state)
        problem.heuristic(state)

    Optional:
        cost_fn(state, action, next_state) -> nonnegative cost

    Default action cost: 1.
    States must be hashable.
    """

    start_time = perf_counter()

    if cost_fn is None:
        cost_fn = lambda state, action, next_state: 1

    start = problem.initial_state

    # Best known path cost to each state.
    best_g = {start: 0}

    # Used to reconstruct the solution after reaching the goal.
    parent = {}

    # Cache heuristic values because a state may be encountered again.
    h_cache = {}

    def h(state):
        if state not in h_cache:
            h_cache[state] = problem.heuristic(state)
        return h_cache[state]

    # Counter breaks ties without comparing states or actions.
    tie_breaker = count()

    # Entries: (f, h, tie_breaker, g, state)
    frontier = []
    start_h = h(start)

    heappush(
        frontier,
        (start_h, start_h, next(tie_breaker), 0, start)
    )

    expanded = 0
    generated = 1

    def make_result(found, states, actions, cost, status):
        return SearchResult(
            found=found,
            states=states,
            actions=actions,
            cost=cost,
            expanded=expanded,
            generated=generated,
            elapsed_seconds=perf_counter() - start_time,
            status=status,
        )

    def reconstruct(goal):
        states = [goal]
        actions = []
        current = goal

        while current != start:
            previous, action = parent[current]
            actions.append(action)
            states.append(previous)
            current = previous

        states.reverse()
        actions.reverse()

        return states, actions

    while frontier:
        _, _, _, current_g, current = heappop(frontier)

        # Ignore outdated entries left in the priority queue.
        if current_g != best_g.get(current):
            continue

        # Only accept a goal when it is removed from the queue.
        if problem.is_goal(current):
            states, actions = reconstruct(current)

            return make_result(
                True,
                states,
                actions,
                current_g,
                "solved",
            )

        if (
            max_expansions is not None
            and expanded >= max_expansions
        ):
            return make_result(
                False, [], [], float("inf"), "expansion_limit"
            )

        expanded += 1

        for action in problem.actions(current):
            next_state = problem.result(current, action)

            step_cost = cost_fn(current, action, next_state)

            if step_cost < 0:
                raise ValueError("A* requires nonnegative step costs.")

            tentative_g = current_g + step_cost

            # This state already has an equal or cheaper path.
            if tentative_g >= best_g.get(next_state, float("inf")):
                continue

            # Found a better route. Reopen the state if necessary.
            best_g[next_state] = tentative_g
            parent[next_state] = (current, action)

            next_h = h(next_state)
            next_f = tentative_g + next_h

            heappush(
                frontier,
                (
                    next_f,
                    next_h,
                    next(tie_breaker),
                    tentative_g,
                    next_state,
                )
            )

            generated += 1

    return make_result(
        False, [], [], float("inf"), "no_solution"
    )
