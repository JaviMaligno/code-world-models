# H3 handoff — experimental units and campaign ledger

Claude Code with `claude-fable-5` implemented the H3 core in
`scripts/paper2_statistics.py`, regenerated `results/paper2_statistics.json`, and added
the H3 tests in `tests/test_paper2_statistics.py`. The Claude workspace then exhausted
its credits before manuscript integration; Codex performed that integration and the
independent verification recorded below.

H3 separates four levels that the previous prose conflated: raw random-stream block,
instrument--stream block, treatment cell, and synthesis draw. The artifact census remains
strong: 105/111 mode-containing 1D draws are exact. The primary inference unit is the
instrument--stream block: every attempt is exact on 50/56 blocks, Clopper--Pearson 95%
[0.7812, 0.9597]. Clustering cart and pendulum sharing a random stream into the strictest
possible unit gives 30/36, [0.6719, 0.9363]. The former 64/70 figure is valid only as a
knob-level block-cell census and is labelled accordingly.

The canonical campaign table covers 20 campaigns and 1040 draws. A same-model,
same-block Qwen replicate agrees on outcomes and gate decisions in 6/6 paired cells (three
of six artifacts are byte-identical), which demonstrates the distinction between outcome
replication and literal code identity. The 2D zero-repair selection is now frozen to the
four named campaigns: 156 draws over 20 raw blocks. Its block-level exact upper bound is
0.1684; pooling draws would give the invalid 0.0234 comparator, 7.2 times too tight.

Verification:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_paper2_statistics.py -q
PYTHONPATH=src .venv/bin/python scripts/paper2_statistics.py --check
```

The manuscript should preserve both the draw census and the stronger unit-correct block
statement. It must not call the 70 knob cells independent or distinct rollout samples.
