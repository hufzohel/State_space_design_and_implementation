
# dispatcher.py


def generate_problem(game: str, generator: str, **kwargs):
    """Dispatch puzzle generation to the appropriate generator."""

    if game == "pipes":
        from .puzzles.pipes.generator import generate_puzzle

        if generator in ("tree", "tile"):
            return generate_puzzle(
                kwargs["rows"],
                kwargs["cols"],
                method=generator,
            )

        raise ValueError(f"Unsupported Pipes generator: {generator}")

    if game == "kakurasu":
        from .puzzles.kakurasu.generator import generate_puzzle

        # Adapt this call if your Kakurasu generator uses
        # a different function signature.
        if generator in ("default", "random"):
            return generate_puzzle(**kwargs)

        raise ValueError(f"Unsupported Kakurasu generator: {generator}")

    if game == "minesweeper":
        from .puzzles.minesweeper.generator import generate_puzzle

        # Adapt this call if your Minesweeper generator uses
        # a different function signature.
        if generator in ("default", "random"):
            return generate_puzzle(**kwargs)

        raise ValueError(
            f"Unsupported Minesweeper generator: {generator}"
        )

    raise ValueError(f"Unknown puzzle: {game}")


def solve_problem(game: str, algorithm: str, problem, environment=None):
    """Dispatch a prepared problem to the appropriate solver."""

    if game == "pipes":
        if algorithm == "dfs":
            from .search.dfs import DFSSolver
            return DFSSolver(problem).solve()

        if algorithm == "astar":
            from .search.astar import astar
            return astar(problem)

        raise ValueError(f"Unsupported Pipes algorithm: {algorithm}")

    if game == "kakurasu":
        if algorithm == "dfs":
            from .search.dfs import DFSSolver
            return DFSSolver(problem).solve()

        if algorithm == "astar":
            from .search.astar import astar
            return astar(problem)

        raise ValueError(f"Unsupported Kakurasu algorithm: {algorithm}")

    if game == "minesweeper":
        if environment is None:
            raise ValueError(
                "Minesweeper requires an environment."
            )

        if algorithm == "online_dfs":
            from .search.onlineDFS import OnlineBlindSolver
            return OnlineBlindSolver(problem)

        if algorithm == "greedy":
            from .search.greedy import GreedySolver
            return GreedySolver(problem, environment).solve()

        if algorithm == "constraint_propagation":
            from .search.Minesweeper_pro_solver import ConstraintPropagator
            return ConstraintPropagator().propagate(problem)

        raise ValueError(
            f"Unsupported Minesweeper algorithm: {algorithm}"
        )

    raise ValueError(f"Unknown puzzle: {game}")
