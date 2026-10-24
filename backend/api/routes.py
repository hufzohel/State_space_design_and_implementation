import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from puzzles.pipes.generator import PuzzleGenerator
from puzzles.pipes.problem import PipesProblem
from search.dfs import DFSSolver


router = APIRouter(prefix="/api")


class PipesNewRequest(BaseModel):
    rows: int = 2
    cols: int = 2


class PipesSolveRequest(BaseModel):
    puzzle_id: str
    algorithm: str


PIPES_PUZZLES = {}


def pipes_state_to_grid(state, rows, cols):
    return [
        list(state[row * cols:(row + 1) * cols])
        for row in range(rows)
    ]


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

    generator = PuzzleGenerator()

    for _ in range(100):
        puzzle, _solution = generator.generate_puzzle(
            request.rows,
            request.cols,
        )
        problem = PipesProblem(puzzle)

        if not problem.is_goal(problem.initial_state):
            break
    else:
        raise HTTPException(
            status_code=500,
            detail="Could not generate an unsolved Pipes puzzle."
        )

    puzzle_id = str(uuid4())
    PIPES_PUZZLES[puzzle_id] = {
        "puzzle_type": "pipes",
        "rows": request.rows,
        "cols": request.cols,
        "state": puzzle,
    }

    return {
        "puzzle_id": puzzle_id,
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
    puzzle = [row[:] for row in puzzle_data["state"]]
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


# ============================================================
# Minesweeper
# ============================================================

@router.post("/minesweeper/new")
def new_minesweeper():
    # TODO:
    # Connect this to backend/puzzles/minesweeper/generator.py
    raise HTTPException(
        status_code=501,
        detail="Minesweeper generator has not been implemented yet."
    )


@router.post("/minesweeper/solve")
def solve_minesweeper():
    # TODO:
    # Connect this to:
    #   backend/puzzles/minesweeper/puzzle.py
    #   backend/search/
    raise HTTPException(
        status_code=501,
        detail="Minesweeper solver has not been implemented yet."
    )
