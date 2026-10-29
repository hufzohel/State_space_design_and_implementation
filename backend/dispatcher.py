"""Application-level dispatch for puzzle generation and solvers."""


def generate_problem(game: str, generator: str, **kwargs):
    """Generate a puzzle using the public generator interfaces."""
    if game == "pipes":
        from backend.puzzles.pipes.generator import PuzzleGenerator

        if generator not in {"tree", "tile"}:
            raise ValueError("Unsupported Pipes generator: %s" % generator)
        rows = kwargs["rows"]
        cols = kwargs["cols"]
        return PuzzleGenerator().generate_puzzle(rows, cols, method=generator)

    if game == "minesweeper":
        from backend.puzzles.minesweeper.generator import MinesweeperGenerator

        if generator not in {"default", "random"}:
            raise ValueError("Unsupported Minesweeper generator: %s" % generator)
        generator_obj = MinesweeperGenerator(
            rows=kwargs["rows"],
            cols=kwargs["cols"],
            mine_count=kwargs["mine_count"],
            seed=kwargs.get("seed"),
        )
        if kwargs.get("first_cell") is not None:
            return generator_obj.generate_for_click(kwargs["first_cell"])
        return generator_obj.generate()

    if game == "kakurasu":
        from backend.puzzles.kakurasu.generator import KakurasuGenerator

        if generator not in {"default", "random"}:
            raise ValueError("Unsupported Kakurasu generator: %s" % generator)
        return KakurasuGenerator(
            rows=kwargs["rows"],
            cols=kwargs["cols"],
            seed=kwargs.get("seed"),
        ).generate()

    raise ValueError("Unsupported puzzle: %s" % game)


def solve_problem(game: str, algorithm: str, problem, environment=None):
    """Dispatch a prepared problem to a solver."""
    if game == "pipes":
        if algorithm == "dfs":
            from backend.search.dfs import DFSSolver

            return DFSSolver(problem).solve()
        if algorithm == "astar":
            from backend.search.astar import astar

            return astar(problem)
        raise ValueError("Unsupported Pipes algorithm: %s" % algorithm)

    if game == "minesweeper":
        if environment is None:
            raise ValueError("Minesweeper requires an environment")
        if algorithm == "online_dfs":
            from backend.search.onlineDFS import OnlineBlindSolver

            return OnlineBlindSolver(problem, environment)
        if algorithm == "greedy":
            from backend.search.greedy import GreedySolver

            return GreedySolver(problem, environment).solve()
        if algorithm == "constraint_propagation":
            from backend.search.Minesweeper_pro_solver import ConstraintPropagator

            return ConstraintPropagator().propagate(problem)
        raise ValueError("Unsupported Minesweeper algorithm: %s" % algorithm)

    if game == "kakurasu":
        if algorithm == "dfs":
            from backend.search.dfs import DFSSolver

            return DFSSolver(problem).solve()

        if algorithm == "astar":
            from backend.search.astar import astar

            return astar(problem)

        raise ValueError("Unsupported Kakurasu algorithm: %s" % algorithm)


def solve_pipes_puzzle(puzzle, algorithm, max_expansions=None):
    """Solve a Pipes board, preferring the optional fast module."""
    # import logging
    # import os

    # log = logging.getLogger(__name__)

    # fast_solver = None
    # if os.getenv("PIPES_FAST_SOLVER", "1") != "0":
    #     try:
    #         from backend.puzzles.pipes.placement import solve_by_placement

    #         fast_solver = solve_by_placement
    #     except ModuleNotFoundError as exc:
    #         # Only "the add-on is absent" is silenced; a missing dependency
    #         # *inside* the add-on is a real bug and must surface.
    #         if exc.name != "backend.puzzles.pipes.placement":
    #             raise

    # if fast_solver is not None:
    #     log.info("Pipes: using optional placement solver (%s)", algorithm)
    #     return fast_solver(puzzle, algorithm)

    # ---- standard path: unchanged core solvers ----
    from backend.puzzles.pipes.problem import PipesProblem

    problem = PipesProblem(puzzle)
    if algorithm == "dfs":
        from backend.search.dfs import DFSSolver

        return DFSSolver(problem).solve()
    if algorithm == "astar":
        from backend.search.astar import astar

        return astar(problem, max_expansions=max_expansions)
    raise ValueError("Unsupported Pipes algorithm: %s" % algorithm)
