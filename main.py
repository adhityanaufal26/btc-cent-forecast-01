#!/usr/bin/env python3
"""BTC 4h forecast for make.fun btc-cent-forecast-01.

A damped pull toward the 24-hour mean, with a small nudge from the last
hour's move:

    guess = last
          + 0.10 * (last - close 60 minutes earlier)
          + 0.25 * (mean of the last 1440 closes - last)

The pull is capped at 1% of last, the guess is rounded to 5 decimals and
kept inside (0, 10,000,000).

Why this shape: the score is mean absolute error, so the best single number
is the middle of where the price might land 240 minutes out. In the
practice stretch BTC snaps back far more than it trends: hourly returns
correlate -0.25 with the next hour, four-hour returns -0.31 with the next
four hours. So the forecast leans back toward the day mean. The 0.10 term
softens that lean when the last hour moved the same way as the gap, so a
steady slide is not over-corrected. Both weights are about half what a
straight fit on the practice stretch would suggest, because that fit comes
from a single four-day slide with overlapping targets and the final runs on
days nobody has seen. No built-in drift: the stretch's -0.19% mean four-hour
drift belongs to that stretch, not to the model. The 1% cap is only a guard
rail; it never bites on the practice or backtest checkpoints.

Python 3.13, standard library only. No network, no randomness, no clock.
Reads $MAKEFUN_INPUT_DIR (or /input/), writes $MAKEFUN_OUTPUT_DIR (or
/output/), one output per *.in file, in name order.

Checked 2026-11-15 on the six practice cases: every price matches the
research spec exactly, two runs byte-identical, one case alone agrees.
"""

import json
import os
import sys

MOMENTUM = 0.10    # pull from the last hour's move
REVERSION = 0.25   # pull toward the day mean
CAP = 0.01         # widest allowed nudge, as a share of last
DAY_MINUTES = 1440  # one full day of 1-minute closes
HOUR_MINUTES = 60   # how far back the recent move is measured
LOW = 0.0
HIGH = 10_000_000.0


def predict_4h(closes):
    """Guess the close 240 minutes after the last close in `closes`."""
    if not closes:
        return 1.0  # empty history: smallest positive guess
    last = float(closes[-1])

    back = len(closes) - 1 - HOUR_MINUTES
    hour_ago = float(closes[back]) if back >= 0 else float(closes[0])

    day = closes[-DAY_MINUTES:]
    day_mean = sum(float(c) for c in day) / len(day)

    move = last - hour_ago
    gap = day_mean - last
    nudge = MOMENTUM * move + REVERSION * gap

    limit = CAP * abs(last)
    if nudge > limit:
        nudge = limit
    elif nudge < -limit:
        nudge = -limit

    guess = round(last + nudge, 5)
    if guess <= LOW:
        guess = round(LOW + 0.00001, 5)
    elif guess >= HIGH:
        guess = round(HIGH - 0.00001, 5)
    return guess


def run_cases(in_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name in sorted(os.listdir(in_dir)):
        if not name.endswith(".in"):
            continue
        case = name[:-3]
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        series = data.get("markets") or []
        closes = []
        for m in series:
            if m.get("id") == "btc-usdc":
                closes = m.get("prices") or []
                break
        if not closes and series:
            closes = series[0].get("prices") or []
        guess = predict_4h(closes)
        payload = {"forecasts": [{"case": case, "price": guess}]}
        with open(os.path.join(out_dir, case + ".out"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
            fh.write("\n")


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input/"
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output/"
    run_cases(in_dir, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
