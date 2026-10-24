import csv
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.benchmark import (  # noqa: E402
    ERROR,
    FAILED,
    PASS,
    TIMEOUT,
    UNSUPPORTED,
    InputSpecification,
    aggregate_results,
    generate_inputs,
    generate_pipes_input,
    load_inputs,
    run_benchmark,
    run_solver_job,
    summarize_group,
    write_outputs,
)
from backend.search.dfs import DFSSolver  # noqa: E402


class ReturningNoneSolver:
    def __init__(self, problem):
        self.problem = problem

    def solve(self):
        return None


class RaisingSolver:
    def __init__(self, problem):
        self.problem = problem

    def solve(self):
        raise RuntimeError("intentional test error")


class SlowSolver:
    def __init__(self, problem):
        self.problem = problem

    def solve(self):
        time.sleep(2)


def small_pipes_input():
    return generate_pipes_input(
        InputSpecification(
            puzzle_type="pipes",
            rows=2,
            cols=2,
            seed=42,
            generator="tree",
        )
    )


class BenchmarkRegressionTests(unittest.TestCase):
    def test_input_generation_is_reproducible(self):
        specifications = [
            InputSpecification("pipes", 2, 3, 42, "tile"),
            InputSpecification(
                "minesweeper",
                5,
                5,
                42,
                "default",
                mine_count=3,
            ),
        ]

        first = generate_inputs(specifications)
        second = generate_inputs(specifications)

        self.assertEqual(first, second)
        self.assertEqual(first[0]["validation_status"], PASS)
        self.assertGreaterEqual(first[0]["rejected_invalid_attempts"], 1)
        self.assertEqual(first[0]["input_hash"], second[0]["input_hash"])

    def test_dfs_measurements_and_solution_correctness(self):
        measurement = run_solver_job(
            small_pipes_input(),
            DFSSolver,
            timeout_seconds=5,
            measure_memory=False,
        )
        memory = run_solver_job(
            small_pipes_input(),
            DFSSolver,
            timeout_seconds=5,
            measure_memory=True,
        )

        self.assertEqual(measurement["status"], PASS)
        self.assertTrue(measurement["solution_found"])
        self.assertTrue(measurement["solution_valid"])
        self.assertGreater(measurement["execution_time_seconds"], 0)
        self.assertGreater(measurement["expanded_nodes"], 0)
        self.assertGreater(measurement["solution_length"], 0)
        self.assertEqual(memory["status"], PASS)
        self.assertGreater(memory["peak_memory_bytes"], 0)

    def test_unsupported_failure_exception_and_timeout(self):
        input_data = small_pipes_input()
        registry = {
            ("pipes", "none"): ReturningNoneSolver,
            ("pipes", "error"): RaisingSolver,
        }
        records, summaries = run_benchmark(
            inputs=[input_data],
            algorithms=["missing", "none", "error"],
            trials=1,
            timeout_seconds=5,
            measure_memory=False,
            solver_registry=registry,
        )
        statuses = {
            summary["algorithm"]: summary["status"]
            for summary in summaries
        }

        self.assertEqual(statuses["missing"], UNSUPPORTED)
        self.assertEqual(statuses["none"], FAILED)
        self.assertEqual(statuses["error"], ERROR)
        timeout_result = run_solver_job(
            input_data,
            SlowSolver,
            timeout_seconds=0.2,
            measure_memory=False,
        )
        self.assertEqual(timeout_result["status"], TIMEOUT)

        missing_record = next(
            record
            for record in records
            if record["algorithm"] == "missing"
        )
        self.assertIsNone(missing_record["expanded_nodes"])
        self.assertIsNone(missing_record["solution_length"])

    def test_missing_metrics_remain_none(self):
        input_data = small_pipes_input()
        failed_record = {
            "status": FAILED,
            "execution_time_seconds": 0.01,
            "expanded_nodes": None,
            "solution_length": None,
        }
        summary = summarize_group(
            input_data,
            "test",
            [failed_record],
            memory_result=None,
        )

        self.assertIsNone(summary["expanded_nodes_mean"])
        self.assertIsNone(summary["solution_length_mean"])
        self.assertIsNone(summary["peak_memory_bytes"])
        self.assertEqual(summary["success_rate"], 0)

    def test_csv_and_json_outputs(self):
        input_data = small_pipes_input()
        records, summaries = run_benchmark(
            inputs=[input_data],
            algorithms=["dfs", "astar"],
            trials=1,
            timeout_seconds=5,
            measure_memory=False,
        )
        metadata = {"test_run": True}
        aggregates = aggregate_results(records, summaries)

        with tempfile.TemporaryDirectory() as directory:
            paths = write_outputs(
                directory,
                [input_data],
                records,
                summaries,
                aggregates,
                metadata,
            )

            for path in paths.values():
                self.assertTrue(path.exists())

            saved_inputs = json.loads(
                paths["inputs"].read_text(encoding="utf-8")
            )
            replay_inputs = load_inputs(paths["inputs"])
            report = json.loads(
                paths["report"].read_text(encoding="utf-8")
            )
            with paths["trials"].open(encoding="utf-8", newline="") as file:
                trial_rows = list(csv.DictReader(file))
            with paths["summary"].open(encoding="utf-8", newline="") as file:
                summary_rows = list(csv.DictReader(file))
            with paths["aggregate"].open(encoding="utf-8", newline="") as file:
                aggregate_rows = list(csv.DictReader(file))

            self.assertEqual(saved_inputs[0]["input_hash"], input_data["input_hash"])
            self.assertEqual(replay_inputs, [input_data])
            self.assertEqual(report["metadata"], metadata)
            self.assertEqual(len(trial_rows), 2)
            self.assertEqual(len(summary_rows), 2)
            self.assertEqual(len(aggregate_rows), 2)
            self.assertEqual(summary_rows[1]["status"], UNSUPPORTED)
            self.assertEqual(summary_rows[1]["peak_memory_bytes"], "")

            saved_inputs[0]["initial_state"][0][0] = 0
            paths["inputs"].write_text(
                json.dumps(saved_inputs),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_inputs(paths["inputs"])


if __name__ == "__main__":
    unittest.main()
