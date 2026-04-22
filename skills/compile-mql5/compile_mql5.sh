#!/bin/bash

## export WINEPREFIX=/home/$USER/.mt5 ## Adjust this according to your desired WINEPREFIX.

FILE_WIN="$1"
LOG_WIN="$2"

BAT_LINUX="$WINEPREFIX/drive_c/compile_mql5.bat"

cat > "$BAT_LINUX" <<EOF
"C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"$FILE_WIN" /log:"$LOG_WIN"
EOF

wine cmd /c C:\\compile_mql5.bat
