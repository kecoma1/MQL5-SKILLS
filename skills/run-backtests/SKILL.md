---
name: run-backtests
description: Use when running MetaTrader 5 Strategy Tester backtests from the terminal in this workspace. Ask the user for the test configuration field by field before launching the test, using the current project defaults unless the user changes them.
---

# Run Backtests

Use this skill when the user wants to run a MetaTrader 5 backtest from the terminal.

## Command

Run the main MetaTrader 5 installation with a tester `.ini` file:

```powershell
Start-Process -FilePath 'C:\Program Files\MetaTrader 5\terminal64.exe' -ArgumentList '/config:C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config\codex-fvgtrader-gbpusd-lastmonth-v2.ini' -Wait
```

Use that command pattern for backtests in this workspace.

## Required Workflow

Before running the test, ask the user for the configuration field by field.
Do not assume the final setup without confirming each field first.
When asking for a field, use JSON Schema style notation like this:

```json
{
  "type": "object",
  "properties": {
    "risk_level": {
      "type": "string",
      "description": "Select your preferred risk level",
      "enum": ["low", "medium", "high"]
    }
  },
  "required": ["risk_level"]
}
```

Use the same notation for backtest questions. Add `enum` options whenever the field has a bounded set of valid choices.

Ask in this order:

1. Expert or strategy file.
2. Symbol.
3. Timeframe.
4. Date range.
5. Deposit.
6. Deposit currency.
7. Leverage.
8. Tick model.
9. Optimization on or off.
10. Visualization on or off.

Use these question shapes:

1. Expert or strategy file:

```json
{
  "type": "object",
  "properties": {
    "expert": {
      "type": "string",
      "description": "Select the Expert Advisor or strategy file to run",
      "enum": ["Experts\\\\codex\\\\FVGTrader.ex5"]
    }
  },
  "required": ["expert"]
}
```

2. Symbol:

```json
{
  "type": "object",
  "properties": {
    "symbol": {
      "type": "string",
      "description": "Select the symbol to backtest",
      "enum": ["GBPUSD"]
    }
  },
  "required": ["symbol"]
}
```

3. Timeframe:

```json
{
  "type": "object",
  "properties": {
    "timeframe": {
      "type": "string",
      "description": "Select the chart timeframe",
      "enum": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
    }
  },
  "required": ["timeframe"]
}
```

4. Date range:

```json
{
  "type": "object",
  "properties": {
    "date_range": {
      "type": "string",
      "description": "Select the date range preset or provide a custom range",
      "enum": ["last_week", "last_month", "last_3_months", "custom"]
    }
  },
  "required": ["date_range"]
}
```

5. Deposit:

```json
{
  "type": "object",
  "properties": {
    "deposit": {
      "type": "number",
      "description": "Enter the starting deposit amount"
    }
  },
  "required": ["deposit"]
}
```

6. Deposit currency:

```json
{
  "type": "object",
  "properties": {
    "currency": {
      "type": "string",
      "description": "Select the deposit currency",
      "enum": ["USD", "EUR", "GBP"]
    }
  },
  "required": ["currency"]
}
```

7. Leverage:

```json
{
  "type": "object",
  "properties": {
    "leverage": {
      "type": "string",
      "description": "Select the leverage",
      "enum": ["1:30", "1:50", "1:100", "1:200", "1:500"]
    }
  },
  "required": ["leverage"]
}
```

8. Tick model:

```json
{
  "type": "object",
  "properties": {
    "tick_model": {
      "type": "string",
      "description": "Select the tick generation model",
      "enum": ["open_prices", "control_points", "every_tick", "real_ticks"]
    }
  },
  "required": ["tick_model"]
}
```

9. Optimization on or off:

```json
{
  "type": "object",
  "properties": {
    "optimization": {
      "type": "string",
      "description": "Select whether optimization is enabled",
      "enum": ["off", "on"]
    }
  },
  "required": ["optimization"]
}
```

10. Visualization on or off:

```json
{
  "type": "object",
  "properties": {
    "visualization": {
      "type": "string",
      "description": "Select whether visualization is enabled",
      "enum": ["off", "on"]
    }
  },
  "required": ["visualization"]
}
```

## Defaults

Use these values as defaults unless the user changes them:

1. Expert: `Experts\codex\FVGTrader.ex5`
2. Symbol: `GBPUSD`
3. Timeframe: `M15`
4. Date range: last month
5. Deposit: `100000`
6. Currency: `USD`
7. Leverage: `1:100`
8. Tick model: real ticks
9. Optimization: off
10. Visualization: off

## Tester INI

Create or update a tester `.ini` with the confirmed values.

Use this structure:

```ini
[Tester]
Expert=<ask_user_expert>
Symbol=GBPUSD
Period=M15
Model=4
Optimization=0
FromDate=2026.02.28
ToDate=2026.03.28
ForwardMode=0
Deposit=100000
Currency=USD
Leverage=1:100
ExecutionMode=0
Visual=0
Report=<ask_user_report>
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
```

## Validation

After launching the test:

1. Read the tester logs.
2. Confirm the backtest really started.
3. Confirm it finished.
4. Read the generated report or result files.
5. Summarize the actual metrics for the user.

If the terminal opens but the test does not run, do not invent results.
State clearly that the launch failed and inspect the tester log before trying again.
