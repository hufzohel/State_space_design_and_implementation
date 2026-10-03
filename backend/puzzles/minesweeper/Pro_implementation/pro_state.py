from dataclasses import dataclass


SAFE = 0
MINE = 1


@dataclass(frozen=True)
class Constraint:
    """
    Represents:

        sum(cells) = mines

    where each cell is either SAFE (0) or MINE (1).
    """

    cells: frozenset[int]
    mines: int


@dataclass(frozen=True)
class KnowledgeState:
    """
    Current logical knowledge of the solver.

    assignments:
        cell -> SAFE or MINE

    constraints:
        exact mine-count constraints over unresolved cells.
    """

    assignments: dict[int, int]
    constraints: tuple[Constraint, ...]