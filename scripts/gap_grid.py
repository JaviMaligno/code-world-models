"""Run the full gap grid: 3 regimes x {mini, nano}. Saves per-run JSON to
results/ and prints a summary table. Needs Azure (.env).

Run: PYTHONPATH=src python scripts/gap_grid.py
"""
import sys

from cwm.run_gap import main

GRID = [
    ("gen_tictactoe", "mini"), ("gen_tictactoe", "nano"),
    ("army5x5a", "mini"), ("army5x5a", "nano"),
    ("trike", "mini"), ("trike", "nano"),
]
COMMON = ["--synth-seeds", "5", "--selfplay-games", "20",
          "--simulations", "300", "--train-games", "40", "--seed", "0"]
EXTRA = sys.argv[1:]  # passthrough, e.g. --no-rules

for game, size in GRID:
    print(f"\n########## {game} / {size} {' '.join(EXTRA)} ##########", flush=True)
    argv = ["--game", game, "--synth-size", size] + COMMON + EXTRA
    try:
        main(argv)
    except Exception as e:  # keep the grid going if one cell fails
        print(f"!!! {game}/{size} FAILED: {e!r}", file=sys.stderr, flush=True)
