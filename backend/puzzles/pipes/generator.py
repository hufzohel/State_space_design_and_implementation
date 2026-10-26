# Terminal 1000 8
# Corner: 1100 12
# Straight: 1010 10
# Tee: 1110 14
# Cross: 1111 15
# Orientation: 0 = up, 1 = right, 2 = down, 3 = left
# import random
# import numpy as np
# import deque

# Type_lst = [8, 12, 10, 14, 15]
# Orientation_lst = [1, 2, 4, 8]

# Queue = deque()

# def cyclic_shift_right(val, n, bit_width = 4):
#     n = n % bit_width
#     # Shift right, then grab the underflow bits and OR them to the left
#     return (val >> n) | ((val << (bit_width - n)) & ((1 << bit_width) - 1))

# def branching_function(lst):
#     tiles_state = cyclic_shift_right(lst[0], Orientation_lst.index(lst[1]), 4)
#     return tiles_state


# def board_generator(n, m):
#     # empty board
#     board = [[None for _ in range(m)] for _ in range(n)]

#     # Root tile and position
#     start = [Type_lst[random.randint(0, 4)], Orientation_lst[random.randint(0, 3)]]
#     x_start = random.randint(0, n - 1)
#     y_start = random.randint(0, m - 1)
#     board[x_start][y_start] = start
#     node = [[x_start, y_start], start]

#     visited = {}
#     visited[(x_start, y_start)] = 1

#     Queue.append(node)
#     while Queue:
#         current_node = Queue.popleft()
#         tiles_output = branching_function(current_node[1])
#         for i in range(len(Orientation_lst)):
#             if tiles_output & Orientation_lst[i]:
#                 x_new = current_node[0][0] + (Orientation_lst[i] == 2) - (Orientation_lst[i] == 8)
#                 y_new = current_node[0][1] + (Orientation_lst[i] == 1) - (Orientation_lst[i] == 4)
#                 if 0 <= x_new < n and 0 <= y_new < m and visited.get((x_new, y_new)) is None:
#                     board[x_new][y_new] = [Type_lst[random.randint(0, 4)], Orientation_lst[i]]
#                     Queue.append([[x_new, y_new], board[x_new][y_new]])
#                     visited[(x_new, y_new)] = 1
#                 elif len(visited) == n * m:
#                     return board
                
#         Queue.pop()

# backend/puzzles/pipes/generator.py

import random
from collections import deque

from .state import (
    ALL_DIRECTIONS,
    OPPOSITE,
    get_neighbor,
    in_bounds,
    possible_rotations,
)

