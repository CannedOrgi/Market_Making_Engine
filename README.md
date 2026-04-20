# Trader (L2 Order Book Depth)

This has **the full L2 order book depth** (10 levels).

| Column | Description |
|--------|-------------|
| `bid_px_00` .. `bid_px_09` | Bid prices, level 0 (best) to level 9 |
| `ask_px_00` .. `ask_px_09` | Ask prices, level 0 (best) to level 9 |
| `bid_sz_00` .. `bid_sz_09` | Bid sizes at each level |
| `ask_sz_00` .. `ask_sz_09` | Ask sizes at each level |
| `bid_ct_00` .. `bid_ct_09` | Number of orders at each bid level |
| `ask_ct_00` .. `ask_ct_09` | Number of orders at each ask level |

## Quick start

```bash
./setup_env.sh          # one time (skip if done for HW1a)
./run_testsample.sh     # test + evaluate (~5 seconds)
```

Open **`local_test_report/report.html`** to see results.
## Command reference

```bash
./setup_env.sh                           # setup (once)
./run_testsample.sh                      # test one date (~5s)
./run_testsample.sh 2024-10-11           # specific date
./run_testsample.sh all                  # all dates (~20s)
./.venv/bin/python run_strategy.py --data test_sample --output /dev/null --show-symbols
```
