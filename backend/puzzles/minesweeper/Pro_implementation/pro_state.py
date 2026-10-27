
from dataclasses import dataclass

SAFE = 0
MINE = 1


@dataclass(frozen=True)
class Constraint:
    """
    Represents the exact equation:

        sum(cells) = mines

    Each cell is binary:
        SAFE = 0
        MINE = 1
    """
    cells: frozenset[int]
    mines: int

    def __post_init__(self):
        object.__setattr__(self, "cells", frozenset(self.cells))

        if not isinstance(self.mines, int) or isinstance(self.mines, bool):
            raise TypeError("Constraint.mines must be an integer")

        if not self.cells:
            if self.mines != 0:
                raise ValueError(
                    "An empty constraint must have zero mines"
                )
        elif not 0 <= self.mines <= len(self.cells):
            raise ValueError(
                "Mine count must be between 0 and the number of cells"
            )


@dataclass(frozen=True)
class KnowledgeState:
    """
    Logical state of the solver.

    assignments:
        cell index -> SAFE or MINE

    constraints:
        Exact mine-count equations over unresolved cells.
    """
    assignments: dict[int, int]
    constraints: tuple[Constraint, ...]

    def __post_init__(self):
        assignments = dict(self.assignments)
        constraints = tuple(self.constraints)

        for cell, value in assignments.items():
            if not isinstance(cell, int) or isinstance(cell, bool):
                raise TypeError("Cell indices must be integers")

            if value not in (SAFE, MINE):
                raise ValueError(
                    f"Invalid assignment for cell {cell}: {value}"
                )

        for constraint in constraints:
            if not isinstance(constraint, Constraint):
                raise TypeError(
                    "All constraints must be Constraint instances"
                )

        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "constraints", constraints)
