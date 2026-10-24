import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from api.routes import (  # noqa: E402
    MINESWEEPER_PUZZLES,
    PIPES_PUZZLES,
    MinesweeperNewRequest,
    PipesNewRequest,
    PipesRotateRequest,
    PipesSolveRequest,
    new_minesweeper,
    new_pipes,
    rotate_pipes,
    solve_minesweeper,
    solve_pipes,
)
from puzzles.pipes.action import RotateAction  # noqa: E402
from puzzles.pipes.problem import PipesProblem  # noqa: E402


class ApiRegressionTests(unittest.TestCase):
    def setUp(self):
        PIPES_PUZZLES.clear()
        MINESWEEPER_PUZZLES.clear()

    def test_tree_and_tile_generation_then_dfs(self):
        puzzle_ids = set()

        for method in ("tree", "tile"):
            created = new_pipes(
                PipesNewRequest(rows=2, cols=2, generator=method)
            )
            puzzle_ids.add(created["puzzle_id"])

            self.assertEqual(created["generator"], method)
            self.assertEqual(len(created["state"]), 2)
            self.assertTrue(all(len(row) == 2 for row in created["state"]))
            self.assertFalse(
                PipesProblem(created["state"]).is_goal(
                    PipesProblem(created["state"]).initial_state
                )
            )

            solved = solve_pipes(
                PipesSolveRequest(
                    puzzle_id=created["puzzle_id"],
                    algorithm="dfs",
                    state=created["state"],
                )
            )
            self.assertTrue(solved["solution_found"])
            self.assertEqual(solved["states"][0], created["state"])
            self.assertEqual(solved["steps"], len(solved["actions"]))
            self.assertEqual(solved["steps"], len(solved["states"]) - 1)

            problem = PipesProblem(created["state"])
            flat_states = [
                tuple(value for row in state for value in row)
                for state in solved["states"]
            ]
            for state, action_data, next_state in zip(
                flat_states,
                solved["actions"],
                flat_states[1:],
            ):
                action = RotateAction(**action_data)
                self.assertEqual(problem.result(state, action), next_state)
            self.assertTrue(problem.is_goal(flat_states[-1]))

        self.assertEqual(len(puzzle_ids), 2)

    def test_human_rotation_validation_and_visible_state_solve(self):
        created = new_pipes(PipesNewRequest())
        puzzle_id = created["puzzle_id"]

        rotated = rotate_pipes(
            PipesRotateRequest(
                puzzle_id=puzzle_id,
                state=created["state"],
                tile_index=0,
                turns=1,
            )
        )
        self.assertNotEqual(rotated["state"], created["state"])
        self.assertEqual(
            rotated["action"],
            {"tile_index": 0, "turns": 1},
        )

        from_visible_state = solve_pipes(
            PipesSolveRequest(
                puzzle_id=puzzle_id,
                algorithm="dfs",
                state=rotated["state"],
            )
        )
        self.assertEqual(from_visible_state["states"][0], rotated["state"])

        from_stored_state = solve_pipes(
            PipesSolveRequest(puzzle_id=puzzle_id, algorithm="dfs")
        )
        self.assertEqual(from_stored_state["states"][0], created["state"])

        human_state = created["state"]
        final_rotation = None
        for action in from_stored_state["actions"]:
            final_rotation = rotate_pipes(
                PipesRotateRequest(
                    puzzle_id=puzzle_id,
                    state=human_state,
                    tile_index=action["tile_index"],
                    turns=action["turns"],
                )
            )
            human_state = final_rotation["state"]

        self.assertIsNotNone(final_rotation)
        self.assertTrue(final_rotation["is_goal"])
        self.assertEqual(human_state, from_stored_state["states"][-1])

        invalid_state = [row[:] for row in created["state"]]
        invalid_state[0][0] = 0
        with self.assertRaises(HTTPException) as context:
            solve_pipes(
                PipesSolveRequest(
                    puzzle_id=puzzle_id,
                    algorithm="dfs",
                    state=invalid_state,
                )
            )
        self.assertEqual(context.exception.status_code, 422)

    def test_api_errors(self):
        created = new_pipes(PipesNewRequest())

        cases = (
            (
                lambda: new_pipes(PipesNewRequest(rows=3, cols=3)),
                422,
            ),
            (
                lambda: new_pipes(PipesNewRequest(generator="unknown")),
                400,
            ),
            (
                lambda: solve_pipes(
                    PipesSolveRequest(
                        puzzle_id=created["puzzle_id"],
                        algorithm="astar",
                    )
                ),
                400,
            ),
            (
                lambda: solve_pipes(
                    PipesSolveRequest(
                        puzzle_id="missing",
                        algorithm="dfs",
                    )
                ),
                404,
            ),
            (
                lambda: rotate_pipes(
                    PipesRotateRequest(
                        puzzle_id=created["puzzle_id"],
                        state=created["state"],
                        tile_index=99,
                    )
                ),
                422,
            ),
        )

        for operation, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                with self.assertRaises(HTTPException) as context:
                    operation()
                self.assertEqual(
                    context.exception.status_code,
                    expected_status,
                )

    def test_minesweeper_response_keeps_mines_private(self):
        created = new_minesweeper(MinesweeperNewRequest())

        self.assertEqual(
            set(created),
            {
                "puzzle_id",
                "puzzle_type",
                "rows",
                "cols",
                "mine_count",
                "state",
                "generation_time_seconds",
            },
        )
        self.assertNotIn("mines", created)
        self.assertNotIn("numbers", created)
        self.assertEqual(len(created["state"]), 5)
        self.assertTrue(all(len(row) == 5 for row in created["state"]))

        stored = MINESWEEPER_PUZZLES[created["puzzle_id"]]
        self.assertEqual(len(stored["mines"]), 3)

        with self.assertRaises(HTTPException) as context:
            solve_minesweeper()
        self.assertEqual(context.exception.status_code, 501)


if __name__ == "__main__":
    unittest.main()
