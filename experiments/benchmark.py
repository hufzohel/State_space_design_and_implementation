"""Reproducible, extensible benchmarks for the available search solvers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing
import platform
import random
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"

for import_root in (REPOSITORY_ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from puzzles.minesweeper.generator import MinesweeperGenerator
from puzzles.minesweeper.problem import MinesweeperProblem, MinesweeperState
from puzzles.pipes.generator import PuzzleGenerator
from puzzles.pipes.problem import PipesProblem
from search.dfs import DFSSolver


PASS = "PASS"
FAILED = "FAILED"
TIMEOUT = "TIMEOUT"
UNSUPPORTED = "UNSUPPORTED"
ERROR = "ERROR"

DEFAULT_TRIALS = 5
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_OUTPUT_DIRECTORY = REPOSITORY_ROOT / "experiments" / "results" / "issue10"


SOLVER_REGISTRY = {
    ("pipes", "dfs"): DFSSolver,
}


UNSUPPORTED_REASONS = {
    ("pipes", "astar"): "A* search has not been implemented.",
    ("minesweeper", "dfs"): (
        "The current DFS does not support Minesweeper successors "
        "that are None."
    ),
    ("minesweeper", "astar"): (
        "A* search and a compatible Minesweeper solver are not implemented."
    ),
}


@dataclass(frozen=True)
class InputSpecification:
    puzzle_type: str
    rows: int
    cols: int
    seed: int
    generator: str
    mine_count: int | None = None


def default_input_specifications(include_3x3: bool = False):
    """Return the small default suite used by the command-line benchmark."""
    specifications = []

    for rows, cols in ((2, 2), (2, 3)):
        for generator in ("tree", "tile"):
            for seed in (42, 43):
                specifications.append(
                    InputSpecification(
                        puzzle_type="pipes",
                        rows=rows,
                        cols=cols,
                        seed=seed,
                        generator=generator,
                    )
                )

    if include_3x3:
        for generator in ("tree", "tile"):
            specifications.append(
                InputSpecification(
                    puzzle_type="pipes",
                    rows=3,
                    cols=3,
                    seed=42,
                    generator=generator,
                )
            )

    for seed in (42, 43):
        specifications.append(
            InputSpecification(
                puzzle_type="minesweeper",
                rows=5,
                cols=5,
                seed=seed,
                generator="default",
                mine_count=3,
            )
        )

    return specifications


def _input_hash(input_data):
    hash_fields = {
        key: input_data[key]
        for key in (
            "puzzle_type",
            "rows",
            "cols",
            "seed",
            "generator",
            "initial_state",
            "mines",
        )
        if key in input_data
    }
    encoded = json.dumps(
        hash_fields,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_pipes_input(specification, max_attempts=100):
    """Generate and validate one reproducible Pipes input."""
    previous_random_state = random.getstate()
    random.seed(specification.seed)

    try:
        generator = PuzzleGenerator()

        for attempt in range(1, max_attempts + 1):
            puzzle, generated_solution = generator.generate_puzzle(
                specification.rows,
                specification.cols,
                method=specification.generator,
            )
            problem = PipesProblem(puzzle)
            solution_state = PipesProblem(generated_solution).initial_state
            initial_is_goal = problem.is_goal(problem.initial_state)
            generated_solution_is_goal = problem.is_goal(solution_state)

            if not initial_is_goal and generated_solution_is_goal:
                input_data = {
                    "input_id": (
                        f"pipes_{specification.rows}x{specification.cols}_"
                        f"{specification.generator}_seed{specification.seed}"
                    ),
                    "puzzle_type": "pipes",
                    "rows": specification.rows,
                    "cols": specification.cols,
                    "seed": specification.seed,
                    "generator": specification.generator,
                    "initial_state": puzzle,
                    "generated_solution": generated_solution,
                    "generation_attempts": attempt,
                    "rejected_invalid_attempts": attempt - 1,
                    "validation_status": PASS,
                    "validation_reason": (
                        "Initial state is unsolved and the generator's "
                        "solution passes PipesProblem.is_goal()."
                    ),
                }
                input_data["input_hash"] = _input_hash(input_data)
                return input_data

        raise RuntimeError(
            "Could not generate a valid, unsolved Pipes input after "
            f"{max_attempts} attempts."
        )
    finally:
        random.setstate(previous_random_state)


def generate_minesweeper_input(specification):
    """Generate a reproducible Minesweeper input, including hidden test data."""
    generator = MinesweeperGenerator(
        rows=specification.rows,
        cols=specification.cols,
        mine_count=specification.mine_count,
        seed=specification.seed,
    )
    generated = generator.generate()
    mines = [
        index
        for index, is_mine in enumerate(generated["mines"])
        if is_mine
    ]
    input_data = {
        "input_id": (
            f"minesweeper_{specification.rows}x{specification.cols}_"
            f"mines{specification.mine_count}_seed{specification.seed}"
        ),
        "puzzle_type": "minesweeper",
        "rows": specification.rows,
        "cols": specification.cols,
        "seed": specification.seed,
        "generator": specification.generator,
        "mine_count": specification.mine_count,
        "initial_state": list(generated["initial_cells"]),
        "mines": mines,
        "generation_attempts": 1,
        "rejected_invalid_attempts": 0,
        "validation_status": PASS,
        "validation_reason": (
            "Mine count, public state shape, and initial non-goal state "
            "were validated."
        ),
    }

    problem = build_problem(input_data)
    if len(mines) != specification.mine_count:
        raise RuntimeError("Minesweeper generator returned the wrong mine count.")
    if len(generated["initial_cells"]) != specification.rows * specification.cols:
        raise RuntimeError("Minesweeper generator returned the wrong state size.")
    if problem.is_goal(problem.initial_state):
        raise RuntimeError("Minesweeper input is already solved.")

    input_data["input_hash"] = _input_hash(input_data)
    return input_data


def generate_inputs(specifications):
    """Generate all benchmark inputs in specification order."""
    inputs = []

    for specification in specifications:
        if specification.puzzle_type == "pipes":
            inputs.append(generate_pipes_input(specification))
        elif specification.puzzle_type == "minesweeper":
            inputs.append(generate_minesweeper_input(specification))
        else:
            raise ValueError(
                f"Unknown puzzle type: {specification.puzzle_type}"
            )

    return inputs


def validate_saved_input(input_data):
    """Validate one serialized input before allowing a replay run."""
    required_fields = {
        "input_id",
        "input_hash",
        "puzzle_type",
        "rows",
        "cols",
        "seed",
        "generator",
        "initial_state",
    }
    missing_fields = required_fields - set(input_data)
    if missing_fields:
        raise ValueError(
            "Saved input is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    if input_data["input_hash"] != _input_hash(input_data):
        raise ValueError(
            f"Saved input hash mismatch: {input_data['input_id']}"
        )

    problem = build_problem(input_data)
    if problem.is_goal(problem.initial_state):
        raise ValueError(
            f"Saved input is already solved: {input_data['input_id']}"
        )

    if input_data["puzzle_type"] == "pipes":
        generated_solution = input_data.get("generated_solution")
        if generated_solution is None:
            raise ValueError(
                "Saved Pipes input has no generated_solution: "
                + input_data["input_id"]
            )
        solution_state = PipesProblem(generated_solution).initial_state
        if not problem.is_goal(solution_state):
            raise ValueError(
                "Saved Pipes input has an invalid generated solution: "
                + input_data["input_id"]
            )
    elif input_data["puzzle_type"] == "minesweeper":
        if len(input_data.get("mines", [])) != input_data.get("mine_count"):
            raise ValueError(
                "Saved Minesweeper input has an invalid mine count: "
                + input_data["input_id"]
            )

    return input_data


def load_inputs(path):
    """Load hash-checked benchmark inputs for an exact replay run."""
    path = Path(path)
    inputs = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("Saved input file must contain a non-empty list.")
    return [validate_saved_input(input_data) for input_data in inputs]


def build_problem(input_data):
    """Reconstruct a fresh problem from a saved benchmark input."""
    if input_data["puzzle_type"] == "pipes":
        puzzle = [row[:] for row in input_data["initial_state"]]
        return PipesProblem(puzzle)

    if input_data["puzzle_type"] == "minesweeper":
        return MinesweeperProblem(
            rows=input_data["rows"],
            cols=input_data["cols"],
            initial_state=MinesweeperState(
                tuple(input_data["initial_state"])
            ),
            mines=frozenset(input_data["mines"]),
        )

    raise ValueError(f"Unknown puzzle type: {input_data['puzzle_type']}")


def validate_search_result(problem, search_result):
    """Validate every state/action transition in one search result."""
    if search_result is None:
        return False, "Solver returned no SearchResult."

    states = getattr(search_result, "states", None)
    actions = getattr(search_result, "actions", None)

    if not states:
        return False, "SearchResult contains no states."
    if not isinstance(actions, list):
        return False, "SearchResult actions are missing or invalid."
    if states[0] != problem.initial_state:
        return False, "The first solution state is not the initial state."
    if len(actions) != len(states) - 1:
        return False, "Action and state counts are inconsistent."

    for state, action, next_state in zip(states, actions, states[1:]):
        if problem.result(state, action) != next_state:
            return False, "A solution transition is invalid."

    if not problem.is_goal(states[-1]):
        return False, "The final solution state is not a goal."

    return True, "Complete solution path is valid."


def _solver_worker(connection, input_data, solver_class, measure_memory):
    """Run one solver in an isolated process and return plain data."""
    try:
        problem = build_problem(input_data)
        solver = solver_class(problem)

        if measure_memory:
            tracemalloc.start()

        start_time = time.perf_counter()
        search_result = solver.solve()
        execution_time = time.perf_counter() - start_time

        peak_memory_bytes = None
        if measure_memory:
            _current_memory, peak_memory_bytes = (
                tracemalloc.get_traced_memory()
            )
            tracemalloc.stop()

        solution_valid, validation_message = validate_search_result(
            problem,
            search_result,
        )
        solution_found = search_result is not None
        expanded_nodes = (
            getattr(search_result, "expanded_nodes", None)
            if solution_found
            else None
        )
        solution_length = (
            len(search_result.actions)
            if solution_found and hasattr(search_result, "actions")
            else None
        )

        connection.send({
            "status": PASS if solution_valid else FAILED,
            "execution_time_seconds": execution_time,
            "peak_memory_bytes": peak_memory_bytes,
            "expanded_nodes": expanded_nodes,
            "solution_length": solution_length,
            "solution_found": solution_found,
            "solution_valid": solution_valid,
            "message": validation_message,
            "error_type": None,
        })
    except Exception as error:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        connection.send({
            "status": ERROR,
            "execution_time_seconds": None,
            "peak_memory_bytes": None,
            "expanded_nodes": None,
            "solution_length": None,
            "solution_found": None,
            "solution_valid": False,
            "message": str(error),
            "error_type": type(error).__name__,
        })
    finally:
        connection.close()


def run_solver_job(
    input_data,
    solver_class,
    timeout_seconds,
    measure_memory=False,
):
    """Run one fresh solver process with a hard wall-clock timeout."""
    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_solver_worker,
        args=(
            child_connection,
            input_data,
            solver_class,
            measure_memory,
        ),
    )
    try:
        process.start()
    except Exception as error:
        parent_connection.close()
        child_connection.close()
        return {
            "status": ERROR,
            "execution_time_seconds": None,
            "peak_memory_bytes": None,
            "expanded_nodes": None,
            "solution_length": None,
            "solution_found": None,
            "solution_valid": False,
            "message": str(error),
            "error_type": type(error).__name__,
        }
    child_connection.close()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        parent_connection.close()
        return {
            "status": TIMEOUT,
            "execution_time_seconds": None,
            "peak_memory_bytes": None,
            "expanded_nodes": None,
            "solution_length": None,
            "solution_found": None,
            "solution_valid": False,
            "message": (
                f"Solver exceeded the {timeout_seconds:g}-second "
                "wall-clock limit."
            ),
            "error_type": None,
        }

    if parent_connection.poll(1.0):
        try:
            result = parent_connection.recv()
        except EOFError:
            result = {
                "status": ERROR,
                "execution_time_seconds": None,
                "peak_memory_bytes": None,
                "expanded_nodes": None,
                "solution_length": None,
                "solution_found": None,
                "solution_valid": False,
                "message": (
                    "Solver process closed its result pipe unexpectedly "
                    f"(exit code {process.exitcode})."
                ),
                "error_type": "UnexpectedWorkerExit",
            }
        parent_connection.close()
        return result

    parent_connection.close()
    return {
        "status": ERROR,
        "execution_time_seconds": None,
        "peak_memory_bytes": None,
        "expanded_nodes": None,
        "solution_length": None,
        "solution_found": None,
        "solution_valid": False,
        "message": (
            "Solver process exited without returning a measurement "
            f"(exit code {process.exitcode})."
        ),
        "error_type": "MissingWorkerResult",
    }


def unsupported_record(input_data, algorithm):
    reason = UNSUPPORTED_REASONS.get(
        (input_data["puzzle_type"], algorithm),
        f"Algorithm '{algorithm}' is not registered for this puzzle.",
    )
    return {
        "input_id": input_data["input_id"],
        "input_hash": input_data["input_hash"],
        "puzzle_type": input_data["puzzle_type"],
        "rows": input_data["rows"],
        "cols": input_data["cols"],
        "seed": input_data["seed"],
        "generator": input_data["generator"],
        "algorithm": algorithm,
        "trial_number": None,
        "status": UNSUPPORTED,
        "execution_time_seconds": None,
        "expanded_nodes": None,
        "solution_length": None,
        "solution_found": None,
        "solution_valid": None,
        "message": reason,
        "error_type": None,
    }


def _mean(values):
    return statistics.mean(values) if values else None


def _median(values):
    return statistics.median(values) if values else None


def summarize_group(input_data, algorithm, records, memory_result):
    """Aggregate trials without replacing unavailable data with zero."""
    if records[0]["status"] == UNSUPPORTED:
        return {
            "input_id": input_data["input_id"],
            "input_hash": input_data["input_hash"],
            "puzzle_type": input_data["puzzle_type"],
            "rows": input_data["rows"],
            "cols": input_data["cols"],
            "seed": input_data["seed"],
            "generator": input_data["generator"],
            "algorithm": algorithm,
            "status": UNSUPPORTED,
            "requested_trials": 0,
            "completed_trials": 0,
            "successful_trials": 0,
            "success_rate": None,
            "execution_time_mean_seconds": None,
            "execution_time_median_seconds": None,
            "peak_memory_bytes": None,
            "memory_status": UNSUPPORTED,
            "expanded_nodes_mean": None,
            "expanded_nodes_median": None,
            "solution_length_mean": None,
            "solution_length_median": None,
            "message": records[0]["message"],
        }

    execution_times = [
        record["execution_time_seconds"]
        for record in records
        if record["execution_time_seconds"] is not None
    ]
    expanded_nodes = [
        record["expanded_nodes"]
        for record in records
        if record["expanded_nodes"] is not None
    ]
    solution_lengths = [
        record["solution_length"]
        for record in records
        if record["solution_length"] is not None
    ]
    successful_trials = sum(
        record["status"] == PASS
        for record in records
    )

    if any(record["status"] == ERROR for record in records):
        status = ERROR
    elif any(record["status"] == TIMEOUT for record in records):
        status = TIMEOUT
    elif successful_trials != len(records):
        status = FAILED
    else:
        status = PASS

    return {
        "input_id": input_data["input_id"],
        "input_hash": input_data["input_hash"],
        "puzzle_type": input_data["puzzle_type"],
        "rows": input_data["rows"],
        "cols": input_data["cols"],
        "seed": input_data["seed"],
        "generator": input_data["generator"],
        "algorithm": algorithm,
        "status": status,
        "requested_trials": len(records),
        "completed_trials": len(execution_times),
        "successful_trials": successful_trials,
        "success_rate": successful_trials / len(records),
        "execution_time_mean_seconds": _mean(execution_times),
        "execution_time_median_seconds": _median(execution_times),
        "peak_memory_bytes": (
            memory_result["peak_memory_bytes"]
            if memory_result is not None
            and memory_result["status"] == PASS
            else None
        ),
        "memory_status": (
            memory_result["status"]
            if memory_result is not None
            else None
        ),
        "expanded_nodes_mean": _mean(expanded_nodes),
        "expanded_nodes_median": _median(expanded_nodes),
        "solution_length_mean": _mean(solution_lengths),
        "solution_length_median": _median(solution_lengths),
        "message": (
            "All timed trials returned valid solution paths."
            if status == PASS
            else "One or more timed trials did not pass."
        ),
    }


def run_benchmark(
    inputs,
    algorithms,
    trials,
    timeout_seconds,
    measure_memory=True,
    solver_registry=None,
):
    """Run all requested algorithms on exactly the supplied inputs."""
    if trials <= 0:
        raise ValueError("trials must be positive.")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    registry = SOLVER_REGISTRY if solver_registry is None else solver_registry
    trial_records = []
    summaries = []

    for input_data in inputs:
        for algorithm in algorithms:
            solver_class = registry.get(
                (input_data["puzzle_type"], algorithm)
            )

            if solver_class is None:
                records = [unsupported_record(input_data, algorithm)]
                trial_records.extend(records)
                summaries.append(
                    summarize_group(
                        input_data,
                        algorithm,
                        records,
                        memory_result=None,
                    )
                )
                continue

            records = []
            for trial_number in range(1, trials + 1):
                measurement = run_solver_job(
                    input_data,
                    solver_class,
                    timeout_seconds,
                    measure_memory=False,
                )
                record = {
                    "input_id": input_data["input_id"],
                    "input_hash": input_data["input_hash"],
                    "puzzle_type": input_data["puzzle_type"],
                    "rows": input_data["rows"],
                    "cols": input_data["cols"],
                    "seed": input_data["seed"],
                    "generator": input_data["generator"],
                    "algorithm": algorithm,
                    "trial_number": trial_number,
                    **{
                        key: value
                        for key, value in measurement.items()
                        if key != "peak_memory_bytes"
                    },
                }
                records.append(record)
                trial_records.append(record)

            memory_result = None
            if measure_memory:
                memory_result = run_solver_job(
                    input_data,
                    solver_class,
                    timeout_seconds,
                    measure_memory=True,
                )

            summaries.append(
                summarize_group(
                    input_data,
                    algorithm,
                    records,
                    memory_result,
                )
            )

    return trial_records, summaries


def aggregate_results(trial_records, summaries):
    """Aggregate per-input summaries across seeds for report tables."""
    group_keys = []
    for summary in summaries:
        key = (
            summary["puzzle_type"],
            summary["rows"],
            summary["cols"],
            summary["generator"],
            summary["algorithm"],
        )
        if key not in group_keys:
            group_keys.append(key)

    aggregates = []
    for puzzle_type, rows, cols, generator, algorithm in group_keys:
        grouped_summaries = [
            summary
            for summary in summaries
            if (
                summary["puzzle_type"],
                summary["rows"],
                summary["cols"],
                summary["generator"],
                summary["algorithm"],
            ) == (puzzle_type, rows, cols, generator, algorithm)
        ]
        grouped_trials = [
            record
            for record in trial_records
            if (
                record["puzzle_type"],
                record["rows"],
                record["cols"],
                record["generator"],
                record["algorithm"],
            ) == (puzzle_type, rows, cols, generator, algorithm)
            and record["status"] != UNSUPPORTED
        ]

        if all(
            summary["status"] == UNSUPPORTED
            for summary in grouped_summaries
        ):
            aggregates.append({
                "puzzle_type": puzzle_type,
                "rows": rows,
                "cols": cols,
                "generator": generator,
                "algorithm": algorithm,
                "status": UNSUPPORTED,
                "input_count": len(grouped_summaries),
                "requested_trials": 0,
                "successful_trials": 0,
                "success_rate": None,
                "execution_time_mean_seconds": None,
                "execution_time_median_seconds": None,
                "peak_memory_mean_bytes": None,
                "peak_memory_median_bytes": None,
                "expanded_nodes_mean": None,
                "expanded_nodes_median": None,
                "solution_length_mean": None,
                "solution_length_median": None,
            })
            continue

        execution_times = [
            record["execution_time_seconds"]
            for record in grouped_trials
            if record["execution_time_seconds"] is not None
        ]
        expanded_nodes = [
            record["expanded_nodes"]
            for record in grouped_trials
            if record["expanded_nodes"] is not None
        ]
        solution_lengths = [
            record["solution_length"]
            for record in grouped_trials
            if record["solution_length"] is not None
        ]
        memory_values = [
            summary["peak_memory_bytes"]
            for summary in grouped_summaries
            if summary["peak_memory_bytes"] is not None
        ]
        requested_trials = len(grouped_trials)
        successful_trials = sum(
            record["status"] == PASS
            for record in grouped_trials
        )

        if any(summary["status"] == ERROR for summary in grouped_summaries):
            status = ERROR
        elif any(
            summary["status"] == TIMEOUT
            for summary in grouped_summaries
        ):
            status = TIMEOUT
        elif successful_trials != requested_trials:
            status = FAILED
        else:
            status = PASS

        aggregates.append({
            "puzzle_type": puzzle_type,
            "rows": rows,
            "cols": cols,
            "generator": generator,
            "algorithm": algorithm,
            "status": status,
            "input_count": len(grouped_summaries),
            "requested_trials": requested_trials,
            "successful_trials": successful_trials,
            "success_rate": (
                successful_trials / requested_trials
                if requested_trials
                else None
            ),
            "execution_time_mean_seconds": _mean(execution_times),
            "execution_time_median_seconds": _median(execution_times),
            "peak_memory_mean_bytes": _mean(memory_values),
            "peak_memory_median_bytes": _median(memory_values),
            "expanded_nodes_mean": _mean(expanded_nodes),
            "expanded_nodes_median": _median(expanded_nodes),
            "solution_length_mean": _mean(solution_lengths),
            "solution_length_median": _median(solution_lengths),
        })

    return aggregates


def environment_metadata(trials, timeout_seconds, algorithms):
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "processor": platform.processor() or None,
        "perf_counter_resolution_seconds": time.get_clock_info(
            "perf_counter"
        ).resolution,
        "timed_trials_per_supported_case": trials,
        "timeout_seconds_per_process": timeout_seconds,
        "requested_algorithms": algorithms,
        "measurement_notes": [
            "Puzzle generation is excluded from solver execution time.",
            "Each timed trial creates a fresh problem and solver process.",
            "Peak tracemalloc memory is measured in a separate solver run.",
            "Process startup time is excluded from execution_time_seconds.",
            "None means unavailable; missing metrics are never replaced by zero.",
        ],
        "available_solvers": [
            {
                "puzzle_type": puzzle_type,
                "algorithm": algorithm,
                "solver_class": solver_class.__name__,
            }
            for (puzzle_type, algorithm), solver_class
            in sorted(SOLVER_REGISTRY.items())
        ],
    }


def _write_csv(path, rows):
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")

    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    output_directory,
    inputs,
    trial_records,
    summaries,
    aggregates,
    metadata,
):
    """Persist reproducible inputs, trial data, summaries, and metadata."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    paths = {
        "inputs": output_directory / "inputs.json",
        "trials": output_directory / "trials.csv",
        "summary": output_directory / "summary.csv",
        "aggregate": output_directory / "aggregate.csv",
        "report": output_directory / "report.json",
    }

    paths["inputs"].write_text(
        json.dumps(inputs, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(paths["trials"], trial_records)
    _write_csv(paths["summary"], summaries)
    _write_csv(paths["aggregate"], aggregates)
    paths["report"].write_text(
        json.dumps(
            {
                "metadata": metadata,
                "inputs": inputs,
                "trials": trial_records,
                "summary": summaries,
                "aggregate": aggregates,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    return paths


def print_report(inputs, summaries, output_paths):
    print("AI Search Benchmark")
    print("===================")
    print(f"Inputs: {len(inputs)}")
    print()
    print(
        "Input".ljust(37),
        "Algorithm".ljust(10),
        "Status".ljust(12),
        "Success".ljust(9),
        "Mean ms".rjust(10),
        "Median ms".rjust(11),
        "Peak KiB".rjust(10),
        "Expanded".rjust(10),
        "Length".rjust(8),
    )

    for summary in summaries:
        success_rate = summary["success_rate"]
        mean_time = summary["execution_time_mean_seconds"]
        median_time = summary["execution_time_median_seconds"]
        peak_memory = summary["peak_memory_bytes"]
        expanded = summary["expanded_nodes_mean"]
        length = summary["solution_length_mean"]

        print(
            summary["input_id"][:36].ljust(37),
            summary["algorithm"].ljust(10),
            summary["status"].ljust(12),
            (
                f"{success_rate:.0%}"
                if success_rate is not None
                else "-"
            ).ljust(9),
            (
                f"{mean_time * 1000:.3f}"
                if mean_time is not None
                else "-"
            ).rjust(10),
            (
                f"{median_time * 1000:.3f}"
                if median_time is not None
                else "-"
            ).rjust(11),
            (
                f"{peak_memory / 1024:.2f}"
                if peak_memory is not None
                else "-"
            ).rjust(10),
            (
                f"{expanded:.1f}"
                if expanded is not None
                else "-"
            ).rjust(10),
            (
                f"{length:.1f}"
                if length is not None
                else "-"
            ).rjust(8),
        )

    print()
    print("Saved results:")
    for name, path in output_paths.items():
        try:
            display_path = path.relative_to(REPOSITORY_ROOT)
        except ValueError:
            display_path = path
        print(f"  {name}: {display_path}")


def parse_arguments(arguments=None):
    parser = argparse.ArgumentParser(
        description="Benchmark available AI search algorithms.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=DEFAULT_TRIALS,
        help="Timed trials per supported input/algorithm pair.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Hard wall-clock timeout for each solver process.",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["dfs", "astar"],
        help="Algorithms to request; unavailable algorithms are recorded.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Directory for JSON and CSV result files.",
    )
    parser.add_argument(
        "--inputs-file",
        type=Path,
        help=(
            "Replay a previously saved inputs.json file instead of "
            "generating the default suite."
        ),
    )
    parser.add_argument(
        "--include-3x3",
        action="store_true",
        help="Also benchmark two resource-intensive 3x3 Pipes cases.",
    )
    return parser.parse_args(arguments)


def main(arguments=None):
    options = parse_arguments(arguments)
    if options.inputs_file is not None:
        inputs = load_inputs(options.inputs_file)
    else:
        specifications = default_input_specifications(options.include_3x3)
        inputs = generate_inputs(specifications)
    trial_records, summaries = run_benchmark(
        inputs=inputs,
        algorithms=options.algorithms,
        trials=options.trials,
        timeout_seconds=options.timeout_seconds,
        measure_memory=True,
    )
    metadata = environment_metadata(
        options.trials,
        options.timeout_seconds,
        options.algorithms,
    )
    aggregates = aggregate_results(trial_records, summaries)
    output_paths = write_outputs(
        options.output_dir,
        inputs,
        trial_records,
        summaries,
        aggregates,
        metadata,
    )
    print_report(inputs, summaries, output_paths)

    failed_supported_cases = [
        summary
        for summary in summaries
        if summary["status"] not in {PASS, UNSUPPORTED}
    ]
    return 1 if failed_supported_cases else 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
