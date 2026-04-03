---
name: candles-and-series
description: Use when working with MqlRates arrays, candles, or time series in MQL5 in this workspace. Follow the local convention for treating index 0 as the most recent candle by explicitly enabling series mode.
---

# Candles And Series

Use this skill when loading or processing candles in MQL5 with `MqlRates[]`, `CopyRates`, `CopyOpen`, `CopyHigh`, `CopyLow`, `CopyClose`, or similar functions.

## Rule

When the logic depends on candle `0` being the most recent candle, always call:

```mq5
ArraySetAsSeries(array, true);
```

Apply this before reading the array contents.

In this workspace, the default expectation for candle-processing logic is:

- index `0`: most recent candle
- index `1`: previous candle
- index `2`: older candle

## Example

```mq5
MqlRates rates[];
ArraySetAsSeries(rates, true);

int copied = CopyRates(_Symbol, _Period, 0, 3, rates);
if(copied < 3)
   return false;

double current_open = rates[0].open;
double previous_high = rates[1].high;
double older_low = rates[2].low;
```

## Validation

Before trusting candle logic, verify these points:

1. `ArraySetAsSeries(..., true)` is applied when the code expects candle `0` to be the latest.
2. `CopyRates(...)` loads only the number of candles actually needed for the pattern.
3. The code does not mix series-style indexing with chronological indexing by mistake.
4. Conditions that refer to candle 1, 2, or 3 are mapped explicitly to the intended indices.

## Closed Candles

For patterns that must be built only from closed candles, do not use `CopyRates(..., 0, ...)` if the current forming candle must be excluded.

In those cases, start from `1`, so `rates[0]` represents the last closed candle.

## Recalculation Vs Entry

Separate these two responsibilities explicitly:

- when the pattern is recalculated
- when entry conditions are evaluated

If the pattern depends on closed candles, it can be recalculated on a new bar.
If the entry depends on price crossing a level, that condition may need to be checked on every tick.

## Candle Numbering

When a pattern depends on candle numbering, the convention must be written explicitly.
It is not enough to say `ArraySetAsSeries(..., true)`.

Also state what each index means in that context, for example:

- `rates[0]` = last closed candle when using `CopyRates(..., 1, ...)`
- `rates[1]` = previous closed candle
- `rates[2]` = third closed candle back

## Pattern Debugging

When there is doubt about a candle-pattern calculation, create a separate EA test.

That EA should print times, OHLC values, indices, and pattern results so the calculation can be validated without mixing it with trading logic.

## Function Ownership

If a class or function is responsible for calculating a pattern, it should also load the candles inside that same function.

Do not split that responsibility between the EA and the class, because that can make each place use a different window, a different shift, or a different array orientation.
