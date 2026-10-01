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
    |-- compile-mql5/
    |   `-- SKILL.md
    |-- davinci-shorts/
    |   |-- SKILL.md
    |   |-- agents/
    |   |   `-- openai.yaml
    |   `-- scripts/
    |       `-- shorts_tools.py
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
- `davinci-shorts`: Workflow for cutting vertical shorts out of a long video with DaVinci Resolve, burning word-highlighted subtitles, and reviewing the render with extracted frames.
- `compile-mql5`: Workflow for compiling MQL5 experts, indicators, and scripts with MetaEditor and checking the real compilation log.
- `expert-advisors`: Conventions for structuring MQL5 expert advisors, especially grouped inputs and practical parameter comments.
- `git`: Git conventions for this repo, including branch naming, commit message format, and issue references.
- `paint-objects`: Rules for creating and updating chart objects in MQL5, including anchoring, repaint-safe updates, and redraw behavior.
- `run-backtests`: Guided workflow for configuring and launching MetaTrader 5 backtests with confirmed inputs and real result validation.
