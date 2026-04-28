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
