
from dataclasses import dataclass

from backend.puzzles.minesweeper.Pro_implementation.pro_state import (
    SAFE,
    MINE,
    Constraint,
    KnowledgeState,
)


@dataclass
class PropagationResult:
    state: KnowledgeState | None
    steps: list[dict]
    contradiction: bool


class ConstraintPropagator:

    def propagate(self, state):
        """
        Propagate exact mine-count constraints to a fixed point.

        Preserves the KnowledgeState interface:
            assignments: cell -> SAFE or MINE
            constraints: tuple[Constraint, ...]

        Returns PropagationResult containing the final state,
        an ordered reasoning log, and contradiction status.
        """
        assignments = dict(state.assignments)
        constraints = list(state.constraints)
        steps = []

        # Relations are internal to this propagation run.
        # Each pair means that both cells have the same value.
        equalities = set()

        def constraint_data(c):
            return {
                "cells": sorted(c.cells),
                "mines": c.mines,
            }

        def record(kind, **details):
            steps.append({"type": kind, **details})

        def contradiction(reason, **details):
            record(
                "contradiction",
                reason=reason,
                assignments=dict(assignments),
                **details,
            )
            return PropagationResult(
                state=None,
                steps=steps,
                contradiction=True,
            )

        def assign(cell, value, reason, **details):
            """Assign a cell, detecting conflicts and logging new facts."""
            if cell in assignments:
                if assignments[cell] != value:
                    return False, {
                        "cell": cell,
                        "existing_assignment": assignments[cell],
                        "expected_assignment": value,
                        **details,
                    }
                return True, None

            assignments[cell] = value
            record(
                "assignment",
                cell=cell,
                value=value,
                value_name="SAFE" if value == SAFE else "MINE",
                reason=reason,
                **details,
            )
            return True, None

        record(
            "start",
            assignments=dict(assignments),
            constraints=[constraint_data(c) for c in constraints],
        )

        # Validate the initial knowledge before deriving anything.
        for c in constraints:
            if c.mines < 0 or c.mines > len(c.cells):
                return contradiction(
                    "invalid_initial_constraint",
                    constraint=constraint_data(c),
                )

        changed = True
        iteration = 0

        while changed:
            iteration += 1
            changed = False

            record(
                "iteration_start",
                iteration=iteration,
                assignment_count=len(assignments),
                constraint_count=len(constraints),
            )

            # ------------------------------------------------
            # 1. Reduce constraints using known assignments.
            # ------------------------------------------------
            reduced = []
            seen_constraints = set()

            for c in constraints:
                remaining_cells = set()
                remaining_mines = c.mines

                for cell in c.cells:
                    if cell not in assignments:
                        remaining_cells.add(cell)
                    elif assignments[cell] == MINE:
                        remaining_mines -= 1

                if (
                    remaining_mines < 0
                    or remaining_mines > len(remaining_cells)
                ):
                    return contradiction(
                        "constraint_inconsistent_after_reduction",
                        constraint=constraint_data(c),
                        remaining_cells=sorted(remaining_cells),
                        remaining_mines=remaining_mines,
                    )

                if not remaining_cells:
                    if remaining_mines != 0:
                        return contradiction(
                            "resolved_constraint_unsatisfied",
                            constraint=constraint_data(c),
                            remaining_mines=remaining_mines,
                        )

                    record(
                        "constraint_resolved",
                        constraint=constraint_data(c),
                    )
                    continue

                reduced_c = Constraint(
                    cells=frozenset(remaining_cells),
                    mines=remaining_mines,
                )

                if reduced_c != c:
                    record(
                        "constraint_reduced",
                        before=constraint_data(c),
                        after=constraint_data(reduced_c),
                    )

                # Duplicate equations add no information.
                if reduced_c not in seen_constraints:
                    reduced.append(reduced_c)
                    seen_constraints.add(reduced_c)

            if reduced != constraints:
                constraints = reduced
                changed = True

            # ------------------------------------------------
            # 2. Direct deductions.
            # ------------------------------------------------
            for c in constraints:
                if c.mines == 0:
                    value = SAFE
                    reason = "all_safe"
                elif c.mines == len(c.cells):
                    value = MINE
                    reason = "all_mines"
                else:
                    continue

                for cell in sorted(c.cells):
                    was_unassigned = cell not in assignments

                    ok, conflict = assign(
                        cell,
                        value,
                        reason,
                        constraint=constraint_data(c),
                    )

                    if not ok:
                        return contradiction(
                            "assignment_conflict",
                            **conflict,
                        )

                    if was_unassigned:
                        changed = True

            # ------------------------------------------------
            # 3. Proper-subset deductions.
            #
            # If A is a subset of B:
            # sum(B - A) = mines(B) - mines(A)
            # ------------------------------------------------
            derived = []
            known = set(constraints)

            for a in constraints:
                for b in constraints:
                    if not a.cells < b.cells:
                        continue

                    difference = b.cells - a.cells
                    mine_count = b.mines - a.mines

                    if (
                        mine_count < 0
                        or mine_count > len(difference)
                    ):
                        return contradiction(
                            "invalid_subset_deduction",
                            subset=constraint_data(a),
                            superset=constraint_data(b),
                            derived_cells=sorted(difference),
                            derived_mines=mine_count,
                        )

                    candidate = Constraint(
                        cells=frozenset(difference),
                        mines=mine_count,
                    )

                    if candidate not in known:
                        known.add(candidate)
                        derived.append(candidate)

                        record(
                            "constraint_derived",
                            reason="subset",
                            constraint=constraint_data(candidate),
                            from_constraints=[
                                constraint_data(a),
                                constraint_data(b),
                            ],
                        )

            if derived:
                constraints.extend(derived)
                changed = True

            # ------------------------------------------------
            # 4. Coupled-cell deductions.
            #
            # For constraints A and B, their shared cells cancel:
            #
            # sum(A - B) - sum(B - A) = mines(A) - mines(B)
            #
            # When each difference contains one cell, this
            # determines equality or the values of both cells.
            # ------------------------------------------------
            for a in constraints:
                for b in constraints:
                    if a is b:
                        continue

                    a_only = a.cells - b.cells
                    b_only = b.cells - a.cells

                    if len(a_only) != 1 or len(b_only) != 1:
                        continue

                    x = next(iter(a_only))
                    y = next(iter(b_only))
                    delta = a.mines - b.mines

                    # x - y = delta, with x,y in {0,1}.
                    if delta not in (-1, 0, 1):
                        return contradiction(
                            "impossible_coupled_equations",
                            first=constraint_data(a),
                            second=constraint_data(b),
                            cells=[x, y],
                            difference=delta,
                        )

                    if delta == 0:
                        # x = y. Record each pair only once.
                        pair = (min(x, y), max(x, y))

                        if pair not in equalities:
                            equalities.add(pair)
                            record(
                                "cells_equivalent",
                                cells=list(pair),
                                reason="overlapping_constraints",
                                from_constraints=[
                                    constraint_data(a),
                                    constraint_data(b),
                                ],
                            )

                    else:
                        # x - y = 1 -> x is a mine, y is safe.
                        # x - y = -1 -> x is safe, y is a mine.
                        x_value = MINE if delta == 1 else SAFE
                        y_value = SAFE if delta == 1 else MINE

                        for cell, value in (
                            (x, x_value),
                            (y, y_value),
                        ):
                            was_unassigned = cell not in assignments

                            ok, conflict = assign(
                                cell,
                                value,
                                "coupled_constraints",
                                cells=[x, y],
                                difference=delta,
                                from_constraints=[
                                    constraint_data(a),
                                    constraint_data(b),
                                ],
                            )

                            if not ok:
                                return contradiction(
                                    "coupled_assignment_conflict",
                                    **conflict,
                                )

                            if was_unassigned:
                                changed = True

            # ------------------------------------------------
            # 5. Propagate equality relationships.
            # ------------------------------------------------
            for x, y in sorted(equalities):
                x_value = assignments.get(x)
                y_value = assignments.get(y)

                if (
                    x_value is not None
                    and y_value is not None
                    and x_value != y_value
                ):
                    return contradiction(
                        "equivalent_cells_conflict",
                        cells=[x, y],
                        x_value=x_value,
                        y_value=y_value,
                    )

                if x_value is not None and y_value is None:
                    ok, conflict = assign(
                        y,
                        x_value,
                        "equivalent_cell",
                        related_cell=x,
                    )
                    if not ok:
                        return contradiction(
                            "equivalent_cell_conflict",
                            **conflict,
                        )
                    changed = True

                elif y_value is not None and x_value is None:
                    ok, conflict = assign(
                        x,
                        y_value,
                        "equivalent_cell",
                        related_cell=y,
                    )
                    if not ok:
                        return contradiction(
                            "equivalent_cell_conflict",
                            **conflict,
                        )
                    changed = True

            record(
                "iteration_end",
                iteration=iteration,
                assignments=dict(assignments),
                constraints=[constraint_data(c) for c in constraints],
                equalities=[list(pair) for pair in sorted(equalities)],
                changed=changed,
            )

        final_state = KnowledgeState(
            assignments=assignments,
            constraints=tuple(constraints),
        )

        record(
            "complete",
            status="fixed_point",
            assignments=dict(assignments),
            constraints=[constraint_data(c) for c in constraints],
            equalities=[list(pair) for pair in sorted(equalities)],
        )

        return PropagationResult(
            state=final_state,
            steps=steps,
            contradiction=False,
        )
