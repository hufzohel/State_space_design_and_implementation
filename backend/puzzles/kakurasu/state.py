from dataclasses import dataclass

UNKNOWN = -1
WHITE = 0
BLACK = 1


@dataclass(frozen=True)
class KakurasuState:
    cells: tuple[int, ...]

    def __post_init__(self):
        # Ensure the state is immutable and hashable for visited sets.
        if not isinstance(self.cells, tuple):
            object.__setattr__(self, "cells", tuple(self.cells))