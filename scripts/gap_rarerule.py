"""Rare-rule gap experiment: treatment (incomplete rules) vs control (complete
rules), each x {mini, nano}. Saves per-cell JSON; prints gap_truth summary.

Run: PYTHONPATH=src python scripts/gap_rarerule.py
"""
import sys
from cwm.run_gap import main

GRID = [
    ("army5x5a_material_incomplete", "mini"),   # treatment
    ("army5x5a_material_incomplete", "nano"),
    ("army5x5a_material", "mini"),              # control (complete rules)
    ("army5x5a_material", "nano"),
]
COMMON = ["--synth-seeds", "5", "--selfplay-games", "20",
          "--simulations", "300", "--train-games", "40", "--seed", "0"]

for game, size in GRID:
    print(f"\n########## {game} / {size} ##########", flush=True)
    try:
        main(["--game", game, "--synth-size", size] + COMMON)
    except Exception as e:
        print(f"!!! {game}/{size} FAILED: {e!r}", file=sys.stderr, flush=True)
