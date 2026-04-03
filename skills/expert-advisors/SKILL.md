---
name: expert-advisors
description: Use when creating or editing MQL5 expert advisors in this workspace. Follow the local conventions for EA structure, includes, classes, chart objects, and parameter declarations.
---

# Expert Advisors

Use this skill when working on `.mq5` expert advisors or related `.mqh` files for this repository.

## Inputs

Always declare EA inputs using this pattern:

1. Group related parameters with `input group`.
2. Add an inline comment to every `input`.
3. Keep comments short and practical.
4. Use clear section names made of separators plus a title, for example:

```mq5
input group ".......... Data"
input int InpCandlesToLoad = 1000;       // Number of candles to load

input group ".......... Drawing"
input int InpPaintDurationMinutes = 120; // Line duration in minutes
input color InpFVGColor = clrDodgerBlue; // FVG color
```

Do not leave `input` declarations without group or comment unless the user explicitly asks for a different style.
