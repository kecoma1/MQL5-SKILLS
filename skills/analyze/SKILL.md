---
name: analyze
description: Analyze market regime and session structure in this MQL5 workspace using reusable CSV exports from an MQL5 script. Use when Codex needs to classify a market as Tendencial or Lateral with moving average and ATR, export per-session data to Terminal Common Files for M15, H1, and D1, and then read those CSV files directly to summarize insights and recommendations by session without recreating scripts that already exist.
---

# Analyze

## Overview

Use this skill to analyze markets by session in this workspace.

Keep the workflow simple:
- export CSV data with the MQL5 script
- read the CSV directly
- answer the user from the exported data

Do not create HTML reports.
Do not rely on Python for this workflow.

## Reusable files

Use these files as the primary workflow:

- `Scripts\codex\SessionMarketExporter.mq5`
- `Presets\SessionMarketExporter-<SYMBOL>-lastyear.set`
- `config\session-market-exporter-<symbol>-lastyear.ini`

Do not recreate them on each request. Reuse them and only update them when the export logic is actually wrong.

## Goal

Produce session-level market analysis for `M15`, `H1`, and `D1` with:

- Session name
- Moving average context
- ATR context
- Market type: `Tendencial` or `Lateral`
- Trend direction
- Session volatility
- Session insights
- Session recommendations

## Export workflow

1. Compile `Scripts\codex\SessionMarketExporter.mq5`.
2. Create or update a script preset under `MQL5\Presets\` with plain script values.
3. Create or update a startup `.ini` under `MQL5\config\` using `[StartUp] Script=...`.
4. Close any running `terminal64.exe` before launching.
5. Launch MT5 with `/config:...`.
6. Export CSV files into `Terminal\Common\Files\`.
7. Read the generated CSV files directly and summarize them for the user.

## Script preset rule

For `ScriptParameters`, use a normal script preset with simple `key=value` lines.

Correct example:

```ini
InpSymbol=EURUSD
InpLookbackDays=365
InpMAPeriod=20
InpMAMethod=0
InpATRPeriod=14
InpTrendSlopeAtrRatio=0.15
InpTrendDistanceAtrRatio=0.20
InpOutputPrefix=session_market
```

Do not use the optimization format `value||start||step||stop||selected` in a script preset. That format is for optimization, not for scripts.

## Startup ini pattern

Use this structure:

```ini
[Common]
Login=4000030114

[Experts]
Enabled=1

[StartUp]
Symbol=EURUSD
Period=M15
Script=codex\SessionMarketExporter
ScriptParameters=SessionMarketExporter-EURUSD-lastyear.set
ShutdownTerminal=1
```

The `Script=` path is relative to `MQL5\Scripts\`.
The `ScriptParameters=` file is loaded from `MQL5\Presets\`.

## Exported CSV files

Expect one CSV per timeframe:

- `session_market_<SYMBOL>_M15.csv`
- `session_market_<SYMBOL>_H1.csv`
- `session_market_<SYMBOL>_D1.csv`

In this workspace they are currently exported directly under:

- `C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\Common\Files\`

## CSV expectations

The exported CSV should include fields like:

- `session`
- `ma_value`
- `ma_slope_points`
- `atr_points`
- `distance_to_ma_points`
- `trend_direction`
- `market_type`
- `trend_score`

Treat these CSV files as the source of truth.

## Session model

Use these session buckets for intraday analysis:

- `Asia`: 00:00-08:00
- `London`: 08:00-16:00
- `NewYork`: 16:00-24:00

For `D1`, use a single `Daily` session.

Treat these windows as UTC unless the script or user explicitly changes them.

## Interpretation rules

- `Tendencial`: moving average slope and price-vs-MA distance are large enough relative to ATR.
- `Lateral`: MA slope and distance-to-MA do not show directional expansion versus ATR.
- `Volatilidad Alta`: current ATR is materially above the session median.
- `Volatilidad Baja`: current ATR is materially below the session median.

Use the exported values directly. Do not invent extra indicators that are not in the CSV.

## Final analysis format

When answering the user, summarize:

- the current regime for each timeframe
- the regime by session
- the volatility by session
- practical recommendations by session
- any cross-timeframe alignment or conflict

Keep the tone analytical and concise.

## Example commands

Compile:

```powershell
& 'C:\Program Files\MetaTrader 5\MetaEditor64.exe' /compile:'C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\Scripts\codex\SessionMarketExporter.mq5' /log:'C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\Logs\session-market-exporter-compile.log'
```

Run the exporter:

```powershell
Get-Process terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process -FilePath 'C:\Program Files\MetaTrader 5\terminal64.exe' -ArgumentList '/config:C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\config\session-market-exporter-eurusd-lastyear.ini' -Wait
```

## Validated paths in this workspace

- `C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\Common\Files\session_market_EURUSD_M15.csv`
- `C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\Common\Files\session_market_EURUSD_H1.csv`
- `C:\Users\user-id\AppData\Roaming\MetaQuotes\Terminal\Common\Files\session_market_EURUSD_D1.csv`
