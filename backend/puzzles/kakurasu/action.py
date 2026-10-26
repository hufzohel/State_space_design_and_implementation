from dataclasses import dataclass

from .state import WHITE, BLACK


@dataclass(frozen=True)
class KakurasuAction:
    cell: int
    value: int

    def __post_init__(self):
        if self.value not in (WHITE, BLACK):
            raise ValueError("value must be WHITE (0) or BLACK (1)")