---
name: interface
description: Use the local MetaTrader 5 Python trading CLI at MQL5\Scripts\interface.py. Use when Codex needs to explain, run, validate, or troubleshoot command-line trading operations such as opening market or pending orders, setting or editing SL/TP, closing positions, canceling pending orders, listing opened trades or pending orders, reading recent trade history, or checking account and symbol details.
---

# Interface

Use this skill for the local MT5 Python CLI wrapper located at:

`C:\Users\kecom\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Scripts\interface.py`

The script is intended to operate MetaTrader 5 through the Python `MetaTrader5` package. Treat it as a live-trading interface: do not submit market, pending, close, edit, or cancel commands unless the user explicitly asked for that action and the target account/symbol/ticket/volume/stops are clear.

## Before Running

1. Work from the script directory unless there is a reason not to:

```powershell
cd C:\Users\kecom\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Scripts
```

2. Confirm a real Python executable is available. If `python` resolves to `C:\Users\kecom\AppData\Local\Microsoft\WindowsApps\python.exe`, it may hang or open the Microsoft Store alias instead of running scripts.

3. Confirm the package is installed when execution is required:

```powershell
python -m pip install MetaTrader5
```

4. Confirm MetaTrader 5 is installed, logged in, and allowed to trade. If needed, pass `--terminal`, `--login`, `--password`, and `--server`.

5. For read-only inspection, prefer `--cmd=help`, `--cmd=opened`, `--cmd=orders`, `--cmd=history`, `--cmd=account`, and `--cmd=symbol`.

## Core Commands

Show the built-in help:

```powershell
python interface.py --cmd=help
```

Open a market buy using SL/TP distances in points:

```powershell
python interface.py --cmd=open --type=buy --market=EURUSD --lot=0.10 --sl-points=200 --tp-points=400
```

Open a pending buy limit using absolute SL/TP prices:

```powershell
python interface.py --cmd=open --type=buylimit --market=EURUSD --lot=0.10 --price=1.08000 --SL=1.07500 --TP=1.09000
```

Close one open position by ticket:

```powershell
python interface.py --cmd=close --id=322334
```

Close all positions, optionally filtered by market:

```powershell
python interface.py --cmd=close --all --market=EURUSD
```

Edit SL/TP on an open position or pending order:

```powershell
python interface.py --cmd=edit --id=23232 --TP=1.09250
python interface.py --cmd=edit --id=23232 --sl-points=150 --tp-points=300
```

Cancel a pending order:

```powershell
python interface.py --cmd=cancel --id=998877
```

List current positions:

```powershell
python interface.py --cmd=opened
python interface.py --cmd=opened --market=EURUSD
```

List pending orders:

```powershell
python interface.py --cmd=orders
python interface.py --cmd=orders --market=EURUSD
```

Read recent history. The misspelled alias `hystory` is accepted for compatibility:

```powershell
python interface.py --cmd=history --last=10
python interface.py --cmd=hystory --last=10 --market=EURUSD
```

Check account or symbol details:

```powershell
python interface.py --cmd=account
python interface.py --cmd=symbol --market=EURUSD
```

## Parameter Rules

Use `--SL` and `--TP` for absolute prices only. Example: `--SL=1.07500`, not `--SL=23` unless 23 is truly the broker price.

Use distance parameters when the user describes stops in points or pips:

```powershell
--sl-points=200 --tp-points=400
--sl-pips=20 --tp-pips=40
```

Use `--price` for pending order entry price. Market orders can omit `--price`; the script uses the current ask for buys and bid for sells.

Use `--stoplimit` for `buystoplimit` and `sellstoplimit` orders.

Use `--lot` or `--volume` for trade volume.

Use `--deviation` for allowed slippage in points on market entries and closes.

Use `--filling` when the broker rejects the default filling mode. Valid values are `ioc`, `fok`, `return`, and `boc`.

Use `--json` when another script needs machine-readable output. Use `--dry-run` to build and print an MT5 trade request without sending it to the broker.

## Safety Workflow

Before sending live-trading commands, restate the exact operation in concrete terms: command, symbol, type, volume, price if pending, SL, TP, ticket if applicable, and whether values are absolute prices or distances.

If the user provides ambiguous stops like `SL=23`, ask whether they mean an absolute price, points, or pips before executing. Do not convert ambiguous stop values silently.

If the user asks only how to do something, provide commands and avoid running them. If testing an order workflow, use `--dry-run` first.

If MT5 returns a non-success `retcode`, report the `retcode`, `retcode_name`, and `comment`. Suggest the smallest relevant next check, such as symbol visibility, filling mode, invalid stops, market closed, insufficient margin, or wrong ticket type.

## Common Troubleshooting

If Python hangs or does not print output, inspect the executable:

```powershell
where.exe python
Get-Command python | Select-Object Source,CommandType
```

If `MetaTrader5` cannot import, install it into the Python interpreter that will run `interface.py`.

If MT5 cannot initialize, make sure the terminal is open or pass the full path:

```powershell
python interface.py --cmd=account --terminal "C:\Path\To\terminal64.exe"
```

If closing by `--id` fails because the ticket is not an open position, check pending orders with `--cmd=orders`; pending orders are removed with `--cmd=cancel`.
