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


    def choose_tile_with_parent_connection(self, required_direction, row, col, visited, n, m,):
        """
        Choose the tile for a newly discovered cell.

        The tile MUST contain the connection back to its parent.

        Additional connections are chosen randomly from legal,
        currently-unvisited neighbors.

        Every chosen connection will later become a child of
        this node.
        """
        available = self.get_available_directions(
            row,
            col,
            visited,
            n,
            m,
        )

        random.shuffle(available)

        # The parent connection is already guaranteed.
        # Choose how many additional children this node has.
        child_count = random.randint(0, len(available))

        chosen_directions = [
            required_direction,
            *available[:child_count],
        ]

        mask = 0

        for direction in chosen_directions:
            mask |= direction

        return mask


    def generate_tree_tile_driven(self, n, m, max_attempts=100):
        """
        Generate a spanning tree using the tile-driven approach.

        Construction:

            random root
                ↓
            choose root tile
                ↓
            tile directions determine children
                ↓
            each child receives the reciprocal parent connection
                ↓
            repeat until all cells are visited

        The generation is retried if random tile choices cause the
        queue to become empty before the entire board is covered.

        Queue entries contain:

            ((row, col), tile_mask)

        because the tile determines which directions this node
        attempts to expand toward.
        """
        if n <= 0 or m <= 0:
            raise ValueError("Board dimensions must be positive.")

        if n * m == 1:
            return [[0]]

        for _ in range(max_attempts):

            board = [
                [None for _ in range(m)]
                for _ in range(n)
            ]

            # ----------------------------------------------------
            # 1. Random root
            # ----------------------------------------------------

            start = (
                random.randint(0, n - 1),
                random.randint(0, m - 1),
            )

            # ----------------------------------------------------
            # 2. Choose root's tile
            # ----------------------------------------------------

            root_candidates = self.get_available_directions(
                start[0],
                start[1],
                visited=set(),
                n=n,
                m=m,
            )

            random.shuffle(root_candidates)

            # Root must have at least one child.
            root_child_count = random.randint(
                1,
                len(root_candidates),
            )

            root_directions = root_candidates[:root_child_count]

            root_mask = 0

            for direction in root_directions:
                root_mask |= direction

            board[start[0]][start[1]] = root_mask

            # ----------------------------------------------------
            # 3. Grow tree according to tile directions
            # ----------------------------------------------------

            visited = {start}

            queue = deque([
                (start, root_mask)
            ])

            while queue:

                (row, col), tile_mask = queue.popleft()

                for direction in ALL_DIRECTIONS:

                    # This tile does not contain this connection.
                    if not (tile_mask & direction):
                        continue

                    next_row, next_col = get_neighbor(
                        row,
                        col,
                        direction,
                    )

                    next_cell = (next_row, next_col)

                    # Defensive checks.
                    if not in_bounds(next_row, next_col, n, m):
                        continue

                    if next_cell in visited:
                        continue

                    # ------------------------------------------------
                    # The parent -> child edge is now created.
                    # ------------------------------------------------

                    visited.add(next_cell)

                    # Child must contain the reciprocal connection.
                    parent_direction = OPPOSITE[direction]

                    child_mask = self.choose_tile_with_parent_connection(
                        required_direction=parent_direction,
                        row=next_row,
                        col=next_col,
                        visited=visited,
                        n=n,
                        m=m,
                    )

                    board[next_row][next_col] = child_mask

                    queue.append(
                        (
                            next_cell,
                            child_mask,
                        )
                    )

            # ----------------------------------------------------
            # 4. Did the tree cover the whole board?
            # ----------------------------------------------------

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