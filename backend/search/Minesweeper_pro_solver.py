from backend.puzzles.minesweeper.Pro_implementation.pro_state import (
    SAFE,
    MINE,
    Constraint,
    KnowledgeState,
)


class ConstraintPropagator:

    def propagate(self, state):
        """
        Repeatedly derive everything that follows from the
        current constraints.

        Returns:
            KnowledgeState
                if consistent

            None
                if a contradiction is found
        """

        assignments = dict(state.assignments)
        constraints = list(state.constraints)

        changed = True

        while changed:
            changed = False

            # ------------------------------------------------
            # 1. Reduce constraints using known assignments
            # ------------------------------------------------

            reduced = []

            for constraint in constraints:
                remaining_cells = set()
                remaining_mines = constraint.mines

                for cell in constraint.cells:

                    if cell not in assignments:
                        remaining_cells.add(cell)

                    elif assignments[cell] == MINE:
                        remaining_mines -= 1

                # --------------------------------------------
                # Contradiction
                # --------------------------------------------

                if remaining_mines < 0:
                    return None

                if remaining_mines > len(remaining_cells):
                    return None

                # --------------------------------------------
                # Fully resolved constraint
                # --------------------------------------------

                if not remaining_cells:

                    if remaining_mines != 0:
                        return None

                    continue

                reduced.append(
                    Constraint(
                        frozenset(remaining_cells),
                        remaining_mines,
                    )
                )

            constraints = reduced

            # ------------------------------------------------
            # 2. Direct deductions
            # ------------------------------------------------

            for constraint in constraints:

                cells = constraint.cells
                mines = constraint.mines

                # 0 mines remaining:
                #
                #     A + B + C = 0
                #
                # therefore:
                #
                #     A = B = C = SAFE

                if mines == 0:

                    for cell in cells:

                        if cell in assignments:

                            if assignments[cell] != SAFE:
                                return None

                        else:
                            assignments[cell] = SAFE
                            changed = True

                # Every remaining cell must be a mine:
                #
                #     A + B + C = 3
                #
                # therefore:
                #
                #     A = B = C = MINE

                elif mines == len(cells):

                    for cell in cells:

                        if cell in assignments:

                            if assignments[cell] != MINE:
                                return None

                        else:
                            assignments[cell] = MINE
                            changed = True

            # ------------------------------------------------
            # 3. Subset deduction
            # ------------------------------------------------

            derived = []

            for a in constraints:

                for b in constraints:

                    if a.cells >= b.cells:
                        continue

                    # A ⊂ B
                    #
                    # A = x
                    # B = y
                    #
                    # therefore:
                    #
                    # B-A = y-x

                    difference = b.cells - a.cells
                    mines = b.mines - a.mines

                    # Impossible derived constraint.
                    if mines < 0:
                        return None

                    if mines > len(difference):
                        return None

                    candidate = Constraint(
                        frozenset(difference),
                        mines,
                    )

                    if candidate not in constraints:
                        derived.append(candidate)

            if derived:
                constraints.extend(derived)
                changed = True

        return KnowledgeState(
            assignments=assignments,
            constraints=tuple(constraints),
        )