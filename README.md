# HW1b Trader (L2 Order Book Depth)

Extend your HW1a strategy to use **the full L2 order book depth** (10 levels).

You now have access to the full top-10 bid/ask prices, sizes, and order counts.
You can reuse your L1 signals from HW1a and add L2 features on top.

## New data available

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

## How to approach this homework

This homework is about **comparing L1 and L2 signals** and understanding when depth
information adds value. Follow these steps systematically and document your findings
in `strategy.md`.

### Step 1: Establish your L1 baseline

Start from your HW1a strategy (or a simple L1 strategy if starting fresh). Run it
on the test sample and record the PnL for each date. This is your benchmark — every
L2 feature you add should be measured against it.

Questions to think about:
- What L1 signals did you use in HW1a? (mid-price, spread, top-of-book imbalance, momentum?)
- How did they perform across different dates? Were some dates better than others — why?

### Step 2: Explore the L2 data

Before building signals, look at the data. Load one date and examine the order book
structure across all 10 levels.

Questions to think about:
- How does the size distribution change from level 0 to level 9? Is most of the
  liquidity at the top of the book, or spread across levels?
- Does the depth profile look different across stocks? Across dates?
- Are there times when the top of book looks healthy but deeper levels are thin?
  What might that mean economically?

### Step 3: Build L2 signals and compare with L1

Construct at least two L2 signals. For each one, measure its correlation with
short-term forward returns and compare against the equivalent L1 signal.

Signal ideas to investigate:
- **Multi-level imbalance**: Does summing bid/ask sizes across multiple levels
  give a better signal than top-of-book alone? Or does it add noise? Try different
  numbers of levels and weighting schemes.
- **Depth-weighted mid-price (microprice)**: How does weighting the mid-price by
  order sizes compare to the simple arithmetic mid? Does the difference between
  microprice and raw mid carry predictive information?
- **Book depth and fragility**: Is the amount of liquidity behind the best quote
  informative? What happens when you trade into a thin book?
- **Order count**: Does the number of orders at a level tell you something different
  from the total size? (Hint: think about who places many small orders vs one large order.)

Key question: **Does L2 always help, or does it sometimes hurt?** Document what you find.

### Step 4: Use a train/test split

You have three dates of sample data. Use two for developing your signals (training)
and hold out one for testing. This is how you check whether your signals generalize
or are overfit to specific market conditions.

Questions to think about:
- Do your L2 signals have consistent predictive power across dates, or do they work
  on some dates and fail on others?
- If a signal works in training but fails in testing, what does that tell you about
  the signal's economic basis?
- How do you choose parameters (thresholds, lookback windows) without overfitting?

### Step 5: Combine L1 and L2 signals

The strongest strategies typically combine L1 and L2 information. Think about how
to combine them:
- Should L2 be a **signal** (directional prediction) or a **filter** (quality gate)?
- When L1 and L2 disagree, what should you do?
- Can you use L2 information to adjust your confidence in an L1 signal?

### Step 6: Adapt to market conditions

Not all trading days are the same. A strategy that works well on a volatile day may
fail on a calm day, and vice versa. Think about how to detect and adapt to different
market regimes.

Questions to think about:
- Can you do something to detect the trading session to characterize the day?
- Once you classify a day as calm or volatile, how should your strategy adjust?
  Should you change your signal thresholds, trade less frequently, or sit out entirely?

### Step 7: Risk management

No matter how good your signals are, risk management determines whether you survive
out-of-sample. Consider:
- Position limits and how to size your orders
- Stop-loss: when should you cut a losing position?
- Spread filter: should you trade when the spread is wide?
- End-of-day: do you want to flatten before close?

### What to write in strategy.md

Your `strategy.md` should tell the story of your investigation:
1. What L1 baseline did you start from and how did it perform?
2. What L2 signals did you build? Show the comparison with L1.
3. Which L2 features helped and which didn't? Explain why economically.
4. How did you handle train/test splitting? What were the results?
5. What is your final strategy and why did you choose this combination?

**We care about the process and reasoning, not just the final PnL.**
A well-documented strategy that thoughtfully compares L1 vs L2 signals and explains
the economic intuition will score higher than an unexplained black box — even if the
black box has better PnL.

## What to submit

Zip containing:
- `run_strategy.py` (required)
- `strategy.md` (required) — explain your strategy concept, what L2 features you used, and results

## Command reference

```bash
./setup_env.sh                           # setup (once)
./run_testsample.sh                      # test one date (~5s)
./run_testsample.sh 2024-10-11           # specific date
./run_testsample.sh all                  # all dates (~20s)
./.venv/bin/python run_strategy.py --data test_sample --output /dev/null --show-symbols
```
