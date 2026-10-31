"""Ground-truth checks for Pipes on small boards (3x3).

h*(s) = min #tiles to change to reach ANY goal configuration
      = optimal action count (each action changes exactly one tile, and every
        distinct orientation of a tile is reachable in one action).

Run from the repo root:  python experiments/verify_pipes_heuristic.py
"""
import itertools
import json
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from backend.puzzles.pipes.generator import PuzzleGenerator
from backend.puzzles.pipes.problem import PipesProblem
from backend.puzzles.pipes.state import possible_rotations
from backend.search.astar import astar


class NoPrune(PipesProblem):
    def outward_openings(self, state):
        return 0


out = []
rng = random.Random(123)
for seed in range(20):
    random.seed(seed)
    for _ in range(100):
        puzzle, _sol = PuzzleGenerator().generate_puzzle(3, 3, method="tree")
        p = PipesProblem(puzzle)
        if not p.is_goal(p.initial_state):
            break
    s0 = p.initial_state
    choices = [possible_rotations(m) for m in s0]
    goals = [g for g in itertools.product(*choices) if p.is_goal(g)]

    def hstar(s):
        return min(sum(1 for a, b in zip(s, g) if a != b) for g in goals)

    opt = hstar(s0)
    a_prune = astar(p)
    a_noprune = astar(NoPrune(puzzle))

    # admissibility sample: random states from the same orbit
    viol = zero_nongoal = 0
    N = 300
    for _ in range(N):
        s = tuple(rng.choice(c) for c in choices)
        h = p.heuristic(s)
        if h > hstar(s):
            viol += 1
        if h == 0 and not p.is_goal(s):
            zero_nongoal += 1
    out.append(dict(seed=seed, goals=len(goals), opt=opt, h0=p.heuristic(s0),
                    astar_prune=a_prune.cost, astar_noprune=a_noprune.cost,
                    exp_prune=a_prune.expanded, exp_noprune=a_noprune.expanded,
                    gen_prune=a_prune.generated, gen_noprune=a_noprune.generated,
                    h_over=viol, h_zero_nongoal=zero_nongoal, sample=N))
    print(json.dumps(out[-1]), flush=True)

n = len(out)
print("boards", n)
print("A*(pruned) optimal on", sum(o["astar_prune"] == o["opt"] for o in out), "/", n)
print("A*(no prune) optimal on", sum(o["astar_noprune"] == o["opt"] for o in out), "/", n)
print("pruned cost == unpruned cost on", sum(o["astar_prune"] == o["astar_noprune"] for o in out), "/", n)
print("h(s0) > opt on", sum(o["h0"] > o["opt"] for o in out), "/", n)
print("mean h_over fraction", sum(o["h_over"] for o in out) / sum(o["sample"] for o in out))
print("h==0 but not goal among samples", sum(o["h_zero_nongoal"] for o in out))
print("mean exp prune/noprune", sum(o["exp_prune"] for o in out) / n, sum(o["exp_noprune"] for o in out) / n)
print("mean gen prune/noprune", sum(o["gen_prune"] for o in out) / n, sum(o["gen_noprune"] for o in out) / n)
print("mean goals", sum(o["goals"] for o in out) / n)
