import random

from puzzles.minesweeper.state import (
    UNKNOWN,
    neighbors,
)


class MinesweeperGenerator:
    def __init__(self, rows, cols, mine_count, seed=None):
        self.rows = rows
        self.cols = cols
        self.mine_count = mine_count

        self.random = random.Random(seed)

    def generate(self):

        while True:

            mines = self._generate_mines()
            numbers = self._calculate_numbers(mines)

            regions = self._zero_regions(
                mines,
                numbers,
            )

            if regions:
                break

        largest = max(
            regions,
            key=len,
        )

        revealed = set(largest)

        for cell in largest:

            for neighbor in neighbors(
                cell,
                self.rows,
                self.cols,
            ):

                if not mines[neighbor]:
                    revealed.add(neighbor)

        initial_cells = [UNKNOWN] * (
            self.rows * self.cols
        )

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

    def _generate_mines(self):

        total = self.rows * self.cols

        mine_positions = set(
            self.random.sample(
                range(total),
                self.mine_count,
            )
        )

        return tuple(
            index in mine_positions
            for index in range(total)
        )

    def _calculate_numbers(self, mines):

        numbers = [0] * (self.rows * self.cols)

        for index in range(self.rows * self.cols):

            if mines[index]:
                numbers[index] = -2
                continue

            count = 0

            for neighbor in neighbors(
                index,
                self.rows,
                self.cols,
            ):

                if mines[neighbor]:
                    count += 1

            numbers[index] = count

        return tuple(numbers)

    def _zero_regions(self, mines, numbers):

        visited = set()
        regions = []

        for index, number in enumerate(numbers):

            if mines[index]:
                continue

            if number != 0:
                continue

            if index in visited:
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

                    if mines[neighbor]:
                        continue

                    if numbers[neighbor] != 0:
                        continue

                    visited.add(neighbor)
                    stack.append(neighbor)

            regions.append(region)

        return regions

    def _generate_initial_reveal(self, mines, numbers):

        regions = self._zero_regions(
            mines,
            numbers,
        )

        if not regions:
            # Regenerate if there is no zero region.
            return self._regenerate_initial_reveal(
                mines,
                numbers,
            )

        largest = max(
            regions,
            key=len,
        )

        revealed = set(largest)

        # Reveal the numbered boundary surrounding the zero region.
        for cell in largest:

            for neighbor in neighbors(
                cell,
                self.rows,
                self.cols,
            ):

                if mines[neighbor]:
                    continue

                revealed.add(neighbor)

        cells = [UNKNOWN] * (
            self.rows * self.cols
        )

        for cell in revealed:

            if mines[cell]:
                continue

            cells[cell] = numbers[cell]

        return tuple(cells)\

    def _regenerate_initial_reveal(
        self,
        mines,
        numbers,
    ):
        """
        If this random board has no zero region,
        generate another mine configuration.
        """

        new_mines = self._generate_mines()
        new_numbers = self._calculate_numbers(new_mines)

        return self._generate_initial_reveal(
            new_mines,
            new_numbers,
        )