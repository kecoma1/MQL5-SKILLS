---
name: compile-mql5
description: Compile MQL5 code in a Linux environment using Wine and a portable MetaTrader 5 installation. Always analyze the compilation log.
---

# Compile MQL5 (Linux + Wine + Portable MT5)

## Environment

- MetaTrader 5 is installed in portable mode
- Base path:

C:\Program Files\MetaTrader 5\

- Do NOT use AppData or terminal-id paths
- All paths must be Windows-style

---

## Compilation Command

Use the local wrapper script:

```bash
mql5_compile.sh "<FILE_WIN>" "<LOG_WIN>"
````

---

## File Locations

All files must be created inside:

C:\Program Files\MetaTrader 5\MQL5\

Common subfolders:

* Experts\
* Indicators\
* Scripts\
* Include\
* logs\

---

## Workflow

1. Create or modify `.mq5` or `.mqh` files
2. Place them in the correct MQL5 directory
3. Compile using the wrapper script
4. Read the compilation log from:

$WINEPREFIX/drive_c/Program Files/MetaTrader 5/MQL5/Logs/

5. Extract:

   * Number of errors
   * Number of warnings
   * Error messages
   * File references

6. Fix issues and recompile

Repeat until:

0 errors, 0 warnings

---

## Important Rules

* Do NOT call MetaEditor directly
* Do NOT use wine commands manually
* Always use mql5_compile.sh
* Always verify compilation via log, not exit code

---

## Output Validation

After compilation:

* Confirm `.ex5` file exists
* Confirm log reports success

---
