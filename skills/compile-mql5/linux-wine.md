# Adaptando la skill para utilizarla con wine en una installation en Linux de MT5.

Probando el sistema en Linux, creamos una re-versión de esta skill que se adapta a trabajar en este contexto, que es distinto de una instalación estándar de MT5 en Windows.

### MetaEditor por medio de Wine.
Cuando utilizamos `wine`, si queremos interactuar con el `MetaEditor64.exe` por CLI para ordenarle la compilación y logs de nuestros archivos de código generados, lo vamos a hacer por medio de comandos `wine cmd`.

`wine cmd` nos permite acceder a la wine command prompt desde la misma shell en donde estemos trabajando. Es una manera de hacer puente hacia el método original, donde el agente va pasando comandos al editor por vía `cmd.exe`. `wine cmd` cambia nuestra shell a una más Windows-like, donde podamos introducir comandos iguales a los que utiliza el método original estando en Windows.

Habiendo resuelto la manera de usar estos comandos en Linux, apareció la tarea de resolver problemas de sintáxis en esos comandos, ya que ambas shell se redactan de maneras ligeramente diferentes. La solución fue encapsularlo todo en un bash-script. El mismo a continuación, y su explicación debajo:
```Bash
#!/bin/bash

## export WINEPREFIX=/home/$USER/.mt5 ## Cambiar ruta por el WINEPREFIX correspondiente.

FILE_WIN="$1"
LOG_WIN="$2"

BAT_LINUX="$WINEPREFIX/drive_c/compile_mql5.bat"

cat > "$BAT_LINUX" <<EOF
"C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"$FILE_WIN" /log:"$LOG_WIN"
EOF

wine cmd /c C:\\compile_mql5.bat > /dev/null 2>&1
```
- Establece $FILE_WIN y $LOG_WIN como variables de entorno $1 y $2. Estos dos últimos van a ser los argumentos que escribamos junto al script al momento de ejecución (se muestra el ejemplo más adelante).
- Establece la variable $BAT_LINUX. Es un archivo `.bat` que va a ir alojado dentro del `drive_c` en nuestro entorno wine, para ejecutarlo con `wine cmd`.
- Componemos el contenido de este batchfile para windows. Acá es donde introducimos la ruta de ejecución de nuestro MetaEditor en formato `cmd/windows-shell`, y los comandos → `/compile:"$FILE_WIN" `, y `/log:"$LOG_WIN"`.
- `wine cmd /c`, es decir abriremos el intérprete de comandos de Windows dentro de wine y le pasaremos la opción `"/c"` que le va a decir a cmd que ejecute el comando y luego termine; `C:\\compile_mql5.bat > /dev/null 2>&1`. cmd va a buscar el batchfile que creamos unas líneas arriba, y ejecutará todo sin devolver más output en nuestra terminal.
- Finalmente lo ejecutamos: `./mql5_compile.sh \
"C:\Program Files\MetaTrader 5\MQL5\Indicators\test_simple.mq5" \
"C:\Program Files\MetaTrader 5\MQL5\Logs\test_simple.log"` (asegúrate de que tenga permiso de ejecución, `chmod +x mql5_compile.sh`).

### Sobre /dev/null 2>&1

Se opta por no dejar output en terminal, `>/dev/null 2>&1`, ya que wine en caso contrario iría llenando nuestra terminal de output con su trabajo, el cual en un contexto de CLI agents puede gastar tokens innecesarios; si todo funciona correctamente, no necesitamos leer outputs. Esto sólo sirve si hay que debuggear algo, en cuyo caso podríamos por ejemplo reemplazar la línea por algo como lo siguiente:
```Bash
wine cmd /c C:\\compile_mql5.bat > /tmp/wine_output.log 2>&1
```
Volcando todo el output de funcionamiento de Wine dentro de otro archivo de log a interpretar por separado si aparecieran errores. La skill prioriza ser eficientes y gastar menos tokens en lugar de esto.

### Explicando el `compile_mql5.bat`

El crear un batchfile fue necesario para que `wine cmd` siguiera nuestro comando sin presentarse errores de sintáxis en el output. Básicamente cuando al principio intentábamos escribir todo el comando bajo la misma shell de linux, no podíamos progresar, porque la linux-shell no recibía correctamente la parte de los comandos que venía en formato windows/cmd. Había que trabajar con los escapados, y la totalidad del proceso se convirtió en una búsqueda intensa y complicada por ejecutar sin errores. El archivo batch se crea para que `wine cmd` lo abra y lo interprete una vez que este último esté abierto. Este es el "paso adicional" que incorporamos para que el framework original funcione con Linux. Primero estamos en una linux shell, luego con `wine cmd` pasamos a una windows shell en wine, y dentro de la misma podemos abrir el batchfile que contiene pura sintáxis estilo windows.

Al final, nuestra arquitectura luce como lo siguiente:
```Agente CLI
→ crea/edita .mq5/.mqh
→ llama a mql5_compile.sh
→ script genera .bat
→ wine cmd ejecuta MetaEditor
→ genera .log + .ex5
→ agente lee log
```

En resumen:
1. Usamos `wine cmd /c` para evitar unificar las sintáxis de cmd shell en windows con bash en linux, de esta manera nos ahorramos problemas de ejecución.
2. Bajo wine en linux, metatrader va a alojarse (al menos [en el ejemplo en que se probó](https://github.com/n-cash/mt5arch.sh)) en la ruta de instalación portable, todo bajo el mismo "C:\Program Files\MetaTrader 5\MQL5\*", y ya no tenemos "C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\*". Esto dificultará por el momento trabajar con múltiples terminales bajo el mismo $WINEPREFIX, pero supongo que hay múltiples maneras de resolverlo según cada caso.
