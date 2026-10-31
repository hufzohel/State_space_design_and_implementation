import time
from dataclasses import asdict, is_dataclass
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.dispatcher import generate_problem, solve_problem, solve_pipes_puzzle
from backend.puzzles.minesweeper.environment import (
    MinesweeperEnvironment,
    MinesweeperState as EnvironmentState,
)
from backend.puzzles.minesweeper.problem import (
    MinesweeperProblem,
    MinesweeperState,
)
from backend.puzzles.pipes.problem import PipesProblem
from backend.puzzles.kakurasu import KakurasuProblem
from backend.puzzles.pipes.state import possible_rotations
from backend.search.dfs import DFSSolver


router = APIRouter(prefix="/api")

MAX_BOARD_CELLS = 36
MAX_MINESWEEPER_CELLS = 100
MAX_SEARCH_EXPANSIONS = 100_000
MAX_MINESWEEPER_STEPS = 2_000

PIPES_GAMES = {}
MINESWEEPER_GAMES = {}
KAKURASU_GAMES = {}


class PipesNewRequest(BaseModel):
    rows: int = Field(default=3, ge=1, le=6)
    cols: int = Field(default=3, ge=1, le=6)
    generator: str = "tree"


class PipesSolveRequest(BaseModel):
    puzzle_id: str
    algorithm: str = "dfs"
    state: Optional[list[list[int]]] = None
    max_expansions: int = Field(
        default=MAX_SEARCH_EXPANSIONS, ge=1, le=MAX_SEARCH_EXPANSIONS
    )


class PipesRotateRequest(BaseModel):
    puzzle_id: str
    state: list[list[int]]
    tile_index: int = Field(ge=0)
    turns: int = Field(default=1, ge=1, le=3)


class MinesweeperNewRequest(BaseModel):
    rows: int = Field(default=5, ge=2, le=9)
    cols: int = Field(default=5, ge=2, le=9)
    mine_count: int = Field(default=3, ge=1)
    seed: Optional[int] = None


class MinesweeperSolveRequest(BaseModel):
    game_id: str
    algorithm: str = "greedy"
    max_steps: int = Field(
        default=MAX_MINESWEEPER_STEPS, ge=1, le=MAX_MINESWEEPER_STEPS
    )


class MinesweeperActionRequest(BaseModel):
    game_id: str
    action: str
    cell: int = Field(ge=0)


class MinesweeperResetRequest(BaseModel):
    game_id: str


class KakurasuNewRequest(BaseModel):
    rows: int = Field(default=5, ge=2, le=8)
    cols: int = Field(default=5, ge=2, le=8)
    seed: Optional[int] = None


class KakurasuSolveRequest(BaseModel):
    game_id: str
    algorithm: str = "dfs"
    max_steps: int = Field(
        default=MAX_SEARCH_EXPANSIONS, ge=1, le=MAX_SEARCH_EXPANSIONS
    )


def _grid(flat, rows, cols):
    return [list(flat[r * cols : (r + 1) * cols]) for r in range(rows)]


def _action_dict(action):
    if is_dataclass(action):
        return asdict(action)
    return action


def _has_revealed(state):
    return any(v >= 0 for v in state.cells)


