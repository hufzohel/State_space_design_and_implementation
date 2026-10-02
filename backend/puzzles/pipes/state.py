# ============================================================
# Direction / bit representation
# ============================================================

UP = 8
RIGHT = 4
DOWN = 2
LEFT = 1

DIRECTIONS = {
    UP: (-1, 0),
    RIGHT: (0, 1),
    DOWN: (1, 0),
    LEFT: (0, -1),
}

OPPOSITE = {
    UP: DOWN,
    RIGHT: LEFT,
    DOWN: UP,
    LEFT: RIGHT,
}

ALL_DIRECTIONS = [UP, RIGHT, DOWN, LEFT]


# ============================================================
# Basic helpers
# ============================================================

def rotate_mask(mask, turns=1):
    """
    Rotate a tile clockwise by `turns` 90-degree rotations.

    Bit convention:
        UP    = 8
        RIGHT = 4
        DOWN  = 2
        LEFT  = 1
    """
    turns %= 4

    for _ in range(turns):
        rotated = 0

        if mask & UP:
            rotated |= RIGHT

        if mask & RIGHT:
            rotated |= DOWN

        if mask & DOWN:
            rotated |= LEFT

        if mask & LEFT:
            rotated |= UP

        mask = rotated

    return mask


def possible_rotations(mask):
    """
    Return all distinct orientations of a tile.

    Symmetric tiles naturally produce fewer than 4 orientations.
    For example:
        straight -> 2
        cross    -> 1
    """
    rotations = []

    for turns in range(4):
        rotated = rotate_mask(mask, turns)

        if rotated not in rotations:
            rotations.append(rotated)

    return rotations

def in_bounds(row, col, n, m):
    return 0 <= row < n and 0 <= col < m


def get_neighbor(row, col, direction):
    dr, dc = DIRECTIONS[direction]
    return row + dr, col + dc