---
name: edit-davinci
description: Lanzar, preparar y manejar DaVinci Resolve desde el MCP para edicion basica - conectar con el bridge, crear y configurar el proyecto, importar video, recortar clips en un timeline (horizontal o vertical 1080x1920), renderizar y revisar el resultado con fotogramas. Use when the user asks to abrir o conectar DaVinci Resolve, crear un proyecto o timeline, proponer o recortar clips o shorts de un video, renderizar o exportar con Resolve, o revisar un render antes de entregarlo. Para subtitulos usar captions-davinci.
---

# Edit DaVinci

Edicion basica con DaVinci Resolve controlado por el MCP `davinci-resolve`: conectar, preparar el proyecto, cortar, renderizar y revisar.

Lo que la API de Resolve no da lo cubre `scripts/edit_tools.py` (Python 3 y ffmpeg/ffprobe en el PATH):

```powershell
python scripts\edit_tools.py probe   --video "<video>"
python scripts\edit_tools.py silence --video "<video>" --at 479.84
python scripts\edit_tools.py frames  --video "<video>" --outdir "<temp>" --at 481 510
python scripts\edit_tools.py encode  --video "<master>" --out "<copia para subir>"
python scripts\edit_tools.py review  --video "<render>" --outdir "<temp>" --every 2.5
```

## 1. Conectar Con Resolve

Comprobar siempre primero con `resolve_control get_version`. Si responde, saltar al paso 2.

Si devuelve `SCRIPTING_UNAVAILABLE`, el Resolve gratuito no acepta scripting externo y hay que pasar por el bridge interno. Recorrer en orden:

1. **Version.** Tiene que ser el gratuito 21.0.x (o Studio). En el gratuito 21.1+ el scripting Python es solo de Studio y el MCP no puede controlarlo: no proponer actualizar.
2. **Resolve abierto.** `resolve_control runtime_mode` dice si esta en marcha; `resolve_control launch` lo arranca. En el gratuito, `launch` abre la aplicacion pero devuelve error de scripting: es lo esperado.
3. **Proyecto abierto.** En el Gestor de proyectos no hay barra de menus. El usuario crea o abre un proyecto cualquiera.
4. **Bridge en marcha.** Lo lanza el usuario, una vez por sesion de Resolve (no por proyecto): `Area de trabajo > Secuencias de comandos > resolve_bridge` (en ingles, `Workspace > Scripts`). No muestra ninguna ventana y se queda "ocupado"; es normal. Volver a probar `get_version`.

Si en ese menu solo aparece `resolve_bridge_canary`, Resolve lista los scripts Lua y se salta los de Python porque no encuentra un Python 3. El de Microsoft Store no le vale: hace falta el de python.org, que se registra en `HKCU\Software\Python\PythonCore`.

```powershell
winget install --id Python.Python.3.10 -e --source winget --scope user
```

Es una descarga: pedir permiso antes. Despues el usuario cierra Resolve del todo, lo reabre y lanza el bridge.

Si los scripts no estan en `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility`, instalarlos con `python scripts/install_resolve_bridge.py` desde la carpeta del MCP.

## 2. Preparar El Proyecto

Leer las propiedades del video con `edit_tools.py probe` y fijar los ajustes con `project_settings set_setting`, en este orden y antes de crear ningun timeline (despues la cadencia ya no se puede cambiar):

1. `timelineFrameRate` = fps del video fuente.
2. `timelineResolutionWidth` y `timelineResolutionHeight`: 1080 y 1920 para vertical, o los del video para horizontal.
3. Solo en vertical: `timelineInputResMismatchBehavior` = `scaleToCrop`, para que el horizontal llene el encuadre recortando los lados.

Importar el video con `media_storage import_to_pool` (rutas absolutas) y leer su id con `project_settings project_summary` (`include_clips: true`).

Confirmar con `project_manager snapshot` y guardar con `project_manager save`.

`timelinePlaybackFrameRate` no se puede cambiar desde la API. Solo afecta a la reproduccion dentro de Resolve, no al render; el usuario lo cambia en Ajustes del proyecto > Master Settings.

## 3. Elegir Y Afinar Los Cortes

Si el usuario pide clips de un video largo, leer su transcripcion entera y proponerlos antes de tocar Resolve. No crear nada hasta que elija.

- Para shorts: entre 30 y 180 segundos, nunca mas.
- Cada clip empieza y acaba en frase completa y se entiende sin el resto del video.
- Presentarlos en una tabla (titulo, inicio -> fin, duracion, por que funciona), recomendar por cual empezar y decir que tramos se descartan y por que.

Los tiempos de una transcripcion por palabras son contiguos (una palabra acaba donde empieza la siguiente), asi que no dicen donde esta el silencio. Medirlo en el audio:

