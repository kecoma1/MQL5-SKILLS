# MQL5-SKILLS
A collection of reusable MQL5 skills for building, testing, and automating trading strategies.

## Repository Structure

```text
MQL5-SKILLS/
|-- LICENSE
|-- README.md
`-- skills/
    |-- candles-and-series/
    |   `-- SKILL.md
    |-- captions-davinci/
    |   |-- SKILL.md
    |   |-- style.json
    |   |-- agents/
    |   |   `-- openai.yaml
    |   |-- fonts/
    |   |   `-- README.md
    |   `-- scripts/
    |       `-- captions.py
    |-- compile-mql5/
    |   `-- SKILL.md
    |-- edit-davinci/
    |   |-- SKILL.md
    |   |-- agents/
    |   |   `-- openai.yaml
    |   `-- scripts/
    |       `-- edit_tools.py
    |-- expert-advisors/
    |   `-- SKILL.md
    |-- git/
    |   `-- SKILL.md
    |-- paint-objects/
    |   `-- SKILL.md
    `-- run-backtests/
        `-- SKILL.md
```

## Skills Overview

- `candles-and-series`: Conventions for loading and indexing candle data in MQL5, especially when using series mode and recent-candle-first logic.
- `captions-davinci`: Animated burned-in captions for vertical shorts from a word-level transcript, with the exact style stored in `style.json` so it can be reproduced identically.
- `compile-mql5`: Workflow for compiling MQL5 experts, indicators, and scripts with MetaEditor and checking the real compilation log.
- `edit-davinci`: Basic DaVinci Resolve editing through the MCP: connecting via the bridge, project setup, cutting clips into a timeline, rendering, and reviewing the render with extracted frames.
- `expert-advisors`: Conventions for structuring MQL5 expert advisors, especially grouped inputs and practical parameter comments.
- `git`: Git conventions for this repo, including branch naming, commit message format, and issue references.
- `paint-objects`: Rules for creating and updating chart objects in MQL5, including anchoring, repaint-safe updates, and redraw behavior.
- `run-backtests`: Guided workflow for configuring and launching MetaTrader 5 backtests with confirmed inputs and real result validation.