def _ensure_board(game, first_cell):
    """Create the mine layout lazily, right after the first click."""
    if game["environment"] is not None and game["first_cell"] == first_cell:
        return
    try:
        generated = generate_problem(
            "minesweeper",
            "random",
            rows=game["rows"],
            cols=game["cols"],
            mine_count=game["mine_count"],
            seed=game["seed"],
            first_cell=first_cell,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(500, str(exc)) from exc

    mines = [i for i, is_mine in enumerate(generated["mines"]) if is_mine]
    game["mines"] = mines
    game["first_cell"] = first_cell
    game["environment"] = MinesweeperEnvironment(game["rows"], game["cols"], mines)
    game["problem"] = MinesweeperProblem(
        game["rows"], game["cols"], MinesweeperState(game["initial"].cells)
    )


def _pipes_validate_state(state, game):
    rows, cols = game["rows"], game["cols"]
    if len(state) != rows or any(len(row) != cols for row in state):
        raise HTTPException(422, f"Pipes state must have shape {rows}x{cols}.")
    original = game["puzzle"]
    for r in range(rows):
        for c in range(cols):
            if state[r][c] not in possible_rotations(original[r][c]):
                raise HTTPException(
                    422,
                    "Pipes state contains a tile that is not a rotation of the original puzzle.",
                )
    return [row[:] for row in state]


def _pipes_result(problem, result, puzzle_id, algorithm, elapsed):
    if result is None:
        return {
            "puzzle_id": puzzle_id,
            "puzzle_type": "pipes",
            "algorithm": algorithm,
            "status": "expansion_limit_or_no_solution",
            "solution_found": False,
            "steps": [],
            "states": [],
            "actions": [],
            "stats": {"expanded": None, "elapsed": elapsed, "cost": None},
            "steps_count": 0,
        }

    if hasattr(result, "found") and not result.found:
        states, actions = [], []
        status = result.status
        stats = {
            "expanded": result.expanded,
            "elapsed": result.elapsed_seconds,
            "cost": None,
        }
    else:
        states, actions = result.states, result.actions
        status = "solved"
        expanded = getattr(result, "expanded_nodes", None)
        if expanded is None:
            expanded = getattr(result, "expanded", None)
        stats = {
            "expanded": expanded,
            "elapsed": getattr(result, "elapsed_seconds", elapsed),
            "cost": getattr(result, "cost", len(actions)),
        }

    states_grid = [_grid(state, problem.rows, problem.cols) for state in states]
    steps = [
        {"state": state, "action": _action_dict(action)}
        for state, action in zip(states_grid[1:], actions)
    ]
    return {
        "puzzle_id": puzzle_id,
        "puzzle_type": "pipes",
        "algorithm": algorithm,
        "status": status,
        "solution_found": status == "solved",
        "steps": steps,
        "states": states_grid,
        "actions": [_action_dict(action) for action in actions],
        "stats": stats,
        "steps_count": len(actions),
    }


def _kakurasu_result(problem, result, puzzle_id, algorithm, elapsed):
    if result is None:
        return {
            "puzzle_id": puzzle_id,
            "puzzle_type": "kakurasu",
            "algorithm": algorithm,
            "status": "expansion_limit_or_no_solution",
            "solution_found": False,
            "steps": [],
            "states": [],
            "actions": [],
            "stats": {"expanded": None, "elapsed": elapsed, "cost": None},
            "steps_count": 0,
        }

    if hasattr(result, "found") and not result.found:
        states, actions = [], []
        status = result.status
        stats = {
            "expanded": result.expanded,
            "elapsed": result.elapsed_seconds,
            "cost": None,
        }
    else:
        states, actions = result.states, result.actions
        status = "solved"
        expanded = getattr(result, "expanded_nodes", None)
        if expanded is None:
            expanded = getattr(result, "expanded", None)
        stats = {
            "expanded": expanded,
            "elapsed": getattr(result, "elapsed_seconds", elapsed),
            "cost": getattr(result, "cost", len(actions)),
        }

    states_grid = [_grid(state.cells, problem.rows, problem.cols) for state in states]
    steps = [
        {"state": state, "action": _action_dict(action)}
        for state, action in zip(states_grid[1:], actions)
    ]
    return {
        "puzzle_id": puzzle_id,
        "puzzle_type": "kakurasu",
        "algorithm": algorithm,
        "status": status,
        "solution_found": status == "solved",
        "steps": steps,
        "states": states_grid,
        "actions": [_action_dict(action) for action in actions],
        "stats": stats,
        "steps_count": len(actions),
    }


@router.get("/status")
def status():
    return {"status": "ok", "service": "AI Search API"}


@router.get("/options")
def options():
    return {
        "pipes": {
            "generators": ["tree", "tile"],
            "solvers": ["dfs", "astar"],
        },
        "minesweeper": {
            "generators": ["random"],
            "solvers": [
                "online_dfs",
                "greedy",
                {"id": "pro", "name": "Pro (constraint)"},
            ],
        },
        "kakurasu": {
            "generators": ["random"],
            "solvers": ["dfs", "astar"],
        },
    }


@router.post("/pipes/new")
def new_pipes(request: PipesNewRequest = PipesNewRequest()):
    if request.rows * request.cols > MAX_BOARD_CELLS:
        raise HTTPException(422, "Pipes board is limited to 16 cells.")
    if request.generator not in {"tree", "tile"}:
        raise HTTPException(400, "generator must be 'tree' or 'tile'.")

    started = time.perf_counter()
    for _ in range(100):
        puzzle, solution = generate_problem(
            "pipes", request.generator, rows=request.rows, cols=request.cols
        )
        problem = PipesProblem(puzzle)
        if not problem.is_goal(problem.initial_state) and PipesProblem(
            solution
        ).is_goal(PipesProblem(solution).initial_state):
            break
    else:
        raise HTTPException(500, "Could not generate an unsolved Pipes puzzle.")

    puzzle_id = str(uuid4())
    PIPES_GAMES[puzzle_id] = {
        "puzzle_type": "pipes",
        "rows": request.rows,
        "cols": request.cols,
        "puzzle": puzzle,
        "generator": request.generator,
    }
    return {
        "puzzle_id": puzzle_id,
        "puzzle_type": "pipes",
        "rows": request.rows,
        "cols": request.cols,
        "state": puzzle,
        "generator": request.generator,
        "generation_time_seconds": time.perf_counter() - started,
    }


@router.post("/pipes/solve")
def solve_pipes(request: PipesSolveRequest):
    game = PIPES_GAMES.get(request.puzzle_id)
    if game is None:
        raise HTTPException(404, "Pipes puzzle not found.")
    if request.algorithm not in {"dfs", "astar"}:
        raise HTTPException(400, "algorithm must be 'dfs' or 'astar'.")

    puzzle = (
        _pipes_validate_state(request.state, game)
        if request.state is not None
        else [row[:] for row in game["puzzle"]]
    )
    problem = PipesProblem(puzzle)
    started = time.perf_counter()
    result = solve_pipes_puzzle(puzzle, request.algorithm, request.max_expansions)
    return _pipes_result(
        problem,
        result,
        request.puzzle_id,
        request.algorithm,
        time.perf_counter() - started,
    )


@router.post("/pipes/rotate")
def rotate_pipes(request: PipesRotateRequest):
    game = PIPES_GAMES.get(request.puzzle_id)
    if game is None:
        raise HTTPException(404, "Pipes puzzle not found.")
    puzzle = _pipes_validate_state(request.state, game)
    problem = PipesProblem(puzzle)
    if request.tile_index >= len(problem.initial_state):
        raise HTTPException(422, "tile_index is outside the board.")
    from backend.puzzles.pipes.action import RotateAction

    action = RotateAction(request.tile_index, request.turns)
    next_state = problem.result(problem.initial_state, action)
    return {
        "puzzle_id": request.puzzle_id,
        "puzzle_type": "pipes",
        "rows": game["rows"],
        "cols": game["cols"],
        "state": _grid(next_state, game["rows"], game["cols"]),
        "action": _action_dict(action),
        "is_goal": problem.is_goal(next_state),
    }


@router.post("/minesweeper/new")
def new_minesweeper(request: MinesweeperNewRequest = MinesweeperNewRequest()):
    if request.rows * request.cols > MAX_MINESWEEPER_CELLS:
        raise HTTPException(422, "Minesweeper board is limited to 64 cells.")
    if request.mine_count >= request.rows * request.cols:
        raise HTTPException(422, "mine_count must be smaller than board size.")

    started = time.perf_counter()
    generated = generate_problem(
        "minesweeper",
        "random",
        rows=request.rows,
        cols=request.cols,
        mine_count=request.mine_count,
        seed=request.seed,
    )
    game_id = str(uuid4())
    mines = [i for i, is_mine in enumerate(generated["mines"]) if is_mine]
    initial = tuple(generated["initial_cells"])
    env = MinesweeperEnvironment(request.rows, request.cols, mines)
    problem = MinesweeperProblem(request.rows, request.cols, MinesweeperState(initial))
    MINESWEEPER_GAMES[game_id] = {
        "puzzle_type": "minesweeper",
        "rows": request.rows,
        "cols": request.cols,
        "mine_count": request.mine_count,
        "mines": mines,
        "environment": env,
        "problem": problem,
        "state": EnvironmentState(initial),
        "initial": EnvironmentState(initial),
    }
    return {
        "game_id": game_id,
        "puzzle_type": "minesweeper",
        "rows": request.rows,
        "cols": request.cols,
        "mine_count": request.mine_count,
        "state": _grid(initial, request.rows, request.cols),
        "generation_time_seconds": time.perf_counter() - started,
    }


def _minesweeper_response(game_id, game, algorithm, steps, status, started):
    state = game["state"]
    response = {
        "game_id": game_id,
        "puzzle_type": "minesweeper",
        "algorithm": algorithm,
        "status": status,
        "steps": steps,
        "state": _grid(state.cells, game["rows"], game["cols"]),
        "stats": {
            "expanded": len(steps),
            "elapsed": time.perf_counter() - started,
            "cost": len(steps),
        },
        "steps_count": len(steps),
    }
    if status == "lost":
        response["mine_positions"] = game["mines"]
    return response


@router.post("/minesweeper/action")
def minesweeper_action(request: MinesweeperActionRequest):
    game = MINESWEEPER_GAMES.get(request.game_id)
    if game is None:
        raise HTTPException(404, "Minesweeper game not found.")
    if request.action not in {"reveal", "flag", "unflag"}:
        raise HTTPException(400, "action must be 'reveal', 'flag' or 'unflag'.")
    if request.cell >= game["rows"] * game["cols"]:
        raise HTTPException(422, "cell is outside the board.")

    from backend.puzzles.minesweeper.action import (
        FlagAction,
        RevealAction,
        UnflagAction,
    )

    if request.action == "flag":
        action = FlagAction(request.cell)
    elif request.action == "unflag":
        action = UnflagAction(request.cell)
    else:
        action = RevealAction(request.cell)

    old = game["state"]
    new = game["environment"].execute(old, action)
    game["state"] = new
    status = (
        "lost"
        if new.lost
        else ("won" if game["environment"].is_win(new) else "playing")
    )
    result = _minesweeper_response(
        request.game_id, game, "human", [], status, time.perf_counter()
    )
    result["action"] = {
        **_action_dict(action),
        "action": request.action,
    }
    return result


@router.post("/minesweeper/reset")
def reset_minesweeper(request: MinesweeperResetRequest):
    game = MINESWEEPER_GAMES.get(request.game_id)
    if game is None:
        raise HTTPException(404, "Minesweeper game not found.")
    game["state"] = game["initial"]
    return {"game_id": request.game_id, "status": "playing"}


def _pro_guess(game, state, knowledge):
    """Pick the least risky unknown cell when pure logic is stuck."""
    unknown = [i for i, v in enumerate(state.cells) if v == -1]
    if not unknown:
        return None

    flagged = sum(1 for v in state.cells if v == -2)
    remaining = max(0, game["mine_count"] - flagged)
    density = remaining / len(unknown)

    # Frontier cells: worst-case mine ratio among the clues touching them.
    risk = {}
    for constraint in knowledge.constraints:
        ratio = constraint.mines / len(constraint.cells)
        for cell in constraint.cells:
            risk[cell] = max(risk.get(cell, 0.0), ratio)

    return min(unknown, key=lambda cell: (risk.get(cell, density), cell))


def _make_pro_chooser(game):
    """Constraint-propagation solver: flags/reveals only what is proven,
    and guesses (lowest risk) only when nothing can be proven."""
    from backend.puzzles.minesweeper.action import FlagAction, RevealAction
    from backend.puzzles.minesweeper.Pro_implementation.pro_problem import (
        ProMinesweeperProblem,
    )
    from backend.puzzles.minesweeper.Pro_implementation.pro_state import MINE, SAFE

    queue = []

    def choose(state):
        # Drop queued actions made unnecessary by flood-fill reveals.
        queue[:] = [a for a in queue if state.cells[a.cell] == -1]
        choose.guessed = False

        if not queue:
            knowledge = ProMinesweeperProblem(
                game["rows"], game["cols"], state.cells
            ).initial_state()
            if knowledge is None:
                return None

            items = sorted(knowledge.assignments.items())
            queue.extend(
                FlagAction(c) for c, v in items if v == MINE and state.cells[c] == -1
            )
            queue.extend(
                RevealAction(c) for c, v in items if v == SAFE and state.cells[c] == -1
            )

            if not queue:
                cell = _pro_guess(game, state, knowledge)
                if cell is None:
                    return None
                choose.guessed = True
                return RevealAction(cell)

        return queue.pop(0)

    choose.guessed = False
    return choose


@router.post("/minesweeper/solve")
def solve_minesweeper(request: MinesweeperSolveRequest):
    game = MINESWEEPER_GAMES.get(request.game_id)
    if game is None:
        raise HTTPException(404, "Minesweeper game not found.")
    if request.algorithm not in {"online_dfs", "greedy", "dfs", "pro"}:
        raise HTTPException(400, "algorithm must be 'online_dfs', 'greedy' or 'pro'.")

    started = time.perf_counter()
    steps = []

    # Always solve from the untouched board.
    state = game["initial"]
    game["state"] = state

    if request.algorithm == "pro":
        choose = _make_pro_chooser(game)
    elif request.algorithm in {"online_dfs", "dfs"}:
        from backend.search.onlineDFS import OnlineBlindSolver

        solver = OnlineBlindSolver(game["problem"], game["environment"])
        choose = solver.choose_action
    else:
        from backend.search.greedy import GreedySolver

        solver = GreedySolver(game["problem"], game["environment"])
        choose = None

    while len(steps) < request.max_steps:
        if game["environment"].is_win(state):
            break
        if state.lost:
            break
        if choose is not None:
            action = choose(state)
            if action is None:
                break
        else:
            candidates = game["problem"].actions(state)
            if not candidates:
                break
            flags = [a for a in candidates if a.__class__.__name__ == "FlagAction"]
            if flags:
                action = flags[0]
            else:
                reveals = [
                    a for a in candidates if a.__class__.__name__ == "RevealAction"
                ]
                if not reveals:
                    break
                action = max(
                    reveals,
                    key=lambda a: game["problem"].heuristic(
                        state, a.cell, use_entropy=False
                    ),
                )
        new_state = game["environment"].execute(state, action)
        action_data = _action_dict(action)
        action_data["action"] = (
            "flag" if action.__class__.__name__ == "FlagAction" else "reveal"
        )
        if request.algorithm == "pro":
            action_data["guess"] = choose.guessed
        steps.append(
            {
                "state": _grid(new_state.cells, game["rows"], game["cols"]),
                "action": action_data,
            }
        )
        state = new_state
        game["state"] = state

    if state.lost:
        final_status = "lost"
    elif game["environment"].is_win(state):
        final_status = "won"
    elif len(steps) >= request.max_steps:
        final_status = "step_limit"
    else:
        final_status = "stalled"
    return _minesweeper_response(
        request.game_id, game, request.algorithm, steps, final_status, started
    )


@router.post("/kakurasu/new")
def new_kakurasu(request: KakurasuNewRequest):
    rows = request.rows
    cols = request.cols

    generated = generate_problem(
        "kakurasu",
        "random",
        rows=rows,
        cols=cols,
        seed=request.seed,
    )

    puzzle_id = str(uuid4())
    started = time.perf_counter()

    problem = KakurasuProblem.from_generated(generated)

    KAKURASU_GAMES[puzzle_id] = {
        "puzzle_type": "kakurasu",
        "rows": rows,
        "cols": cols,
        "problem": problem,
        "state": problem.initial_state,
        "solution": generated["solution"],
    }

    return {
        "puzzle_id": puzzle_id,
        "puzzle_type": "kakurasu",
        "rows": rows,
        "cols": cols,
        "state": problem.to_display_cells(problem.initial_state),
        "row_targets": list(problem.row_targets),
        "col_targets": list(problem.col_targets),
        "generation_time_seconds": time.perf_counter() - started,
    }


@router.post("/kakurasu/solve")
def solve_kakurasu(request: KakurasuSolveRequest):
    puzzle_id = request.game_id
    puzzle = KAKURASU_GAMES.get(puzzle_id)

    if puzzle is None:
        raise HTTPException(404, "Kakurasu puzzle not found.")

    if request.algorithm not in {"dfs", "astar"}:
        raise HTTPException(
            400,
            "Unsupported algorithm. Use 'dfs' or 'astar'.",
        )

    started = time.perf_counter()

    try:
        solution = solve_problem(
            "kakurasu",
            request.algorithm,
            puzzle["problem"],
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    elapsed = time.perf_counter() - started

    return _kakurasu_result(
        puzzle["problem"],
        solution,
        puzzle_id,
        request.algorithm,
        elapsed,
    )
