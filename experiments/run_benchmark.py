"""Benchmark Pipes (DFS, A*) and Minesweeper (online_dfs, greedy).

Run from the repo root:

    python experiments/run_benchmark.py pipes        --out experiments/results/pipes.jsonl
    python experiments/run_benchmark.py minesweeper  --out experiments/results/ms.jsonl --seeds 100
    python experiments/run_benchmark.py summary      --out experiments/results/pipes.jsonl --kind pipes
    python experiments/run_benchmark.py summary      --out experiments/results/ms.jsonl --kind minesweeper

Method: every run is a separate Python process. A "time" pass runs without
tracemalloc; a "mem" pass (first --mem-seeds seeds only) records the tracemalloc
peak, because tracemalloc slows the program down.
"""
import argparse
import collections
import json
import os
import random
import subprocess
import sys
import time
import tracemalloc

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ----------------------------------------------------------------- worker
def _worker(a):
    sys.path.insert(0, REPO)
    if a["puzzle"] == "pipes":
        from backend.puzzles.pipes.generator import PuzzleGenerator
        from backend.puzzles.pipes.problem import PipesProblem
        from backend.search.astar import astar
        from backend.search.dfs import DFSSolver

        random.seed(a["seed"])
        for _ in range(100):  # same acceptance rule as POST /api/pipes/new
            puzzle, _solution = PuzzleGenerator().generate_puzzle(a["rows"], a["cols"], method="tree")
            problem = PipesProblem(puzzle)
            if not problem.is_goal(problem.initial_state):
                break
        run = lambda: (DFSSolver(problem).solve() if a["alg"] == "dfs" else astar(problem))
    else:
        from backend.puzzles.minesweeper.environment import MinesweeperEnvironment
        from backend.puzzles.minesweeper.generator import MinesweeperGenerator
        from backend.puzzles.minesweeper.problem import MinesweeperProblem, MinesweeperState
        from backend.search.greedy import GreedySolver
        from backend.search.onlineDFS import OnlineBlindSolver

        g = MinesweeperGenerator(a["rows"], a["cols"], a["mines"], seed=a["seed"]).generate()
        env = MinesweeperEnvironment(a["rows"], a["cols"], [i for i, m in enumerate(g["mines"]) if m])
        problem = MinesweeperProblem(a["rows"], a["cols"], MinesweeperState(tuple(g["initial_cells"])))
        solver = (OnlineBlindSolver if a["alg"] == "online_dfs" else GreedySolver)(problem, env)
        run = solver.solve

    if a["mode"] == "mem":
        tracemalloc.start()
    t0 = time.perf_counter()
    r = run()
    out = {"seconds": time.perf_counter() - t0}
    if a["puzzle"] == "pipes":
        if a["alg"] == "dfs":
            out.update(status="solved" if r else "no_solution", steps=len(r.actions),
                       expanded=r.expanded_nodes, generated=None)
        else:
            out.update(status=r.status, steps=len(r.actions), expanded=r.expanded, generated=r.generated)
    else:
        out.update(status=r.status, steps=len(r.actions), expanded=r.expanded_nodes)
    if a["mode"] == "mem":
        out["peak_mb"] = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
    return out


# ----------------------------------------------------------------- driver
def _drive(args):
    if args.puzzle == "pipes":
        jobs = [dict(puzzle="pipes", rows=r, cols=c, mines=0, alg=alg, seed=s)
                for (r, c) in [(2, 2), (2, 3), (3, 3), (3, 4), (4, 4)]
                for alg in ("dfs", "astar") for s in range(args.seeds)]
    else:
        jobs = [dict(puzzle="minesweeper", rows=n, cols=n, mines=max(1, round(n * n * 0.15)), alg=alg, seed=s)
                for n in (5, 6, 7, 8, 9) for alg in ("online_dfs", "greedy") for s in range(args.seeds)]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        for mode in ("time", "mem"):
            for job in jobs:
                if mode == "mem" and job["seed"] >= args.mem_seeds:
                    continue
                spec = dict(job, mode=mode)
                try:
                    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--worker", json.dumps(spec)],
                                       capture_output=True, text=True, timeout=args.timeout)
                    lines = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
                    res = json.loads(lines[-1][7:]) if lines else {"status": "error", "error": p.stderr[-300:]}
                except subprocess.TimeoutExpired:
                    res = {"status": "timeout", "seconds": args.timeout}
                res.update(spec)
                fh.write(json.dumps(res) + "\n")
                fh.flush()


# ----------------------------------------------------------------- summary
def _summary(args):
    rows = [json.loads(l) for l in open(args.out)]
    groups = collections.defaultdict(lambda: {"time": [], "mem": []})
    for r in rows:
        groups[(r["rows"], r["cols"], r["alg"])][r["mode"]].append(r)
    mean = lambda xs: (sum(xs) / len(xs)) if xs else float("nan")
    for key in sorted(groups):
        t, m = groups[key]["time"], groups[key]["mem"]
        status = collections.Counter(r["status"] for r in t)
        secs = [r["seconds"] for r in t if "seconds" in r]
        mem = [r["peak_mb"] for r in m if "peak_mb" in r]
        line = (f"{key[0]}x{key[1]} {key[2]:10s} n={len(t)} {dict(status)} "
                f"time mean={mean(secs):.4f}s max={max(secs, default=float('nan')):.3f}s "
                f"peak mem mean={mean(mem):.3f}MB max={max(mem, default=float('nan')):.3f}MB "
                f"steps mean={mean([r['steps'] for r in t if 'steps' in r]):.1f}")
        if args.kind == "pipes":
            line += f" expanded mean={mean([r['expanded'] for r in t if 'expanded' in r]):.1f}"
        else:
            line += f" win rate={status['won'] / max(1, len(t)):.2f}"
        print(line)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--worker":
        try:
            print("RESULT " + json.dumps(_worker(json.loads(sys.argv[2]))))
        except Exception as exc:  # keep the driver alive
            print("RESULT " + json.dumps({"status": "error", "error": repr(exc)}))
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", choices=["pipes", "minesweeper", "summary"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--mem-seeds", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--kind", choices=["pipes", "minesweeper"], default="pipes")
    args = ap.parse_args()
    _summary(args) if args.puzzle == "summary" else _drive(args)
