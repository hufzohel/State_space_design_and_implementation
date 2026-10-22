"""Run a small, reproducible DFS benchmark for a 2x2 Pipes puzzle."""

import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.puzzles.pipes.generator import PuzzleGenerator
from backend.puzzles.pipes.problem import PipesProblem
from backend.search.dfs import DFSSolver


ROWS = 2
COLS = 2
RANDOM_SEED = 42
NUMBER_OF_RUNS = 5


def create_problem():
    """Create a reproducible 2x2 Pipes puzzle and its problem object."""
    random.seed(RANDOM_SEED)

    generator = PuzzleGenerator()
    puzzle, _generated_solution = generator.generate_puzzle(ROWS, COLS)
    problem = PipesProblem(puzzle)

    return puzzle, problem


def summarize_search_result(problem, search_result):
    """Extract correctness and search metrics from one DFS result."""
    solution_found = search_result is not None
    expanded_nodes = search_result.expanded_nodes if solution_found else 0
    solution_length = len(search_result.actions) if solution_found else 0

    final_state_is_goal = False
    if solution_found and search_result.states:
        final_state_is_goal = problem.is_goal(search_result.states[-1])

    return {
        "solution_found": solution_found,
        "final_state_is_goal": final_state_is_goal,
        "expanded_nodes": expanded_nodes,
        "solution_length": solution_length,
    }


def run_timed_trials(problem):
    """Run DFS repeatedly with tracing disabled and record each duration."""
    trials = []

    for run_number in range(1, NUMBER_OF_RUNS + 1):
        solver = DFSSolver(problem)

        start_time = time.perf_counter()
        search_result = solver.solve()
        execution_time = time.perf_counter() - start_time

        trial = summarize_search_result(problem, search_result)
        trial["run_number"] = run_number
        trial["execution_time_seconds"] = execution_time
        trials.append(trial)

    return trials


def measure_peak_memory(problem):
    """Run DFS once more and measure memory separately from timed trials."""
    solver = DFSSolver(problem)

    tracemalloc.start()
    try:
        search_result = solver.solve()
        _current_memory, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    memory_run = summarize_search_result(problem, search_result)
    if not (
        memory_run["solution_found"]
        and memory_run["final_state_is_goal"]
    ):
        raise RuntimeError("The separate memory measurement found no valid solution.")

    return peak_memory


def print_report(puzzle, trials, peak_memory):
    """Print individual DFS runs and aggregate benchmark statistics."""
    execution_times = [
        trial["execution_time_seconds"]
        for trial in trials
    ]
    all_runs_valid = all(
        trial["solution_found"] and trial["final_state_is_goal"]
        for trial in trials
    )

    print("Pipes DFS Benchmark")
    print("===================")
    print(f"Board size: {ROWS}x{COLS}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Timed runs: {NUMBER_OF_RUNS}")
    print("Initial puzzle:")

    for row in puzzle:
        print(f"  {row}")

    print("\nIndividual runs:")
    for trial in trials:
        print(
            f"  Run {trial['run_number']}: "
            f"time={trial['execution_time_seconds']:.6f} seconds, "
            f"found={trial['solution_found']}, "
            f"valid_goal={trial['final_state_is_goal']}, "
            f"expanded_nodes={trial['expanded_nodes']}, "
            f"solution_length={trial['solution_length']}"
        )

    print("\nSummary:")
    print(f"  All {NUMBER_OF_RUNS} runs found valid solutions: {all_runs_valid}")
    print(f"  Mean execution time: {statistics.mean(execution_times):.6f} seconds")
    print(f"  Median execution time: {statistics.median(execution_times):.6f} seconds")
    print(
        "  Peak Python memory allocation (separate run): "
        f"{peak_memory} bytes ({peak_memory / 1024:.2f} KiB)"
    )

    if not all_runs_valid:
        raise RuntimeError("At least one timed DFS run found no valid solution.")


def main():
    """Create one problem, benchmark DFS, and display the report."""
    puzzle, problem = create_problem()

    if problem.is_goal(problem.initial_state):
        raise RuntimeError(
            "The generated puzzle is already solved; choose another seed "
            "before using it as benchmark evidence."
        )

    trials = run_timed_trials(problem)
    peak_memory = measure_peak_memory(problem)
    print_report(puzzle, trials, peak_memory)


if __name__ == "__main__":
    main()
