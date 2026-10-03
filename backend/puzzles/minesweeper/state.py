UNKNOWN = -1
FLAGGED = -2

REVEALED_MIN = 0
REVEALED_MAX = 8


def index_of(row, col, cols):
    return row * cols + col


def row_col(index, cols):
    return divmod(index, cols)


def in_bounds(row, col, rows, cols):
    return 0 <= row < rows and 0 <= col < cols


def neighbors(index, rows, cols):
    row, col = row_col(index, cols)

    result = []

    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue

            nr = row + dr
            nc = col + dc

            if in_bounds(nr, nc, rows, cols):
                result.append(index_of(nr, nc, cols))

    return result


def is_unknown(value):
    return value == UNKNOWN


def is_flagged(value):
    return value == FLAGGED


def is_revealed(value):
    return REVEALED_MIN <= value <= REVEALED_MAX