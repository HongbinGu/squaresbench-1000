# SquaresBench-1000

A certified geometric packing benchmark: 1,000 instances of packing *n* unit
squares (n = 1 … 1,000) into the smallest axis-aligned square, together with an
interval-arithmetic verifier that certifies every configuration and a
digit-budget experiment that quantifies the decimal precision required for a
lossless serialisation round trip.

This repository accompanies the manuscript
*"SquaresBench-1000: a certified geometric packing benchmark and a 17-digit
precision trap in numerical certification pipelines"*.

## Contents

```
data/
  submission.csv          the full benchmark: 500,500 rows, columns
                          n, square_id, x, y, angle; coordinates are decimal
                          literals with up to 17 significant digits
                          (25.1 MB, SHA-256 e0d68933893dcbb91d2f0e23e7c4d5ce…)
  per_puzzle.csv          certified side length L per instance
  counterexamples_10.csv  the ten instances that are rejected after a single
                          binary64 round trip; use them as regression tests
scripts/
  jocs_digit_budget.py    Section 4 experiment: certification rate vs. number
                          of retained decimal digits (k = 12 … 17)
  jocs_undecided_rate.py  Section 3 experiment: fraction of candidate pairs
                          that binary64 cannot decide (92.9%)
  jocs_paper_assets.py    reproduces every figure of the paper
results/
  *.json                  raw outputs of the scripts above
verifier/
  interval-arithmetic verifier (see below)
```

## Requirements

Python ≥ 3.9 with `mpmath`, `numpy`, `matplotlib`, `pandas`.

```bash
python -m pip install mpmath numpy matplotlib pandas
```

## Reproducing the paper

```bash
# digit-budget curve (Section 4): ~1 h on a four-core laptop
python scripts/jocs_digit_budget.py --sample 150 --workers 6

# undecided-pair rate (Section 3)
python scripts/jocs_undecided_rate.py --sample 120

# every figure of the paper
python scripts/jocs_paper_assets.py
```

## Key numbers

| Quantity | Value |
|---|---|
| Aggregate score (sum over n = 1 … 1,000) | 22.250911 |
| After one binary64 round trip | 22.322617 |
| Aggregate loss of the ten counterexamples | 0.071707 |
| Digit budget: certification rate at k = 12 → 17 | 49.3% → 100% |
| Candidate pairs undecided in binary64 | 92.9% |

## License

MIT — see [LICENSE](LICENSE).