class PuzzleGenerator:
    def random_scramble(self, solution):
        """
        Randomly rotate every tile.

        The resulting board is guaranteed to differ from the solution
        whenever at least one tile has more than one possible orientation.
        """
        puzzle = [row[:] for row in solution]

        for r in range(len(puzzle)):
            for c in range(len(puzzle[0])):
                orientations = possible_rotations(solution[r][c])

                if len(orientations) > 1:
                    orientations = [
                        mask for mask in orientations
                        if mask != solution[r][c]
                    ]

                puzzle[r][c] = random.choice(orientations)

        return puzzle

    # ============================================================
    # Tree -> tile conversion
    # ============================================================

    def tree_to_masks(self,edges, n, m):
        """
        Convert a set of tree edges into tile masks.

        Each edge is represented as:

            ((r1, c1), (r2, c2))

        The direction between the two cells determines which bits
        are activated in each cell.
        """
        board = [
            [0 for _ in range(m)]
            for _ in range(n)
        ]

        for (r1, c1), (r2, c2) in edges:

            dr = r2 - r1
            dc = c2 - c1

            if dr == -1 and dc == 0:
                direction = ALL_DIRECTIONS[0]  # UP
            elif dr == 1 and dc == 0:
                direction = ALL_DIRECTIONS[2]  # DOWN
            elif dr == 0 and dc == 1:
                direction = ALL_DIRECTIONS[1]  # RIGHT
            elif dr == 0 and dc == -1:
                direction = ALL_DIRECTIONS[3]  # LEFT
            else:
                raise ValueError("Invalid tree edge.")

            board[r1][c1] |= direction
            board[r2][c2] |= OPPOSITE[direction]

        return board

    # ============================================================
    # APPROACH 1
    # Tree-first generation
    # ============================================================

    def generate_tree(self,n, m):
        """
        Generate a randomized spanning tree of an n x m grid.

        The root is randomized.

        We use randomized BFS:
            - queue contains positions
            - each unvisited neighbor becomes a child
            - every cell is reached exactly once
            - therefore the resulting graph is a tree
        """
        if n <= 0 or m <= 0:
            raise ValueError("Board dimensions must be positive.")

        start = (
            random.randint(0, n - 1),
            random.randint(0, m - 1),
        )

        visited = {start}
        queue = deque([start])
        edges = []

        while queue:
            current = queue.popleft()
            row, col = current

            directions = ALL_DIRECTIONS[:]
            random.shuffle(directions)

            for direction in directions:
                next_row, next_col = get_neighbor(
                    row,
                    col,
                    direction,
                )

                next_cell = (next_row, next_col)

                if not in_bounds(next_row, next_col, n, m):
                    continue

                if next_cell in visited:
                    continue

                # Add exactly one parent -> child edge.
                edges.append((current, next_cell))

                visited.add(next_cell)
                queue.append(next_cell)

        return edges


    def generate_puzzle_tree_first(self,n, m):
        """
        Generate a Pipes puzzle using the tree-first approach.

        Returns:
            puzzle:
                scrambled board

            solution:
                valid connected tree configuration
        """
        edges = self.generate_tree(n, m)

        solution = self.tree_to_masks(edges, n, m)
        puzzle = self.random_scramble(solution)

        return puzzle, solution


    # ============================================================
    # APPROACH 2
    # Your tile-driven approach, refined
    # ============================================================

    def get_available_directions(self, row, col, visited, n, m):
        """
        Return directions from (row, col) that:
            - stay inside the board
            - lead to an unvisited cell
        """
        available = []

        for direction in ALL_DIRECTIONS:
            next_row, next_col = get_neighbor(row, col, direction)
            next_cell = (next_row, next_col)

            if not in_bounds(next_row, next_col, n, m):
                continue

            if next_cell in visited:
                continue

            available.append(direction)

        return available


    
    def choose_tile_with_parent_connection(
        self, required_direction, row, col, visited, n, m
    ):
        """
        Choose a legal tile configuration for a newly discovered cell.

        The parent connection is mandatory.
        Try branching configurations first, then simpler configurations.
        If no child direction is legal, return a terminal tile.
        """

        available = self.get_available_directions(
            row, col, visited, n, m
        )

        # Generate candidate configurations containing the parent
        # connection and any subset of currently available directions.
        candidates = []

        for subset_size in range(len(available), -1, -1):
            for _ in range(1):
                shuffled = available[:]
                random.shuffle(shuffled)

                chosen_directions = [
                    required_direction,
                    *shuffled[:subset_size],
                ]

                mask = 0
                for direction in chosen_directions:
                    mask |= direction

                if mask not in candidates:
                    candidates.append(mask)

        random.shuffle(candidates)

        # Try each candidate in randomized order.
        for mask in candidates:
            legal = True

            for direction in ALL_DIRECTIONS:
                if not (mask & direction):
                    continue

                next_row, next_col = get_neighbor(
                    row, col, direction
                )
                next_cell = (next_row, next_col)

                if not in_bounds(next_row, next_col, n, m):
                    legal = False
                    break

                if next_cell in visited:
                    legal = False
                    break

            if legal:
                return mask

        # Fallback: preserve the parent connection as a terminal.
        return required_direction

    
    def generate_tree_tile_driven(self, n, m, max_attempts=100):
        """
        Generate a spanning tree using tile-driven growth.

        Each tile proposes directions for growth. A direction is
        accepted only if it leads to an unvisited, in-bounds cell.
        Accepted edges are recorded reciprocally in both tiles.
        """

        if n <= 0 or m <= 0:
            raise ValueError("Board dimensions must be positive.")

        if n * m == 1:
            return [[0]]

        for _ in range(max_attempts):
            board = [[0 for _ in range(m)] for _ in range(n)]

            start = (
                random.randint(0, n - 1),
                random.randint(0, m - 1),
            )

            visited = {start}
            queue = deque([start])

            while queue:
                row, col = queue.popleft()

                # Only directions that can create new tree edges.
                available = self.get_available_directions(
                    row, col, visited, n, m
                )
                random.shuffle(available)

                # A tile can stop, continue, or branch.
                child_count = random.randint(0, len(available))
                chosen_directions = available[:child_count]

                for direction in chosen_directions:
                    next_row, next_col = get_neighbor(
                        row, col, direction
                    )
                    next_cell = (next_row, next_col)

                    # Recheck because an earlier direction may have
                    # changed the visited set.
                    if not in_bounds(next_row, next_col, n, m):
                        continue

                    if next_cell in visited:
                        continue

                    # Commit this edge to both endpoint masks.
                    board[row][col] |= direction
                    board[next_row][next_col] |= OPPOSITE[direction]

                    visited.add(next_cell)
                    queue.append(next_cell)

            if len(visited) == n * m:
                return board

        raise RuntimeError(
            f"Failed to generate a complete tree after "
            f"{max_attempts} attempts."
        )



    def generate_puzzle_tile_driven(self, n, m):
        """
        Generate a Pipes puzzle using the tile-driven approach.

        Returns:
            puzzle:
                scrambled initial configuration

            solution:
                valid configuration produced by the generator
        """
        solution = self.generate_tree_tile_driven(n, m)
        puzzle = self.random_scramble(solution)

        return puzzle, solution

    # ============================================================
    # Public generator interface
    # ============================================================

    def generate_puzzle(self, n, m, method="tree"):
        """
        Generate a Pipes puzzle.

        method:
            "tree" -> tree-first approach
            "tile" -> refined tile-driven approach
        """

        if method == "tree":
            return self.generate_puzzle_tree_first(n, m)

        if method == "tile":
            return self.generate_puzzle_tile_driven(n, m)

        raise ValueError(
            "Unknown generation method. "
            "Use 'tree' or 'tile'."
        )