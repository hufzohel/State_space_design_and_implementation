import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from puzzles.minesweeper.generator import MinesweeperGenerator
from puzzles.pipes.action import RotateAction
from puzzles.pipes.generator import PuzzleGenerator
from puzzles.pipes.problem import PipesProblem
from puzzles.pipes.state import possible_rotations
from search.dfs import DFSSolver


router = APIRouter(prefix="/api")


class PipesNewRequest(BaseModel):
    rows: int = 2
    cols: int = 2
    generator: str = "tree"


class PipesSolveRequest(BaseModel):
    puzzle_id: str
    algorithm: str
    state: Optional[list[list[int]]] = None


class PipesRotateRequest(BaseModel):
    puzzle_id: str
    state: list[list[int]]
    tile_index: int
    turns: int = 1


class MinesweeperNewRequest(BaseModel):
    rows: int = 5
    cols: int = 5
    mine_count: int = 3


PIPES_PUZZLES = {}
MINESWEEPER_PUZZLES = {}


def pipes_state_to_grid(state, rows, cols):
    return [
        list(state[row * cols:(row + 1) * cols])
        for row in range(rows)
    ]


def validate_pipes_state(state, puzzle_data):
    rows = puzzle_data["rows"]
    cols = puzzle_data["cols"]

    if (
        len(state) != rows
        or any(len(row) != cols for row in state)
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Pipes state must have shape {rows}x{cols}."
        )

    original_state = puzzle_data["state"]

    for row in range(rows):
        for col in range(cols):
            mask = state[row][col]
            original_mask = original_state[row][col]

            if mask not in possible_rotations(original_mask):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Pipes state contains a tile that is not a "
                        "rotation of the original puzzle."
                    )
                )

    return [row[:] for row in state]


# ============================================================
# General
# ============================================================

@router.get("/status")
def status():
    return {
        "status": "ok"
    }


# ============================================================
# Pipes
# ============================================================

@router.post("/pipes/new")
def new_pipes(request: Optional[PipesNewRequest] = None):
    if request is None:
        request = PipesNewRequest()

    if request.rows != 2 or request.cols != 2:
        raise HTTPException(
            status_code=422,
            detail="Only 2x2 Pipes puzzles are supported."
        )

    if request.generator not in {"tree", "tile"}:
        raise HTTPException(
            status_code=400,
            detail="Only the tree and tile generators are supported."
        )

    generator = PuzzleGenerator()
    start_time = time.perf_counter()

    for _ in range(100):
        puzzle, generated_solution = generator.generate_puzzle(
            request.rows,
            request.cols,
            method=request.generator,
        )
        problem = PipesProblem(puzzle)
        solution_state = PipesProblem(generated_solution).initial_state

        if (
            not problem.is_goal(problem.initial_state)
            and problem.is_goal(solution_state)
        ):
            break
    else:
        raise HTTPException(
            status_code=500,
            detail="Could not generate a solvable, unsolved Pipes puzzle."
        )

    generation_time = time.perf_counter() - start_time

    puzzle_id = str(uuid4())
    PIPES_PUZZLES[puzzle_id] = {
        "puzzle_type": "pipes",
        "rows": request.rows,
        "cols": request.cols,
        "state": puzzle,
        "generator": request.generator,
    }

    return {
        "puzzle_id": puzzle_id,
        "generation_time_seconds": generation_time,
        **PIPES_PUZZLES[puzzle_id],
    }