```powershell
python scripts\edit_tools.py silence --video "<video>" --at 479.84
```

Usar el corte sugerido mas cercano para la entrada y para la salida; la salida ya viene en fotogramas del video. Si no hay silencio al final (el hablante enlaza frases), cortar en el punto mas bajo y avisar de que el final queda seco.

Para vertical, mirar antes el encuadre con `edit_tools.py frames` en dos o tres segundos del tramo: el recorte se queda con la franja central (el 31,6 % del ancho de un 16:9). Si el sujeto no esta centrado o hay rotulos que se cortan a medias, decirlo.

## 4. Montar El Timeline

`media_pool create_timeline_from_clips` con `clip_infos`:

```json
{
  "name": "Short 01 - Claude vs Codex",
  "clip_infos": [
    { "clip_id": "<id>", "start_frame": 28793, "end_frame": 33312, "record_frame": 0 }
  ],
  "if_exists": "fail"
}
```

`start_frame` y `end_frame` son fotogramas del video fuente; `record_frame` es la posicion en el timeline. Varios tramos seguidos: una entrada por tramo, con `record_frame` igual a la suma de las duraciones anteriores.

Leer el resultado con `project_manager snapshot` (`include: ["timeline", "gaps_overlaps"]`): duracion esperada y cero huecos.

## 5. Renderizar

1. `render set_format_and_codec` con `mp4` y `H264`.
2. `render set_settings` en llamadas pequenas. Una llamada con muchas claves falla entera sin decir cual sobra:
   - `SelectAllFrames`, `TargetDir`, `CustomName`
   - `FormatWidth`, `FormatHeight`, `ExportVideo`, `ExportAudio`
3. `render add_job`, `render start` con ese `job_id`, y `render get_job_status` hasta `CompletionPercentage` 100.

Limites conocidos por el bridge:

- `TargetDir` debe estar dentro de `allowed_output_roots` de `~/.config/davinci-resolve-mcp/bridge.json` (por defecto `~\Movies`; crearla si no existe). Renderizar ahi y mover el archivo a su carpeta como `_master.mp4`.
- `VideoQuality` no se puede fijar: sale a unos 56 Mbps (unos 500 MB por 75 s a 1080x1920 y 60 fps). Ese es el master. La copia para subir se saca con `edit_tools.py encode` (H.264 CRF 18, tope 14 Mbps) o, si lleva subtitulos, con la skill `captions-davinci`.
- Importar un `.srt` al panel multimedia funciona, pero `append_to_timeline` no lo coloca en la pista de subtitulos. Si el usuario lo quiere en el timeline, que lo arrastre desde el panel.

## 6. Revisar Con Fotogramas

Obligatorio antes de decirle al usuario que esta listo. Nunca entregar un render sin haberlo mirado.

```powershell
python scripts\edit_tools.py review --video "<render>" --outdir "<temp>" --every 2.5 --at 21.0 48.6
```

Imprime resolucion, fps, duracion, peso, nivel de audio y fotogramas negros o congelados, y deja `sheet.jpg` (un fotograma cada `--every` segundos), `first.jpg`, `last.jpg`, los segundos pedidos con `--at` y, por cada `--strip`, 16 fotogramas seguidos de la franja de subtitulos. Abrir las imagenes y comprobar:

- Resolucion y duracion esperadas.
- El sujeto dentro del encuadre durante todo el clip.
- Primer y ultimo fotograma: que no empiece ni acabe a media palabra.

Si algo falla, corregir y volver a revisar antes de avisar. Los fotogramas van a una carpeta temporal, no a la del video.

## 7. Informar

Decir que archivo es el que se sube, que se ha comprobado y que queda a decision del usuario (encuadre cerrado, final seco). Guardar el proyecto con `project_manager save`.

## Estructura De Carpetas

```text
<n>/
  <video>.mp4
  <video>-transcripcion.json     transcripcion por palabras
  <video>.srt                    subtitulos del video completo, solo para leer
  shorts/
    ShortNN_<tema>_master.mp4    render directo de Resolve
    ShortNN_<tema>_subs.mp4      copia ligera con subtitulos (captions-davinci)
```

Nombres de salida sin espacios ni acentos.

## Reglas

- No crear proyectos, timelines ni renders hasta que el usuario haya elegido que quiere.
- No instalar ni descargar nada sin permiso explicito.
- No sobrescribir un `_master.mp4` sin avisar: volver a renderizar tarda y pesa.
- Si el MCP falla, leer el campo `remediation` del error antes de proponer otra via. ffmpeg como sustituto del corte solo si el usuario lo acepta.
- Antes de una operacion que no este aqui, consultar `knowledge search` del MCP: recoge limites y trampas de la API.
