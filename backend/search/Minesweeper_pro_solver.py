import random
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
    guess_cell: int | None = None


class ConstraintPropagator:
    """
    Sound constraint-based Minesweeper solver.

    Reasoning:
        1. Validate and reduce constraints.
        2. Apply direct deductions.
        3. Apply subset deductions.
        4. Enumerate satisfying assignments for small connected
           components and infer values shared by every solution.
        5. Repeat until a fixed point is reached.

    If exact enumeration exceeds its configured limits, the solver
    abstains from making deductions from that component.

    A successful result means the knowledge base is consistent and
    propagation has reached a fixed point. It does not necessarily
    mean every board cell has been solved.
    """

    def __init__(
        self,
        max_component_size=20,
        max_search_nodes=500_000,
    ):
        if max_component_size < 1:
            raise ValueError("max_component_size must be positive")

        if max_search_nodes < 1:
            raise ValueError("max_search_nodes must be positive")

        self.max_component_size = max_component_size
        self.max_search_nodes = max_search_nodes

    @staticmethod
    def _constraint_data(c):
        return {
            "cells": sorted(c.cells),
            "mines": c.mines,
        }

    def propagate(self, state, unknown_cells=None):
        assignments = dict(state.assignments)
        constraints = list(state.constraints)
        steps = []

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
            if value not in (SAFE, MINE):
                raise ValueError("Assignment must be SAFE or MINE")

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

        def normalize(raw_constraints):
            """
            Reduce equations using known assignments.

            Identical cell sets with different mine counts are
            contradictory, not merely duplicate constraints.
            """
            by_cells = {}
            normalized = []

            for c in raw_constraints:
                if not isinstance(c, Constraint):
                    raise TypeError(
                        "All constraints must be Constraint instances"
                    )

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
                    return None, {
                        "constraint": self._constraint_data(c),
                        "remaining_cells": sorted(remaining_cells),
                        "remaining_mines": remaining_mines,
                    }

                if not remaining_cells:
                    if remaining_mines != 0:
                        return None, {
                            "constraint": self._constraint_data(c),
                            "remaining_cells": [],
                            "remaining_mines": remaining_mines,
                        }

                    record(
                        "constraint_resolved",
                        constraint=self._constraint_data(c),
                    )
                    continue

                reduced = Constraint(
                    cells=frozenset(remaining_cells),
                    mines=remaining_mines,
                )

                previous = by_cells.get(reduced.cells)

                if previous is not None:
                    if previous != reduced.mines:
                        return None, {
                            "cells": sorted(reduced.cells),
                            "first_mine_count": previous,
                            "second_mine_count": reduced.mines,
                        }

                    # Exact duplicate: no new information.
                    continue

                by_cells[reduced.cells] = reduced.mines
                normalized.append(reduced)

                if reduced != c:
                    record(
                        "constraint_reduced",
                        before=self._constraint_data(c),
                        after=self._constraint_data(reduced),
                    )

            normalized.sort(
                key=lambda c: (
                    len(c.cells),
                    tuple(sorted(c.cells)),
                    c.mines,
                )
            )

            return normalized, None

        def subset_deductions(current):
            """
            If A is a proper subset of B:

                sum(B - A) = mines(B) - mines(A)
            """
            known = {
                (c.cells, c.mines)
                for c in current
            }
            derived = []

            for a in current:
                for b in current:
                    if not a.cells < b.cells:
                        continue

                    difference = b.cells - a.cells
                    mine_count = b.mines - a.mines

                    if (
                        mine_count < 0
                        or mine_count > len(difference)
                    ):
                        return None, {
                            "subset": self._constraint_data(a),
                            "superset": self._constraint_data(b),
                            "derived_cells": sorted(difference),
                            "derived_mines": mine_count,
                        }

                    candidate = Constraint(
                        cells=frozenset(difference),
                        mines=mine_count,
                    )
                    key = (candidate.cells, candidate.mines)

                    if key not in known:
                        known.add(key)
                        derived.append(candidate)

                        record(
                            "constraint_derived",
                            reason="subset",
                            constraint=self._constraint_data(candidate),
                            from_constraints=[
                                self._constraint_data(a),
                                self._constraint_data(b),
                            ],
                        )

            return derived, None

        def connected_components(current):
            """
            Partition unresolved variables into independent
            constraint-connected components.
            """
            cell_to_constraints = {}

            for index, c in enumerate(current):
                for cell in c.cells:
                    cell_to_constraints.setdefault(cell, []).append(index)

            unseen = set(cell_to_constraints)
            components = []

            while unseen:
                start = min(unseen)
                stack = [start]
                component_cells = set()
                component_constraints = set()

                while stack:
                    cell = stack.pop()

                    if cell in component_cells:
                        continue

                    component_cells.add(cell)
                    unseen.discard(cell)

                    for index in cell_to_constraints[cell]:
                        if index in component_constraints:
                            continue

                        component_constraints.add(index)

                        for neighbor in current[index].cells:
                            if neighbor not in component_cells:
                                stack.append(neighbor)

                components.append(
                    (
                        component_cells,
                        [current[i] for i in sorted(component_constraints)],
                    )
                )

            return components

        def enumerate_component(cells, component_constraints):
            """
            Enumerate satisfying binary assignments for one component.

            Returns:
                (forced_assignments, contradiction, complete)

            If the search limit is reached, complete=False. In that
            case, no deductions are taken from partial enumeration.
            """
            ordered_cells = sorted(cells)
            cell_set = set(ordered_cells)

            local_constraints = []

            for c in component_constraints:
                indices = tuple(
                    ordered_cells.index(cell)
                    for cell in sorted(c.cells)
                )
                local_constraints.append((indices, c.mines))

            containing = [[] for _ in ordered_cells]

            for ci, (indices, target) in enumerate(local_constraints):
                for index in indices:
                    containing[index].append(ci)

            values = [-1] * len(ordered_cells)
            current_mines = [0] * len(local_constraints)
            remaining = [
                len(indices)
                for indices, _ in local_constraints
            ]

            nodes = 0
            solutions = 0
            forced = [None] * len(ordered_cells)
            aborted = False

            def search(depth):
                nonlocal nodes, solutions, aborted

                if aborted:
                    return

                nodes += 1

                if nodes > self.max_search_nodes:
                    aborted = True
                    return

                if depth == len(ordered_cells):
                    solutions += 1

                    for i, value in enumerate(values):
                        if forced[i] is None:
                            forced[i] = value
                        elif forced[i] != value:
                            forced[i] = -2

                    return

                for value in (SAFE, MINE):
                    values[depth] = value
                    valid = True
                    touched = containing[depth]

                    for ci in touched:
                        remaining[ci] -= 1
                        current_mines[ci] += value

                        target = local_constraints[ci][1]

                        if (
                            current_mines[ci] > target
                            or current_mines[ci] + remaining[ci] < target
                        ):
                            valid = False

                    if valid:
                        search(depth + 1)

                    for ci in touched:
                        current_mines[ci] -= value
                        remaining[ci] += 1

                    if aborted:
                        return

                values[depth] = -1

            search(0)

            if aborted:
                record(
                    "enumeration_skipped",
                    reason="search_limit",
                    cells=ordered_cells,
                    nodes=nodes,
                )
                return {}, False, False

            if solutions == 0:
                return {}, True, True

            forced_assignments = {
                ordered_cells[i]: forced[i]
                for i in range(len(ordered_cells))
                if forced[i] in (SAFE, MINE)
            }

            record(
                "enumeration_complete",
                cells=ordered_cells,
                solutions=solutions,
                forced_assignments=dict(forced_assignments),
            )

            return forced_assignments, False, True

        record(
            "start",
            assignments=dict(assignments),
            constraints=[
                self._constraint_data(c) for c in constraints
            ],
        )

        # Validate existing assignments and initial equations.
        for c in constraints:
            if c.mines < 0 or c.mines > len(c.cells):
                return contradiction(
                    "invalid_initial_constraint",
                    constraint=self._constraint_data(c),
                )

        # Reject inconsistent equations before starting deduction.
        constraints, error = normalize(constraints)

        if error is not None:
            return contradiction(
                "inconsistent_initial_knowledge",
                **error,
            )

        iteration = 0

        while True:
            iteration += 1
            changed = False

            record(
                "iteration_start",
                iteration=iteration,
                assignment_count=len(assignments),
                constraint_count=len(constraints),
            )

            # 1. Reduce constraints and detect conflicts.
            reduced, error = normalize(constraints)

            if error is not None:
                return contradiction(
                    "constraint_inconsistent_after_reduction",
                    **error,
                )

            if reduced != constraints:
                constraints = reduced
                changed = True

            # 2. Direct deductions.
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
                        constraint=self._constraint_data(c),
                    )

                    if not ok:
                        return contradiction(
                            "assignment_conflict",
                            **conflict,
                        )

                    if was_unassigned:
                        changed = True

            # Newly assigned cells must be reduced before further
            # deductions use the constraints.
            reduced, error = normalize(constraints)

            if error is not None:
                return contradiction(
                    "constraint_inconsistent_after_reduction",
                    **error,
                )

            if reduced != constraints:
                constraints = reduced
                changed = True

            # 3. Proper-subset deductions.
            derived, error = subset_deductions(constraints)

            if error is not None:
                return contradiction(
                    "invalid_subset_deduction",
                    **error,
                )

            if derived:
                constraints.extend(derived)
                changed = True

            # 4. Exact enumeration on independent components.
            #    Every forced value is true in every satisfying
            #    assignment of its component.
            for cells, component_constraints in connected_components(
                constraints
            ):
                if len(cells) > self.max_component_size:
                    record(
                        "enumeration_skipped",
                        reason="component_too_large",
                        cells=sorted(cells),
                        size=len(cells),
                    )
                    continue

                forced, impossible, complete = enumerate_component(
                    cells,
                    component_constraints,
                )

                if impossible:
                    return contradiction(
                        "no_satisfying_assignment",
                        cells=sorted(cells),
                        constraints=[
                            self._constraint_data(c)
                            for c in component_constraints
                        ],
                    )

                if not complete:
                    continue

                for cell, value in sorted(forced.items()):
                    was_unassigned = cell not in assignments

                    ok, conflict = assign(
                        cell,
                        value,
                        "exact_component_enumeration",
                        component=sorted(cells),
                    )

                    if not ok:
                        return contradiction(
                            "enumeration_assignment_conflict",
                            **conflict,
                        )

                    if was_unassigned:
                        changed = True

            record(
                "iteration_end",
                iteration=iteration,
                assignments=dict(assignments),
                constraints=[
                    self._constraint_data(c)
                    for c in constraints
                ],
                changed=changed,
            )

            if not changed:
                break

        final_state = KnowledgeState(
            assignments=assignments,
            constraints=tuple(constraints),
        )

        # Fallback recommendation only; never treat a guess as a deduction.
        guess_cell = None

        if unknown_cells is not None:
            candidates = sorted(set(unknown_cells) - set(assignments))

            if candidates:
                guess_cell = random.choice(candidates)
                record(
                    "guess_recommended",
                    cell=guess_cell,
                    reason="propagation_stuck",
                    candidates=len(candidates),
                )

        record(
            "complete",
            status="fixed_point",
            assignments=dict(assignments),
            constraints=[
                self._constraint_data(c) for c in constraints
            ],
            guess_cell=guess_cell,
        )

        return PropagationResult(
            state=final_state,
            steps=steps,
            contradiction=False,
            guess_cell=guess_cell,
        )
