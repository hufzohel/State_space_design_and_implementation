
def solve_problem(game: str, algorithm: str, problem):
    if game == "pipes":
        if algorithm == "dfs":
            from .search.dfs import DFSSolver
            return DFSSolver(problem).solve()

        if algorithm == "astar":
            from .search.astar import astar
            return astar(problem)

        raise ValueError(
            f"Unsupported Pipes algorithm: {algorithm}"
        )

    if game == "minesweeper":
        if algorithm == "greedy":
            # Minesweeper needs the real environment because
            # the solver chooses an action, observes the result,
            # and repeats.
            raise NotImplementedError(
                "Pass the Minesweeper environment to the greedy solver."
            )

        raise ValueError(
            f"Unsupported Minesweeper algorithm: {algorithm}"
        )

    raise ValueError(f"Unknown game: {game}")