@router.post("/pipes/solve")
def solve_pipes(request: PipesSolveRequest):
    puzzle_data = PIPES_PUZZLES.get(request.puzzle_id)

    if puzzle_data is None:
        raise HTTPException(
            status_code=404,
            detail="Pipes puzzle not found."
        )

    if request.algorithm != "dfs":
        raise HTTPException(
            status_code=400,
            detail="Only the dfs algorithm is supported."
        )

    rows = puzzle_data["rows"]
    cols = puzzle_data["cols"]
    if request.state is None:
        puzzle = [row[:] for row in puzzle_data["state"]]
    else:
        puzzle = validate_pipes_state(
            request.state,
            puzzle_data,
        )

    problem = PipesProblem(puzzle)
    solver = DFSSolver(problem)

    start_time = time.perf_counter()
    search_result = solver.solve()
    execution_time = time.perf_counter() - start_time

    if search_result is None:
        return {
            "puzzle_id": request.puzzle_id,
            "puzzle_type": "pipes",
            "algorithm": "dfs",
            "solution_found": False,
            "states": [],
            "actions": [],
            "steps": 0,
            "expanded_nodes": None,
            "execution_time_seconds": execution_time,
        }

    states = search_result.states
    actions = search_result.actions

    if not states or states[0] != problem.initial_state:
        raise HTTPException(
            status_code=500,
            detail="DFS returned an invalid initial state."
        )

    if not problem.is_goal(states[-1]):
        raise HTTPException(
            status_code=500,
            detail="DFS returned an invalid final state."
        )

    if len(actions) != len(states) - 1:
        raise HTTPException(
            status_code=500,
            detail="DFS returned inconsistent action and state counts."
        )

    for state, action, next_state in zip(states, actions, states[1:]):
        if problem.result(state, action) != next_state:
            raise HTTPException(
                status_code=500,
                detail="DFS returned an inconsistent solution path."
            )

    return {
        "puzzle_id": request.puzzle_id,
        "puzzle_type": "pipes",
        "algorithm": "dfs",
        "solution_found": True,
        "states": [
            pipes_state_to_grid(state, rows, cols)
            for state in states
        ],
        "actions": [
            {
                "tile_index": action.tile_index,
                "turns": action.turns,
            }
            for action in actions
        ],
        "steps": len(actions),
        "expanded_nodes": search_result.expanded_nodes,
        "execution_time_seconds": execution_time,
    }


@router.post("/pipes/rotate")
def rotate_pipes(request: PipesRotateRequest):
    puzzle_data = PIPES_PUZZLES.get(request.puzzle_id)

    if puzzle_data is None:
        raise HTTPException(
            status_code=404,
            detail="Pipes puzzle not found."
        )

    if request.turns not in {1, 2, 3}:
        raise HTTPException(
            status_code=422,
            detail="Pipes rotations must be 1, 2, or 3 turns."
        )

    puzzle = validate_pipes_state(request.state, puzzle_data)
    problem = PipesProblem(puzzle)

    if not 0 <= request.tile_index < len(problem.initial_state):
        raise HTTPException(
            status_code=422,
            detail="Pipes tile_index is outside the board."
        )

    action = RotateAction(
        tile_index=request.tile_index,
        turns=request.turns,
    )
    next_state = problem.result(problem.initial_state, action)

    return {
        "puzzle_id": request.puzzle_id,
        "puzzle_type": "pipes",
        "rows": puzzle_data["rows"],
        "cols": puzzle_data["cols"],
        "state": pipes_state_to_grid(
            next_state,
            puzzle_data["rows"],
            puzzle_data["cols"],
        ),
        "action": {
            "tile_index": action.tile_index,
            "turns": action.turns,
        },
        "is_goal": problem.is_goal(next_state),
    }


# ============================================================
# Minesweeper
# ============================================================

@router.post("/minesweeper/new")
def new_minesweeper(
    request: Optional[MinesweeperNewRequest] = None,
):
    if request is None:
        request = MinesweeperNewRequest()

    if (
        request.rows != 5
        or request.cols != 5
        or request.mine_count != 3
    ):
        raise HTTPException(
            status_code=422,
            detail="Only 5x5 Minesweeper puzzles with 3 mines are supported."
        )

    generator = MinesweeperGenerator(
        rows=request.rows,
        cols=request.cols,
        mine_count=request.mine_count,
    )

    start_time = time.perf_counter()
    generated = generator.generate()
    generation_time = time.perf_counter() - start_time

    puzzle_id = str(uuid4())
    mines = frozenset(
        index
        for index, is_mine in enumerate(generated["mines"])
        if is_mine
    )

    MINESWEEPER_PUZZLES[puzzle_id] = {
        "puzzle_type": "minesweeper",
        "rows": request.rows,
        "cols": request.cols,
        "mine_count": request.mine_count,
        "state": generated["initial_cells"],
        "mines": mines,
    }

    return {
        "puzzle_id": puzzle_id,
        "puzzle_type": "minesweeper",
        "rows": request.rows,
        "cols": request.cols,
        "mine_count": request.mine_count,
        "state": pipes_state_to_grid(
            generated["initial_cells"],
            request.rows,
            request.cols,
        ),
        "generation_time_seconds": generation_time,
    }


@router.post("/minesweeper/solve")
def solve_minesweeper():
    raise HTTPException(
        status_code=501,
        detail=(
            "Minesweeper solving is not available because the current "
            "search implementation does not support invalid successors."
        )
    )
