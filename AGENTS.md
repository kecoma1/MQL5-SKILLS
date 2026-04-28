# AGENTS.md

## Mission

This repository builds modular MQL5 Expert Advisors from reusable trading blocks.

The user describes manual trading protocols. Codex must translate them into explicit module contracts before implementation.

## Hard rules

- Never mix detection, rendering, entry decision, risk sizing, position management, and trade execution in the same module.
- Default all new EAs to trading disabled.
- Never execute live trades from scripts unless the user explicitly asks for live execution in the same prompt.
- Prefer demo/tester workflows.
- Never store broker passwords, account passwords, API keys, or secrets in repo files.
- After editing `.mq5` or `.mqh`, compile and inspect the real compiler log.
- Do not claim success based only on command exit code.
- Do not run optimization before a deterministic single backtest passes.
- Use closed candles for pattern detection unless tick-level logic is explicitly required.
- Every technical detector must have a minimal test EA or script.
- Every renderer must be separable from the detector.

## Directory model

- `Include/TradeBlocks/Technicals`: pure signal detectors.
- `Include/TradeBlocks/Rendering`: chart object drawing only.
- `Include/TradeBlocks/Risk`: risk and sizing only.
- `Include/TradeBlocks/Position`: position lifecycle management only.
- `Include/TradeBlocks/Execution`: order send/modify/close only.
- `Experts/codex`: final EA orchestrators.
- `Scripts/codex`: isolated tests and diagnostics.

## Development loop

1. Produce a module contract.
2. Wait for approval or proceed only if the user requested implementation.
3. Implement one module.
4. Compile.
5. Read log.
6. Fix warnings and errors.
7. Add or update test harness.
8. Summarize changed files and behavioral impact.
