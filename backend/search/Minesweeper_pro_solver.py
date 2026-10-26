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
            KnowledgeState if consistent
            None if a contradiction is found
        """

        assignments = dict(state.assignments)
        constraints = list(state.constraints)

        def contradiction(reason, **details):
            print(f"\n[PROPAGATION CONTRADICTION] {reason}")
            for key, value in details.items():
                print(f"  {key}: {value}")
            print(f"  Current assignments: {assignments}")
            return None

        changed = True
        iteration = 0

        while changed:
            iteration += 1
            changed = False

            print(f"\n[Propagation iteration {iteration}]")
            print(f"  Assignments so far: {len(assignments)}")
            print(f"  Constraints to process: {len(constraints)}")

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

                if remaining_mines < 0:
                    return contradiction(
                        "Negative remaining mine count after reduction",
                        constraint=constraint,
                        remaining_cells=sorted(remaining_cells),
                        original_mines=constraint.mines,
                        remaining_mines=remaining_mines,
                    )

                if remaining_mines > len(remaining_cells):
                    return contradiction(
                        "More remaining mines than unresolved cells",
                        constraint=constraint,
                        remaining_cells=sorted(remaining_cells),
                        remaining_cell_count=len(remaining_cells),
                        remaining_mines=remaining_mines,
                    )

                if not remaining_cells:
                    if remaining_mines != 0:
                        return contradiction(
                            "Fully resolved constraint is unsatisfied",
                            constraint=constraint,
                            remaining_mines=remaining_mines,
                        )
                    continue

                reduced_constraint = Constraint(
                    frozenset(remaining_cells),
                    remaining_mines,
                )
                reduced.append(reduced_constraint)

            constraints = reduced

            # ------------------------------------------------
            # 2. Direct deductions
            # ------------------------------------------------

            for constraint in constraints:
                cells = constraint.cells
                mines = constraint.mines

                if mines == 0:
                    # All cells must be safe.
                    for cell in cells:
                        if cell in assignments:
                            if assignments[cell] != SAFE:
                                return contradiction(
                                    "Safe deduction conflicts with existing assignment",
                                    constraint=constraint,
                                    cell=cell,
                                    existing_assignment=assignments[cell],
                                    expected=SAFE,
                                )
                        else:
                            assignments[cell] = SAFE
                            changed = True

                elif mines == len(cells):
                    # All cells must be mines.
                    for cell in cells:
                        if cell in assignments:
                            if assignments[cell] != MINE:
                                return contradiction(
                                    "Mine deduction conflicts with existing assignment",
                                    constraint=constraint,
                                    cell=cell,
                                    existing_assignment=assignments[cell],
                                    expected=MINE,
                                )
                        else:
                            assignments[cell] = MINE
                            changed = True

            # ------------------------------------------------
            # 3. Subset deduction
            # ------------------------------------------------

            derived = []
            existing_constraints = set(constraints)

            for a in constraints:
                for b in constraints:
                    # Only derive when A is a proper subset of B.
                    if not a.cells < b.cells:
                        continue

                    difference = b.cells - a.cells
                    mines = b.mines - a.mines

                    if mines < 0:
                        return contradiction(
                            "Subset deduction produces a negative mine count",
                            subset_constraint=a,
                            superset_constraint=b,
                            derived_cells=sorted(difference),
                            derived_mines=mines,
                        )

                    if mines > len(difference):
                        return contradiction(
                            "Subset deduction produces too many mines",
                            subset_constraint=a,
                            superset_constraint=b,
                            derived_cells=sorted(difference),
                            derived_mines=mines,
                            derived_cell_count=len(difference),
                        )

                    candidate = Constraint(
                        frozenset(difference),
                        mines,
                    )

                    if candidate not in existing_constraints:
                        derived.append(candidate)
                        existing_constraints.add(candidate)

            if derived:
                constraints.extend(derived)
                changed = True

        return KnowledgeState(
            assignments=assignments,
            constraints=tuple(constraints),
        )
