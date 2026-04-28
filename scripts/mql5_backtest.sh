#!/bin/bash

# export WINEPREFIX=/home/$USER/.mt5 ## Adjust accordingly

INI_WIN="$1"
BAT_LINUX="$WINEPREFIX/drive_c/run_backtest.bat"

cat > "$BAT_LINUX" <<EOF
"C:\Program Files\MetaTrader 5\terminal64.exe" /config:"$INI_WIN"
EOF

wine cmd /c C:\\run_backtest.bat > /dev/null 2>&1
