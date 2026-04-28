---
name: detect-price-patterns
description: Use when creating or modifying MQL5 logic to analyze price action and detect patterns (e.g., Fair Value Gaps, Order Blocks, Head & Shoulders). Strictly isolates calculation logic from visual rendering.
---

# Detect Price Patterns (MQL5 Calculation Logic)

Use this skill when writing algorithms to scan historical or live price data for specific candlestick formations or price action structures. 

## 1. Strict Separation of Concerns (No Rendering)
Never include chart object manipulation (`ObjectCreate`, `ObjectMove`, `ChartRedraw`) inside pattern detection functions. 
- Detection functions are purely analytical.
- They must evaluate price data and return a strictly typed `struct` containing the results.

## 2. Standardized Data Structures
Define a clear, lightweight `struct` to hold the pattern's attributes. The structure must contain all necessary data (prices, times, validity) so that a separate rendering or trading function can use it without recalculating anything.

```mql5
// Example structure for a pattern
struct SPricePattern {
    bool     isValid;      // True if the pattern is currently valid
    int      type;         // 1 for Bullish, -1 for Bearish, 0 for None
    datetime startTime;    // Anchor time 1 (e.g., oldest candle)
    datetime endTime;      // Anchor time 2 (e.g., newest candle)
    double   topPrice;     // Upper boundary of the pattern
    double   bottomPrice;  // Lower boundary of the pattern
};
```

## 3. Efficient Data Access
Choose the right data access method depending on the context:
- **Inside `OnCalculate` (Indicators):** Use the passed arrays (`open[]`, `high[]`, `low[]`, `close[]`, `time[]`). Always ensure arrays are addressed correctly using `ArraySetAsSeries`.
- **Inside `OnTick` or arbitrary functions (Expert Advisors/Scripts):**
  - For single or few candles, use direct functions like `iHigh()`, `iLow()`, `iTime()`.
  - For scanning large historical ranges (loops > 100 bars), use `CopyRates()` into an `MqlRates` array for better performance and memory efficiency.

## 4. Time vs. Index Coordinates
While algorithms iterate using bar indices (`shift` or `i`), the returned structure **must** use `datetime` for horizontal coordinates. Indices shift as new bars appear, making them unstable for long-term tracking or rendering, whereas `datetime` is absolute.

Example of a pure detection function (FVG):

```mql5
SPricePattern DetectFVG(string symbol, ENUM_TIMEFRAMES tf, int shift) {
    SPricePattern pattern;
    ZeroMemory(pattern); // Initialize with defaults (isValid = false)
    
    // Safety check: ensure enough bars exist
    if(Bars(symbol, tf) <= shift + 2) return pattern;

    double c2_high = iHigh(symbol, tf, shift + 2); // Oldest candle
    double c2_low  = iLow(symbol, tf, shift + 2);
    double c0_high = iHigh(symbol, tf, shift);     // Newest candle
    double c0_low  = iLow(symbol, tf, shift);

    // Bullish FVG Detection
    if(c0_low > c2_high) {
        pattern.isValid     = true;
        pattern.type        = 1;
        pattern.topPrice    = c0_low;
        pattern.bottomPrice = c2_high;
        pattern.startTime   = iTime(symbol, tf, shift + 2);
        pattern.endTime     = iTime(symbol, tf, shift);
        return pattern;
    }

    // Bearish FVG Detection
    if(c0_high < c2_low) {
        pattern.isValid     = true;
        pattern.type        = -1;
        pattern.topPrice    = c2_low;
        pattern.bottomPrice = c0_high;
        pattern.startTime   = iTime(symbol, tf, shift + 2);
        pattern.endTime     = iTime(symbol, tf, shift);
        return pattern;
    }

    return pattern;
}
```

## 5. Parameterization
Always parameterize the detection function with at least `symbol`, `timeframe`, and the starting `shift` (index). Do not hardcode `_Symbol` or `_Period` inside the function, as this limits its reuse in multi-currency or multi-timeframe Expert Advisors.

