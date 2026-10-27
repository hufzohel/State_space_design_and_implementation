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
        return MinesweeperGenerator(
            rows=kwargs["rows"],
            cols=kwargs["cols"],
            mine_count=kwargs["mine_count"],
            seed=kwargs.get("seed"),
        ).generate()

    raise ValueError(
        "Unsupported puzzle: %s (Kakurasu is intentionally deferred)" % game
    )


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

    raise ValueError(
        "Unsupported puzzle: %s (Kakurasu is intentionally deferred)" % game
    )
