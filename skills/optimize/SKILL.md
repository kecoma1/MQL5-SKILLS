---
name: optimization
description: Run MetaTrader 5 parameter optimizations in this workspace and summarize real results from exported optimization reports. Use when Codex needs to optimize EA inputs such as SL, TP, RSI values, or other inputs for experts under MQL5\Experts, by generating a tester .ini with [TesterInputs], launching MT5 from the terminal, and reading the resulting XML ranking.
---

# Optimization

## Overview

Use this skill for MT5 strategy optimizations in this workspace.

Confirm the optimization setup, write a tester `.ini` under `MQL5\config\`, place the parameter ranges in `[TesterInputs]`, close any running MT5 instance, launch `terminal64.exe` with `/config:...`, and summarize the actual ranking from the exported XML report.

## Required workflow

1. Confirm the test configuration before launching.
2. Ask for these fields in this order unless the user has already specified them clearly:
   - Expert or strategy file
   - Symbol
   - Timeframe
   - Date range
   - Deposit
   - Deposit currency
   - Leverage
   - Tick model
   - Optimization on or off
   - Visualization on or off
3. Ask which input parameters will be optimized and the exact ranges.
4. Create or update a tester `.ini` under `MQL5\config\`.
5. Put the optimization ranges inside a `[TesterInputs]` section in that `.ini`.
6. Create `MQL5\backtest\reports\` if missing.
7. If MT5 is already running, close it before launch.
8. Launch MT5 with the generated `.ini`.
9. Read terminal and tester logs to confirm the optimization really started and finished.
10. Read the exported optimization XML and summarize the best passes.

## Critical local rule

In this workspace, command-line optimization works when the parameter ranges are defined in `[TesterInputs]` inside the tester `.ini`.

Do not rely on `ExpertParameters=...set` for optimization ranges here. That produced the tester error:
`no optimized parameter selected, please check input(s) to be optimized and set start, step and stop values`

## Tester ini pattern

Use this structure:

```ini
[Tester]
Expert=codex\RSICrossTrader.ex5
Symbol=GBPUSD
Period=M15
Model=4
Optimization=1
FromDate=2026.02.28
ToDate=2026.03.28
ForwardMode=0
Deposit=100000
Currency=USD
Leverage=1:100
ExecutionMode=0
OptimizationCriterion=0
Visual=0
Report=MQL5\backtest\reports\report_name
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0

[TesterInputs]
InpRSIPeriod=4||4||1||4||N
InpRSIPrice=1||1||0||7||N
InpBuyLevel=30.0||30.0||3.000000||300.000000||N
InpSellLevel=70.0||70.0||7.000000||700.000000||N
InpLots=0.01||0.01||0.001000||0.100000||N
InpStopLossPoints=100||100||10||120||Y
InpTakeProfitPoints=100||100||10||120||Y
InpMagicNumber=20260328||20260328||1||202603280||N
InpOnePositionPerSymbol=true||false||0||true||N
```

## Input range format

Use MT5 optimization format:

```text
ParameterName=current||start||step||stop||selected
```

Rules:
- Use `Y` only for parameters being optimized.
- Use `N` for fixed parameters.
- Keep the current value equal to the chosen start value unless there is a reason not to.
- Preserve the parameter names exactly as declared in the EA inputs.

Example:

```text
InpStopLossPoints=100||100||10||120||Y
InpTakeProfitPoints=100||100||10||120||Y
```

## Path rules

- Write `Expert=` relative to `MQL5\Experts\`. Use `codex\RSICrossTrader.ex5`, not `Experts\codex\RSICrossTrader.ex5`.
- Write the tester `.ini` under `MQL5\config\`.
- Export reports to `MQL5\backtest\reports\report_name`.
- Optimization exports a readable XML workbook. Use that XML as the primary source.

## Launch command

Use this command pattern:

```powershell
Start-Process -FilePath 'C:\Program Files\MetaTrader 5\terminal64.exe' -ArgumentList '/config:C:\Users\<user-id>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\config\your-optimization.ini' -Wait
```

Before launching, close any existing MT5 process. Otherwise the tester may not run.

## Validation

Read these logs after launch:

- `Terminal\...\logs\YYYYMMDD.log`
- `Terminal\...\tester\logs\YYYYMMDD.log`

Treat these tester log lines as authoritative:

- Start confirmed: `complete optimization started`
- Success confirmed: `optimization finished, total passes N`
- Broken config: `no optimized parameter selected`

If the optimization did not start, inspect the `.ini` and especially `[TesterInputs]` before retrying.

## Reading the report

Optimization results are exported as an XML workbook under `MQL5\backtest\reports\`.

Read that XML and extract at least:
- Pass
- Result
- Profit
- Profit Factor
- Equity DD %
- Trades
- All optimized input columns, such as `InpStopLossPoints` and `InpTakeProfitPoints`

Summarize:
- The best combination
- The top ranking passes
- The report path used
- Whether the optimization finished successfully

## Example from this workspace

This exact optimization was validated successfully:
- Expert: `codex\RSICrossTrader.ex5`
- Symbol: `GBPUSD`
- Period: `M15`
- Dates: `2026.02.28` to `2026.03.28`
- Model: real ticks (`Model=4`)
- Optimization: on
- Visual: off
- Optimized params:
  - `InpStopLossPoints=100||100||10||120||Y`
  - `InpTakeProfitPoints=100||100||10||120||Y`

It completed with 9 passes and produced:
`MQL5\backtest\reports\codex_rsicrosstrader_gbpusd_lastmonth_opt_sltp_100_120.xml`
