import random

from backend.puzzles.minesweeper.state import (
    UNKNOWN,
    neighbors,
)


class MinesweeperGenerator:
    def __init__(
        self,
        rows,
        cols,
        mine_count,
        seed=None,
        max_zero_region_size=None,
        max_attempts=1000,
    ):
        if rows <= 0 or cols <= 0:
            raise ValueError("Rows and columns must be positive.")

        total = rows * cols

        if not 1 <= mine_count < total:
            raise ValueError("mine_count must be between 1 and rows * cols - 1.")

        if max_zero_region_size is None:
            max_zero_region_size = max(1, total // 4)

        if not 1 <= max_zero_region_size <= total:
            raise ValueError("max_zero_region_size must be between 1 and board size.")

        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")

        self.rows = rows
        self.cols = cols
        self.mine_count = mine_count
        self.max_zero_region_size = max_zero_region_size
        self.max_attempts = max_attempts

        self.random = random.Random(seed)

    def generate(self):
        for _ in range(self.max_attempts):
            mines = self._generate_mines()
            numbers = self._calculate_numbers(mines)
            regions = self._zero_regions(mines, numbers)

            # A board needs at least one zero region.
            if not regions:
                continue

            largest = max(regions, key=len)

            # Reject boards whose largest zero region is too large.
            if len(largest) > self.max_zero_region_size:
                continue

            revealed = set(largest)

            # Reveal the safe numbered boundary around the region.
            for cell in largest:
                for neighbor in neighbors(
                    cell,
                    self.rows,
                    self.cols,
                ):
                    if not mines[neighbor]:
                        revealed.add(neighbor)

            initial_cells = [UNKNOWN] * (self.rows * self.cols)

            for cell in revealed:
                if not mines[cell]:
                    initial_cells[cell] = numbers[cell]

            return {
                "rows": self.rows,
                "cols": self.cols,
                "mines": mines,
                "numbers": numbers,
                "initial_cells": tuple(initial_cells),
            }

        raise RuntimeError(
            f"Could not generate a board with a largest zero region "
            f"of at most {self.max_zero_region_size} cells after "
            f"{self.max_attempts} attempts. Try increasing "
            f"max_zero_region_size or max_attempts."
        )

    def generate_for_click(self, first_cell, max_attempts=3000):
        """Build a no-guess mine layout AFTER the player's first click."""
        from backend.puzzles.minesweeper.action import RevealAction
        from backend.puzzles.minesweeper.environment import (
            MinesweeperEnvironment,
            MinesweeperState as EnvState,
        )
        from backend.puzzles.minesweeper.problem import (
            MinesweeperProblem,
            MinesweeperState as ProblemState,
        )

        total = self.rows * self.cols

        if not 0 <= first_cell < total:
            raise ValueError("first_cell is outside the board.")

        safe_zone = {first_cell, *neighbors(first_cell, self.rows, self.cols)}
        candidates = [c for c in range(total) if c not in safe_zone]

        if self.mine_count > len(candidates):
            raise ValueError("Too many mines for a safe first click.")

        blank = tuple([UNKNOWN] * total)

        for _ in range(max_attempts):
            mine_set = set(self.random.sample(candidates, self.mine_count))
            mines = tuple(i in mine_set for i in range(total))

            env = MinesweeperEnvironment(self.rows, self.cols, mine_set)
            problem = MinesweeperProblem(self.rows, self.cols, ProblemState(blank))

            state = env.execute(EnvState(blank), RevealAction(first_cell))

            while not env.is_win(state):
                forced = problem.forced_actions(state)
                if not forced:
                    break
                for action in forced:
                    state = env.execute(state, action)

            if env.is_win(state):
                return {
                    "rows": self.rows,
                    "cols": self.cols,
                    "mines": mines,
                    "numbers": self._calculate_numbers(mines),
                    "first_cell": first_cell,
                }

        raise RuntimeError(
            "Could not generate a board solvable without guessing. "
            "Try fewer mines or a smaller board."
        )

    def _generate_mines(self):
        total = self.rows * self.cols

        mine_positions = set(
            self.random.sample(
                range(total),
                self.mine_count,
            )
        )

        return tuple(index in mine_positions for index in range(total))

    def _calculate_numbers(self, mines):
        numbers = [0] * (self.rows * self.cols)

        for index in range(self.rows * self.cols):
            if mines[index]:
                numbers[index] = -2
                continue

            numbers[index] = sum(
                mines[neighbor]
                for neighbor in neighbors(
                    index,
                    self.rows,
                    self.cols,
                )
            )

        return tuple(numbers)

    def _zero_regions(self, mines, numbers):
        visited = set()
        regions = []

        for index, number in enumerate(numbers):
            if mines[index] or number != 0 or index in visited:
                continue

            region = []
            stack = [index]
            visited.add(index)

            while stack:
                cell = stack.pop()
                region.append(cell)

                for neighbor in neighbors(
                    cell,
                    self.rows,
                    self.cols,
                ):
                    if neighbor in visited:
                        continue

                    if mines[neighbor] or numbers[neighbor] != 0:
                        continue

                    visited.add(neighbor)
                    stack.append(neighbor)

            regions.append(region)

        return regions
