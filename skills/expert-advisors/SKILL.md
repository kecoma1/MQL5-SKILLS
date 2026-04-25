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
input group ".......... EA Settings"
input int InpMagicNumber = 7777;       // Magic number

input group ".......... Risk Settings"
input double InpRiskPercent = 1.0; // Risk per trade (%)
input int InpMaxDailyTrades = 3; // Max amount of trades per day
```

Do not leave `input` declarations without group or comment unless the user explicitly asks for a different style.

---

## Universal Helper: IsNewBar()

```mql5
bool IsNewBar(ENUM_TIMEFRAMES tf = PERIOD_CURRENT) {
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, tf, 0);
   if(currentBarTime != lastBarTime) {
      lastBarTime = currentBarTime;
      return true;
   }
   return false;
}
```

Always gate OnTick() logic behind IsNewBar() unless you need tick-level precision (scalping).

---

## The CRiskManager Class (Complete Implementation)

```mql5
class CRiskManager : public IModule {
private:
   double   m_riskPercent;       // Risk per trade
   double   m_maxDailyDD;        // Max daily drawdown %
   double   m_maxTotalDD;        // Max total drawdown %
   double   m_dayStartBalance;   // Balance at session start
   double   m_peakBalance;       // Highest ever balance (for total DD)
   bool     m_haltTrading;       // Kill switch
   bool     m_reducedMode;       // Reduced lot mode (6% DD warning)
   int      m_consecutiveLosses; // Track losing streak
   datetime m_lastDayReset;      // Track daily reset

public:
   CRiskManager(double riskPct, double maxDailyDD, double maxTotalDD) {
      m_riskPercent        = riskPct;
      m_maxDailyDD         = maxDailyDD;
      m_maxTotalDD         = maxTotalDD;
      m_dayStartBalance    = AccountInfoDouble(ACCOUNT_BALANCE);
      m_peakBalance        = m_dayStartBalance;
      m_haltTrading        = false;
      m_reducedMode        = false;
      m_consecutiveLosses  = 0;
      m_lastDayReset       = TimeCurrent();
   }

   //--- Daily reset at midnight ---
   void DailyReset() {
      MqlDateTime now;
      TimeToStruct(TimeCurrent(), now);
      MqlDateTime last;
      TimeToStruct(m_lastDayReset, last);

      if(now.day != last.day) {
         m_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
         m_haltTrading     = false;  // Unlock new trading day
         m_reducedMode     = false;
         m_lastDayReset    = TimeCurrent();
         Print("RiskManager: Daily reset. New balance: ", m_dayStartBalance);
      }
   }

   //--- Is trading allowed right now? ---
   bool IsTradeAllowed() {
      DailyReset();
      if(m_haltTrading) return false;

      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

      // Update peak
      if(balance > m_peakBalance) m_peakBalance = balance;

      // Daily drawdown check
      double dailyDD = (m_dayStartBalance - equity) / m_dayStartBalance * 100.0;
      if(dailyDD >= m_maxDailyDD) {
         m_haltTrading = true;
         Alert("RISK: Daily DD limit hit! EA halted for today. DD=", dailyDD, "%");
         return false;
      }

      // Total drawdown check
      double totalDD = (m_peakBalance - equity) / m_peakBalance * 100.0;
      if(totalDD >= m_maxTotalDD) {
         m_haltTrading = true;
         Alert("RISK: Total DD limit hit! EA permanently halted. DD=", totalDD, "%");
         return false;
      }

      // Warning zone — reduce lots
      m_reducedMode = (totalDD >= m_maxTotalDD * 0.7); // 70% of max DD
      return true;
   }

   //--- Calculate lot size ---
   double CalculateLotSize(double slDistancePoints) {
      if(slDistancePoints <= 0) return 0;

      double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskPct  = m_reducedMode ? m_riskPercent * 0.5 : m_riskPercent;
      double riskAmt  = balance * riskPct / 100.0;

      double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double lotStep  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double minLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

      double lotSize = riskAmt / (slDistancePoints * tickVal / tickSize);
      lotSize = MathFloor(lotSize / lotStep) * lotStep;
      lotSize = MathMax(minLot, MathMin(maxLot, lotSize));

      return lotSize;
   }

   //--- Consecutive loss tracker ---
   void RecordTradeResult(bool isWin) {
      if(isWin) {
         m_consecutiveLosses = 0;
      } else {
         m_consecutiveLosses++;
         if(m_consecutiveLosses >= 3) {
            m_reducedMode = true;  // Enter reduced mode after 3 losses
            Print("RISK: 3 consecutive losses. Entering reduced mode.");
         }
      }
   }

   bool   IsReady()    { return true; }
   void   Reset()      { DailyReset(); }
   bool   IsHalted()   { return m_haltTrading; }
   bool   IsReduced()  { return m_reducedMode; }
   string GetStatus()  {
      return StringFormat("Risk: %.1f%% | DailyDD: %.2f%% | TotalDD: %.2f%% | Halt: %s",
         m_riskPercent,
         (m_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / m_dayStartBalance * 100,
         (m_peakBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / m_peakBalance * 100,
         m_haltTrading ? "YES" : "NO");
   }
};
```

---
