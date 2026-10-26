import random

from .state import UNKNOWN


class KakurasuGenerator:
    def __init__(self, rows=5, cols=5, seed=None):
        if rows <= 0 or cols <= 0:
            raise ValueError("Board dimensions must be positive")

        self.rows = rows
        self.cols = cols
        self.seed = seed

    def generate(self):
        rng = random.Random(self.seed)

        # Hidden solution used only to construct the clues.
        solution = tuple(
            rng.randint(0, 1)
            for _ in range(self.rows * self.cols)
        )

        row_targets = []

        for r in range(self.rows):
            total = sum(
                (c + 1) * solution[r * self.cols + c]
                for c in range(self.cols)
            )
            row_targets.append(total)

        col_targets = []

        for c in range(self.cols):
            total = sum(
                (r + 1) * solution[r * self.cols + c]
                for r in range(self.rows)
            )
            col_targets.append(total)

        return {
            "rows": self.rows,
            "cols": self.cols,
            "row_targets": tuple(row_targets),
            "col_targets": tuple(col_targets),
            "initial_cells": (UNKNOWN,) * (self.rows * self.cols),

            # For testing only. Never pass this field to the solver.
            "solution": solution,
        }