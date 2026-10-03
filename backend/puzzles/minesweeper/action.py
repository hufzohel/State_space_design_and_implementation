from dataclasses import dataclass


@dataclass(frozen=True)
class RevealAction:
    cell: int


@dataclass(frozen=True)
class FlagAction:
    cell: int


@dataclass(frozen=True)
class UnflagAction:
    cell: int