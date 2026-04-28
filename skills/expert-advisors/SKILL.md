---
name: ea-orchestrator
description: Use when creating or editing the main .mq5 Expert Advisor file in this workspace. The EA acts purely as a central orchestrator. Follow local conventions for module importation, input grouping, dependency injection, and strict event routing. NEVER write raw trading or calculation logic in the main file.
---

# EA Orchestrator (Main .mq5)

Use this skill when building the main Expert Advisor file. The main EA is an orchestrator: it imports specialized modules (detectors, risk, position management), collects user inputs, and routes MetaTrader events to the appropriate classes. 

## 1. The Orchestrator Principle
- **No Business Logic:** The main `.mq5` file must NOT contain indicator calculations, risk math, or order execution logic. 
- **Delegation:** All complex operations must be delegated to instances of classes defined in `Include/TradeBlocks/`.

## 2. Imports and Instantiation
Include the necessary module headers at the top of the file and declare global instances or pointers for the modules that will manage the EA's lifecycle.

```mql5
#include <TradeBlocks/Detectors/FVGDetector.mqh>
#include <TradeBlocks/Risk/RiskManager.mqh>
#include <TradeBlocks/Execution/PositionManager.mqh>

CFVGDetector     g_detector;
CRiskManager     g_riskManager;
CPositionManager g_posManager;
```

## 3. Input Parameters Convention
Always declare EA inputs using a strict, readable pattern. Group them by the module they configure.

1. Group related parameters with `input group`.
2. Add an inline comment to every `input` (this serves as the label in the MT5 UI).
3. Use clear section names made of separators plus a title.

```mql5
input group ".......... Risk Settings"
input double InpRiskPercent = 1.0; // Risk per trade (%)
input double InpMaxDailyDD  = 5.0; // Max daily drawdown (%)

input group ".......... Strategy Settings"
input int    InpLookback    = 3;   // FVG Lookback period
```

## 4. Execution Routing (Event Handlers)
The MQL5 event handlers (`OnInit`, `OnTick`, `OnTradeTransaction`) must only route data to the respective modules.

### OnInit()
- Pass the input variables to the respective module initialization methods or constructors.
- Validate configuration and return `INIT_PARAMETERS_INCORRECT` if a module rejects the inputs.

### OnTick()
- **Pacing:** Gate non-critical logic behind a `IsNewBar()` check unless tick-level precision (e.g., trailing stops) is explicitly required by the `position-management` module.
- **Delegation Flow:**
  1. **State:** Update modules (e.g., `g_posManager.UpdateTick()`).
  2. **Detect:** Ask the technical detector for a signal intent.
  3. **Validate:** If an intent exists, ask the risk manager for authorization and sizing.
  4. **Execute:** Pass the authorized, sized intent to the position manager to execute.

```mql5
void OnTick() {
   // 1. Tick-level management (e.g., trailing stops)
   g_posManager.OnTick();

   // 2. Bar-level evaluation
   if(IsNewBar(_Symbol, _Period)) {
      TradeIntent intent = g_detector.CheckSignal();
      
      if(intent.isValid) {
         double lotSize = g_riskManager.CalculateLotSize(intent.stopLossPoints);
         if(lotSize > 0 && g_riskManager.IsTradeAllowed()) {
            g_posManager.ExecuteIntent(intent, lotSize);
         }
      }
   }
}
```

### OnTradeTransaction()
- Pass raw transaction data directly to the Position Manager and Risk Manager for internal state tracking (e.g., updating daily drawdown, win/loss streaks, or breakeven triggers).
- Do not write raw `if(trans.type == TRADE_TRANSACTION_DEAL_ADD)` logic in the main EA file.

```mql5
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result) {
   g_posManager.OnTradeTransaction(trans, request, result);
   g_riskManager.OnTradeTransaction(trans);
}
```

## 5. Universal Helpers
If small utility functions are strictly needed (like `IsNewBar()`), place them at the very end of the EA or, ideally, include them from a generic `Include/TradeBlocks/Utils/Helpers.mqh` file to keep the EA namespace uncluttered.
