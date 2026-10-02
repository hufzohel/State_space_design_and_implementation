from collections import deque

from .state import (
    UP,
    RIGHT,
    DOWN,
    LEFT,
    DIRECTIONS,
    OPPOSITE,
    ALL_DIRECTIONS,
    rotate_mask,
    possible_rotations,
)
from .action import RotateAction


class PipesProblem:
    def __init__(self, puzzle):
        """
        puzzle: 2D list of tile masks.
        Example:
            [
                [12, 10, 8],
                [14, 15, 12],
                [8,  10, 14]
            ]
        """

        self.rows = len(puzzle)
        self.cols = len(puzzle[0])

        # Flatten the board so the state is easy to hash.
        self.initial_state = tuple(
            tile
            for row in puzzle
            for tile in row
        )

    def actions(self, state):
        """
        Return all possible rotations from this state.
        """

        actions = []

        for tile_index, mask in enumerate(state):

            # Try the three possible non-zero rotations.
            seen_masks = set()

            for turns in (1, 2, 3):
                new_mask = rotate_mask(mask, turns)

                # Symmetric pieces may produce the same orientation.
                if new_mask == mask:
                    continue

                if new_mask in seen_masks:
                    continue

                seen_masks.add(new_mask)

                actions.append(
                    RotateAction(
                        tile_index=tile_index,
                        turns=turns
                    )
                )

        return actions

    def result(self, state, action):
        """
        Apply an action and return the resulting state.

        The original state is not modified.
        """

        new_state = list(state)

        tile_index = action.tile_index
        turns = action.turns

        new_state[tile_index] = rotate_mask(
            new_state[tile_index],
            turns
        )

        return tuple(new_state)

    def is_goal(self, state):
        """
        A Pipes board is solved when:

        1. No pipe leaks outside the board.
        2. Every connection is reciprocal.
        3. Every tile belongs to one connected component.
        4. The resulting graph has no cycles.
        """

        # ---------------------------------------------------------
        # 1. Check boundary leaks + reciprocal connections
        # ---------------------------------------------------------

        edge_count = 0

        for index, mask in enumerate(state):
            row = index // self.cols
            col = index % self.cols

            for direction in ALL_DIRECTIONS:

                if not (mask & direction):
                    continue

                next_row = row + DIRECTIONS[direction][0]
                next_col = col + DIRECTIONS[direction][1]

                # Pipe points outside the board.
                if not (
                    0 <= next_row < self.rows
                    and 0 <= next_col < self.cols
                ):
                    return False

                next_index = next_row * self.cols + next_col
                next_mask = state[next_index]

                # Neighbor must point back.
                if not (next_mask & OPPOSITE[direction]):
                    return False

                # Count each undirected edge only once.
                if direction in (RIGHT, DOWN):
                    edge_count += 1

        # ---------------------------------------------------------
        # 2. Check connectivity
        # ---------------------------------------------------------

        if not state:
            return False

        visited = {0}
        queue = deque([0])

        while queue:
            index = queue.popleft()

            row = index // self.cols
            col = index % self.cols
            mask = state[index]

            for direction in ALL_DIRECTIONS:

                if not (mask & direction):
                    continue

                dr, dc = DIRECTIONS[direction]
                next_row = row + dr
                next_col = col + dc

                next_index = next_row * self.cols + next_col

                if next_index not in visited:
                    visited.add(next_index)
                    queue.append(next_index)

        if len(visited) != len(state):
            return False

        # ---------------------------------------------------------
        # 3. Connected graph + N-1 edges = tree
        # ---------------------------------------------------------

        if edge_count != len(state) - 1:
            return False

        return True

    def heuristic(self, state):
        """
        Estimates the remaining tree-connection progress.

        The reciprocal connections form a graph over the tiles.
        If the graph has C connected components, at least C - 1
        component merges are needed to obtain one connected tree.

        This measures structural progress toward the goal.
        """

        n = len(state) 

        # Find connected components in the reciprocal-connection graph.
        visited = set()
        components = 0

        for start in range(n):
            if start in visited:
                continue

            components += 1
            stack = [start]
            visited.add(start)

            while stack:
                index = stack.pop()

                row = index // self.cols
                col = index % self.cols
                mask = state[index]

                for direction in ALL_DIRECTIONS:
                    if not (mask & direction):
                        continue

                    next_row = row + DIRECTIONS[direction][0]
                    next_col = col + DIRECTIONS[direction][1]

                    # Boundary connection cannot be reciprocal.
                    if not (
                        0 <= next_row < self.rows
                        and 0 <= next_col < self.cols
                    ):
                        continue

                    next_index = next_row * self.cols + next_col
                    next_mask = state[next_index]

                    # Only traverse reciprocal connections.
                    if not (next_mask & OPPOSITE[direction]):
                        continue

                    if next_index not in visited:
                        visited.add(next_index)
                        stack.append(next_index)

        return components - 1