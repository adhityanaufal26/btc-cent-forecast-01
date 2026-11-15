# btc-cent-forecast-01

make.fun entry: forecast Bitcoin's US-dollar price 4 hours ahead from the
last 72 hours of 1-minute closes, lowest mean absolute error in cents wins.

## Model

Shrunk mean-reversion blend, Python 3.13 stdlib only:

```
forecast = last
         + 0.10 * (last - price 60 min ago)
         + 0.25 * (24h mean - last)
```

`|adjustment|` capped at 1% of `last`; rounded to 5 decimals; clamped to
(0, 10,000,000). BTC's 4h returns in the practice window are strongly
mean-reverting (1h-return autocorrelation -0.25, 4h-return autocorrelation
-0.31), so the forecast pulls toward the 24h mean; the small momentum term
trims the reversion when the recent move agrees with the deviation.
Coefficients are shrunk to ~half their in-sample regression values because
the regression is one 4-day window and the final is an unseen regime.

## Run

```
MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=<out> python3 main.py
```

Reads every `*.in` in the input dir, writes one `<id>.out` per case:
exactly `{"forecasts":[{"case":"<id>","price":<number>}]}`.

## Practice results (cents MAE, lower is better)

| evaluation | this model | persistence |
|------------|-----------|-------------|
| Practice p00–p04 (5 known cases) | 47,169.8 | 47,054.7 |
| Practice p00–p05, p05 actual UP | 42,535.3 | 44,521.6 |
| Practice p00–p05, p05 actual DOWN | 46,699.7 | 44,521.6 |
| Walk-forward, 64 hourly ckpts Nov 8–10 | 41,882.2 | 44,629.8 |
