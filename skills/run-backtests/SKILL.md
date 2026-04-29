---
name: run-backtests
description: Run MetaTrader 5 Strategy Tester backtests in Linux using Wine and a portable MT5 installation. Generate tester INI files, execute terminal64.exe through a local wrapper, inspect logs, and validate reports.
---

# Run Backtests — Linux + Wine + Portable MT5

## Environment

MetaTrader 5 is installed in portable mode.

Base Windows path:

C:\Program Files\MetaTrader 5\

Linux equivalent:

$WINEPREFIX/drive_c/Program Files/MetaTrader 5/

Do NOT use:

C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\

All paths passed to MetaTrader must be Windows-style paths.

---

## Command

Do NOT call `terminal64.exe` directly.

Do NOT use PowerShell.

Do NOT use `Start-Process`.

Use the local wrapper:

```bash
./mql5_backtest.sh "<INI_WIN>"
````

Example:

```bash
./mql5_backtest.sh "C:\Program Files\MetaTrader 5\MQL5\Profiles\Tester\backtest.ini"
```

---

## Required Files

The agent must generate:

1. Tester `.ini`
2. Report path
3. Optional run-specific log/report naming

Recommended INI location:

C:\Program Files\MetaTrader 5\MQL5\Profiles\Tester\backtest.ini

Recommended report location:

C:\Program Files\MetaTrader 5\MQL5\Files\Reports\backtest_report.html

Linux report equivalent:

$WINEPREFIX/drive_c/Program Files/MetaTrader 5/MQL5/Files/Reports/backtest_report.html

---

## Workflow

1. Confirm or infer test parameters from the user request.
2. Generate the tester `.ini`.
3. Run:

```bash
./mql5_backtest.sh "<INI_WIN>"
```

4. Inspect Strategy Tester logs.
5. Confirm the test started.
6. Confirm the test finished.
7. Confirm the report file exists.
8. Read and summarize actual report metrics.

Do not invent results.

---

## Defaults

Use these defaults unless the user changes them:

* Expert: Experts\codex\FVGTrader.ex5
* Symbol: GBPUSD
* Timeframe: M15
* Date range: last month
* Deposit: 100000
* Currency: USD
* Leverage: 1:100
* Tick model: real_ticks
* Optimization: off
* Visualization: off

---

## Tick Model Mapping

Use:

* open_prices → Model=1
* control_points → Model=2
* every_tick → Model=0
* real_ticks → Model=4

Default:

Model=4

---

## Optimization Mapping

* off → Optimization=0
* on → Optimization=1

Default:

Optimization=0

---

## Visualization Mapping

* off → Visual=0
* on → Visual=1

Default:

Visual=0

---

## Tester INI Template

```ini
[Tester]
Expert=Experts\codex\FVGTrader.ex5
Symbol=GBPUSD
Period=M15
Model=4
Optimization=0
FromDate=2026.03.28
ToDate=2026.04.28
ForwardMode=0
Deposit=100000
Currency=USD
Leverage=1:100
ExecutionMode=0
Visual=0
Report=C:\Program Files\MetaTrader 5\MQL5\Files\Reports\backtest_report.html
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
```

---

## Validation

After running the wrapper:

1. Check that the report exists.
2. Check tester logs.
3. Confirm terminal shutdown occurred.
4. Extract actual metrics from the generated report.
5. Report:

   * Net profit
   * Balance drawdown
   * Equity drawdown
   * Total trades
   * Profit factor
   * Expected payoff
   * Recovery factor, if present

If the report does not exist, inspect logs and state that the backtest failed.

---

## Rules

* Never use PowerShell syntax.
* Never use AppData terminal-id paths.
* Never expose Wine quoting to the agent.
* Always use wrapper scripts.
* Always validate using logs and report files.
