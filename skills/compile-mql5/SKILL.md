---
name: compile-mql5
description: Use when compiling MQL5 experts, indicators, scripts, or include-dependent code in this workspace from the terminal. Follow the local MetaEditor command pattern and always inspect the compilation log after running it.
---

# Compile MQL5

Use this skill when compiling `.mq5` files in this repository.

## Command

Use `MetaEditor64.exe` from the local MetaTrader installation.

Example command:

```powershell
& 'C:\Program Files\MetaTrader 5\MetaEditor64.exe' /compile:'C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\codex\FVG.mq5' /log:'C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Logs\codex-fvg-compile.log'
```

Adjust the compiled file and log path to the target being worked on.

## Log Review

Always read the log after compiling.

For the current EA example, the log is:

`C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Logs\codex-fvg-compile.log`

Do not assume compilation succeeded just because the command returned exit code `0`.
Check the log and report:

1. Number of errors.
2. Number of warnings.
3. Important file paths mentioned by the compiler.
4. Whether the expected `.ex5` file was produced or updated.
