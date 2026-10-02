from dataclasses import dataclass


@dataclass(frozen=True)
class RotateAction:
    tile_index: int
    turns: int