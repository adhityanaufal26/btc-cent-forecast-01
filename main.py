#!/usr/bin/env python3
"""BTC 4h forecast for make.fun btc-cent-forecast-01.

Model: shrunk mean-reversion blend.
    forecast = last
             + 0.10 * (last - price 60 min ago)
             + 0.25 * (24h mean - last)
    |adjustment| capped at 1% of last; rounded to 5 decimals;
    clamped to (0, 10,000,000).

Rationale: scoring is mean absolute error, so the forecast is the conditional
median 4h out. In the practice window BTC's 4h returns are strongly
mean-reverting (1h-return autocorrelation -0.25, 4h-return autocorrelation
-0.31), so the forecast pulls toward the 24h mean. The small +0.10 x 1h-move
term trims the reversion when the recent move agrees with the deviation, so a
steady trend does not get over-corrected. Coefficients are shrunk to ~half
their in-sample regression values because the regression is one 4-day window
with overlapping targets and the final is an unseen regime. No drift term:
the window's mean 4h drift is regime-specific and must not be baked in.
The 1% cap is a pure safety valve; it never binds on practice/backtest data
(largest observed |adjustment| in the practice window is $381.76, well under
the 1% cap of ~$740 at those prices).

Verified in-session 2026-11-15 (fresh re-type, this session): all 6 practice
outputs match the research spec exactly (p00 74746.13405, p01 74501.40635,
p02 73869.56903, p03 73555.35081, p04 73904.4032, p05 73670.81331); two full
runs byte-identical; single-case run gives the same p03 price.

Python 3.13 stdlib only. No network, no randomness, no time dependence.
Reads $MAKEFUN_INPUT_DIR (else /input/), writes $MAKEFUN_OUTPUT_DIR
(else /output/). One output per *.in file, in name order.
"""

import json
import os
import sys

MOMENTUM_WEIGHT = 0.10   # weight on (last - price 60 min ago)
REVERSION_WEIGHT = 0.25  # weight on (24h mean - last)
CAP_FRACTION = 0.01      # |adjustment| capped at 1% of last
MEAN_WINDOW = 1440       # 24h of 1-minute closes
MOMENTUM_LAG = 60        # minutes back for the recent move
PRICE_MIN = 0.0
PRICE_MAX = 10_000_000.0


def forecast_price(prices):
    """Forecast the close 240 minutes after the last price in `prices`."""
    if not prices:
        return 1.0
    last = float(prices[-1])

    # Price 60 minutes ago; fall back to the earliest close on short history.
    idx = len(prices) - 1 - MOMENTUM_LAG
    price_ago = float(prices[idx]) if idx >= 0 else float(prices[0])

    # Mean of the last 24h of closes (or all closes if fewer exist).
    window = prices[-MEAN_WINDOW:]
    mean_24h = sum(float(p) for p in window) / len(window)

    adjustment = (MOMENTUM_WEIGHT * (last - price_ago)
                  + REVERSION_WEIGHT * (mean_24h - last))

    cap = CAP_FRACTION * abs(last)
    if adjustment > cap:
        adjustment = cap
    elif adjustment < -cap:
        adjustment = -cap

    price = round(last + adjustment, 5)
    if price <= PRICE_MIN:
        price = round(PRICE_MIN + 0.00001, 5)
    elif price >= PRICE_MAX:
        price = round(PRICE_MAX - 0.00001, 5)
    return price


def run(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for name in sorted(os.listdir(input_dir)):
        if not name.endswith(".in"):
            continue
        case_id = name[:-3]
        with open(os.path.join(input_dir, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        markets = case.get("markets") or []
        prices = []
        for market in markets:
            if market.get("id") == "btc-usdc":
                prices = market.get("prices") or []
                break
        if not prices and markets:
            prices = markets[0].get("prices") or []
        price = forecast_price(prices)
        out = {"forecasts": [{"case": case_id, "price": price}]}
        out_path = os.path.join(output_dir, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f)
            f.write("\n")


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input/"
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output/"
    run(input_dir, output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
