"""How many DISTINCT gate samples does the synthesis campaign actually have?

The paper quotes counts like "106/106 over 65 distinct gate samples" and "0/156
pooled". Peer review (2026-07-25) established that those over-count, and the reason
is structural rather than a slip in arithmetic: `collect_transitions` draws
`Random(rollout_seed + i)` and `continuous_danger_synthesis.py` sets
`rollout_seed = 10_000 * (seed_index + 1 + seed_offset)`. Neither depends on the
instrument, the knob, the patch shape or the prompt variant. So the cart's
`x_wall = 4` cell and its `x_wall = 8` cell reuse the SAME random streams, and the
PatchField2D guided ablation reuses the disc cells' streams byte for byte.

The sampling unit is therefore the (seed_index, seed_offset) block, not the
(arm, seed) cell. Two draws from one block are two synthesis attempts on ONE sample,
which is the right unit for:

  * counting how much independent evidence a claim rests on;
  * a Wilson interval, since trials within a block are not independent.

This script recounts every campaign at block level and reports both the cell count
the paper used to quote and the block count it should, plus the cluster-level Wilson
bound for each claim. It reads the versioned results only -- no new compute -- so it
can run in CI alongside the numeric audit.

Run: PYTHONPATH=src python scripts/sample_stream_census.py   (instant)
"""
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.law import wilson_ci  # noqa: E402

R = _REPO / "results"


def load(name):
    p = R / name
    return json.loads(p.read_text()) if p.exists() else None


def block_of(cell):
    """The rollout-seed block a cell's gate sample came from. The synthesis script
    sets rollout_seed = 10_000*(seed_index + 1 + seed_offset), and `seed` in the
    cell records it, so the seed value IS the block identity -- and it is shared
    across instruments, knobs, shapes and prompt variants, which is the whole
    point of this census."""
    for key in ("rollout_seed", "seed"):
        if key in cell:
            return cell[key]
    return None


FAMILIES = (
    ("1D cart", "continuous_synthesis_*xwall*.json"),
    ("1D pendulum", "continuous_synthesis_pendulum_*.json"),
    ("PatchField2D disc", "continuous_synthesis_patch2d_*.json"),
    ("PatchField2D square", "continuous_synthesis_patch2dsq_*.json"),
    ("Claude relay", "continuous_claude_relay*.json"),
)

out = {"script": "sample_stream_census.py", "families": []}
print(f"{'family':>22} {'files':>6} {'cells':>7} {'blocks':>7} {'ratio':>6}  blocks")
all_blocks = set()
for label, pat in FAMILIES:
    files = sorted(R.glob(pat))
    cells, blocks = 0, set()
    for f in files:
        d = json.loads(f.read_text())
        cs = d if isinstance(d, list) else d.get("cells", d.get("rows", []))
        for c in cs:
            cells += 1
            b = block_of(c)
            if b is not None:
                blocks.add(b)
    if not cells:
        continue
    all_blocks |= blocks
    out["families"].append({"family": label, "pattern": pat,
                            "files": [f.name for f in files], "cells": cells,
                            "distinct_blocks": len(blocks),
                            "blocks": sorted(blocks)})
    print(f"{label:>22} {len(files):6} {cells:7} {len(blocks):7} "
          f"{cells/max(1,len(blocks)):6.2f}  {sorted(blocks)[:4]}"
          f"{'...' if len(blocks) > 4 else ''}")
out["distinct_blocks_overall"] = len(all_blocks)
print(f"\ndistinct rollout-seed blocks across the ENTIRE campaign: "
      f"{len(all_blocks)}")

print("\nCluster-level recount of the headline claims. A Wilson interval over CELLS")
print("treats repeated draws on one sample as independent trials; the honest unit is")
print("the block, and the block-level bound is the conservative one to quote.")


def mode_present_cells(pattern, key="sample_contains_wall"):
    """Cells whose gate sample contained the mode -- the denominator of a repair
    claim -- together with the distinct blocks behind them."""
    cells, blocks = [], set()
    for f in sorted(R.glob(pattern)):
        d = json.loads(f.read_text())
        cs = d if isinstance(d, list) else d.get("cells", d.get("rows", []))
        for c in cs:
            if c.get(key):
                cells.append(c)
                b = block_of(c)
                if b is not None:
                    blocks.add(b)
    return cells, blocks


claims = []
for label, pat in (("1D cart repair", "continuous_synthesis_*xwall*.json"),
                   ("1D pendulum repair", "continuous_synthesis_pendulum_*.json"),
                   ("PatchField2D repair (disc)", "continuous_synthesis_patch2d_*.json"),
                   ("PatchField2D repair (square)",
                    "continuous_synthesis_patch2dsq_*.json")):
    cells, blocks = mode_present_cells(pat)
    if not cells:
        continue
    n_cell, n_block = len(cells), len(blocks)
    # the conservative reading: at most n_block independent successes
    lo_cell = wilson_ci(n_cell, n_cell)[1]
    lo_block = wilson_ci(n_block, n_block)[1] if n_block else None
    hi_cell = wilson_ci(0, n_cell)[2]
    hi_block = wilson_ci(0, n_block)[2] if n_block else None
    claims.append({"claim": label, "mode_present_cells": n_cell,
                   "distinct_blocks": n_block,
                   "wilson_lower_if_all_repair_cells": lo_cell,
                   "wilson_lower_if_all_repair_blocks": lo_block,
                   "wilson_upper_if_none_repair_cells": hi_cell,
                   "wilson_upper_if_none_repair_blocks": hi_block})
    print(f"  {label:>28}: {n_cell:3} mode-present cells over {n_block:2} blocks")
    print(f"{'':>30}  all-repair Wilson lower: {lo_cell:.3f} (cells) vs "
          f"{lo_block:.3f} (blocks)")
    print(f"{'':>30}  none-repair Wilson upper: {hi_cell:.3f} (cells) vs "
          f"{hi_block:.3f} (blocks)")
out["claims"] = claims
print("\nReading: quote the block count as the number of independent samples, and the")
print("block-level Wilson bound as the conservative one. A campaign that varies the")
print("knob, the patch shape or the prompt while holding the seed base fixed adds")
print("TREATMENTS, not samples -- which is a legitimate design, but it must not be")
print("reported as extra sample coverage. Use --seed-offset to draw a fresh block.")

dst = R / "sample_stream_census.json"
dst.write_text(json.dumps(out, indent=2))
print(f"\nwrote {dst}")
