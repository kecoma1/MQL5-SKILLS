---
name: davinci-shorts
description: Sacar shorts verticales (1080x1920) de un video largo con DaVinci Resolve y su transcripcion por palabras. Use when the user asks to proponer clips de un video, recortar un short o reel vertical, renderizarlo con DaVinci Resolve, generarle subtitulos quemados (caja clara con palabras que se oscurecen al decirse y palabras clave en grande), o revisar un render con fotogramas antes de entregarlo.
---

# DaVinci Shorts

Flujo para convertir un video horizontal de busto parlante en shorts verticales: proponer clips, cortar en Resolve, renderizar, subtitular y revisar con fotogramas.

Todo lo que no es Resolve lo hace `scripts/shorts_tools.py` (solo necesita Python 3 y ffmpeg/ffprobe en el PATH):

```powershell
python scripts\shorts_tools.py silence --help
python scripts\shorts_tools.py subs --help
python scripts\shorts_tools.py burn --help
python scripts\shorts_tools.py review --help
```

## Estructura De Carpetas

Cada video vive en su carpeta numerada dentro del workspace:

```text
<n>/
  <video>.mp4
  <video>-transcripcion.json     transcripcion por palabras (segments[].words[] con start, duration, text, eos)
  <video>.srt                    subtitulos del video completo, solo para leer
  subtitulos-correcciones.json   nombres propios mal transcritos y palabras que van en grande
  shorts/
    ShortNN_<tema>_master.mp4    render directo de Resolve
    ShortNN_<tema>.srt / .ass    subtitulos del short
    ShortNN_<tema>_subs.mp4      copia ligera con subtitulos quemados, la que se sube
```

Nombres de salida sin espacios ni acentos.

## 1. Proponer Clips

Antes de tocar Resolve, leer el `.srt` completo y proponer clips. No crear nada hasta que el usuario elija.

- Duracion entre 30 y 180 segundos, nunca mas.
- Cada clip empieza y acaba en frase completa y se entiende sin el resto del video.
- Presentarlos en una tabla: titulo, inicio -> fin, duracion y por que funciona, y recomendar por cual empezar.
- Decir tambien que tramos se descartan y por que.

## 2. Afinar Los Cortes

Los tiempos de la transcripcion son contiguos (una palabra acaba donde empieza la siguiente), asi que no dicen donde esta el silencio. Medirlo en el audio:

```powershell
python scripts\shorts_tools.py silence --video "<n>\<video>.mp4" --at 479.84 --fps 60
```

Usar el corte sugerido mas cercano para la entrada y para la salida. Si no hay silencio al final (el hablante enlaza frases), cortar en el punto mas bajo y avisar al usuario de que el final queda seco.

## 3. Preparar Resolve

Requisitos, comprobarlos antes de prometer nada:

- Resolve gratuito 21.0.x. En el gratuito 21.1+ el scripting Python es solo de Studio y el MCP no puede controlarlo.
- Un Python 3 de python.org registrado en Windows. El de Microsoft Store no lo ve Resolve: si en `Area de trabajo > Secuencias de comandos` solo aparece `resolve_bridge_canary`, falta ese Python. Instalarlo requiere permiso del usuario y reiniciar Resolve.
- Un proyecto abierto. En el Gestor de proyectos no hay barra de menus.
- El bridge en marcha: `Area de trabajo > Secuencias de comandos > resolve_bridge`. Lo lanza el usuario, una vez por sesion de Resolve (no por proyecto). No muestra ninguna ventana; comprobarlo con `resolve_control get_version`.

Ajustes del proyecto, en este orden y antes de crear ningun timeline:

1. `timelineFrameRate` = fps del video fuente (leerlo con ffprobe).
2. `timelineResolutionWidth` = 1080 y `timelineResolutionHeight` = 1920.
3. `timelineInputResMismatchBehavior` = `scaleToCrop`, para que el horizontal llene el vertical recortando los lados.

Despues importar el video con `media_storage import_to_pool` y crear el timeline con `media_pool create_timeline_from_clips` usando `clip_infos` con `start_frame` / `end_frame` en fotogramas del video fuente y `record_frame` 0. Leer el resultado con `project_manager snapshot` y confirmar duracion y que no hay huecos.

Antes de cortar, extraer dos o tres fotogramas del tramo en el video fuente y mirar el encuadre: el recorte vertical se queda con la franja central (el 31,6 % del ancho en un 16:9). Si el sujeto no esta centrado o hay rotulos que se cortan a medias, decirlo.

## 4. Renderizar

1. `render set_format_and_codec` con `mp4` y `H264`.
2. `render set_settings` en llamadas pequenas. Una llamada con muchas claves falla entera sin decir cual sobra:
   - `SelectAllFrames`, `TargetDir`, `CustomName`
   - `FormatWidth` 1080, `FormatHeight` 1920, `ExportVideo`, `ExportAudio`
3. `render add_job`, `render start`, y consultar `render get_job_status` hasta `CompletionPercentage` 100.

Limites conocidos por el bridge:

- `TargetDir` debe estar dentro de `allowed_output_roots` de `~/.config/davinci-resolve-mcp/bridge.json`. Renderizar ahi y mover el archivo a `<n>\shorts\` como `_master.mp4`.
- `VideoQuality` no se puede fijar: el render sale a unos 56 Mbps (unos 500 MB por 75 s). Es el master; la copia para subir se genera en el paso 6.
- `timelinePlaybackFrameRate` no se puede cambiar desde la API. Solo afecta a la reproduccion dentro de Resolve.
- Importar el `.srt` al panel multimedia funciona, pero `append_to_timeline` no lo coloca en la pista de subtitulos. Si el usuario los quiere en el timeline, que arrastre el `.srt` desde el panel.

## 5. Subtitulos

```powershell
python scripts\shorts_tools.py subs `
  --transcript "<n>\<video>-transcripcion.json" `
  --start 479.883 --end 555.2 `
  --corrections "<n>\subtitulos-correcciones.json" `
  --outdir "<n>\shorts" --name Short01_Claude_vs_Codex
```

`--start` y `--end` son los segundos del video original que corresponden a los fotogramas del corte.

Genera un `.srt` (con puntuacion, para subir a la plataforma o usar en Resolve) y un `.ass` para quemar.

### Estilo

Es el estilo que el usuario eligio a partir de un video de muestra. No cambiarlo por otro sin que lo pida.

- Caja clara `#ebe9ea` de esquinas bien redondeadas (radio del 30 % del alto, `--roundness`), ajustada al texto, centrada al 78,3 % de la altura.
- Texto en Poppins Bold `#252324`, sin borde ni sombra. Minusculas tal cual, sin puntos ni comas finales.
- Las palabras del grupo que aun no se han dicho salen en gris `#bfbdbe` y se oscurecen cuando se pronuncian con un fundido progresivo de 220 ms (`--word-fade`), nunca de golpe en un fotograma.
- Grupos de hasta 3 palabras o 18 caracteres, partidos en comas y finales de frase.
- Las palabras clave van solas y en grande (cuerpo 103 frente a 56, en px a 1080 de ancho). Una palabra corta suelta justo delante se une a ellas ("una locura").
- Cada caja entra con un fundido de 90 ms y una ligera ampliacion; sale por corte seco cuando entra la siguiente.

La fuente se lee de `fonts/Poppins-Bold.ttf` dentro de la skill (o `--font-file`). No esta en el repositorio: si falta, buscar `Poppins-Bold.ttf` en el equipo y copiarla ahi, o pedir permiso para descargarla.

### Correcciones Y Palabras Clave

Leer el `.srt` generado entero antes de quemar. La transcripcion falla en nombres propios y cifras: cada error nuevo se anade a `subtitulos-correcciones.json` y se regenera.

```json
{
  "replacements": [
    { "from": "cloud", "to": "Claude" },
    { "from": "GPT seis", "to": "GPT-6" },
    { "from": "por cinco", "to": "x5" }
  ],
  "emphasis": ["Codex", "infumable", "locura", "Opus 5.5", "90 £"]
}
```

`replacements` se compara por palabras, sin mayusculas ni puntuacion, y las frases largas ganan a las cortas. Sirve tambien para arreglar comas (`"20 casi más uso"` -> `"20, casi más uso"`), que es donde se parten los grupos.

`emphasis` son las palabras o frases de hasta 3 palabras que salen en grande, escritas como quedan despues de las correcciones. Elegir las que cargan el mensaje del clip (nombres de producto, cifras, el adjetivo fuerte), mas o menos una de cada cuatro o cinco cajas; si todo va en grande, nada destaca.

## 6. Quemar Y Generar La Copia Para Subir

```powershell
python scripts\shorts_tools.py burn `
  --video "<n>\shorts\Short01_Claude_vs_Codex_master.mp4" `
  --ass "<n>\shorts\Short01_Claude_vs_Codex.ass" `
  --out "<n>\shorts\Short01_Claude_vs_Codex_subs.mp4"
```

H.264 CRF 18 con tope de 14 Mbps, AAC 192 kbps y `faststart`. Unos 130 MB por 75 s a 60 fps.

## 7. Revisar Con Fotogramas

Obligatorio antes de decirle al usuario que esta listo. Nunca entregar un render sin haberlo mirado.

```powershell
python scripts\shorts_tools.py review `
  --video "<n>\shorts\Short01_Claude_vs_Codex_subs.mp4" `
  --outdir "<carpeta temporal>" --every 2.5 --at 21.0 48.6 --strip 26.3
```

Imprime resolucion, fps, duracion, peso, nivel de audio y fotogramas negros o congelados, y deja `sheet.jpg` (un fotograma cada `--every` segundos), `first.jpg`, `last.jpg`, los segundos pedidos con `--at` y, por cada `--strip`, 16 fotogramas seguidos de la zona de subtitulos para ver la animacion. Abrir las imagenes y comprobar:

- Resolucion 1080x1920 y la duracion esperada.
- Cara y microfono dentro del encuadre durante todo el clip.
- Primer y ultimo fotograma: que no empiece ni acabe a media palabra.
- Subtitulos legibles, sin tapar la boca y sin salirse por los lados. Pedir con `--at` los subtitulos mas largos del `.srt`.
- Con `--strip` en un cambio de caja: que la entrada funde y que las palabras pasan de gris a oscuro al decirse.
- Si el usuario da un video de referencia para el estilo, cortarlo en fotogramas cada 0,1 s, medir colores y tamanos sobre los fotogramas y comparar el resultado lado a lado.
- Nombres propios bien escritos.

Si algo falla, corregir y volver a revisar antes de avisar.

## 8. Informar

Decir que archivo es el que se sube, que se ha comprobado y que queda a decision del usuario (encuadre cerrado, final seco, estilo de subtitulos). Guardar el proyecto con `project_manager save`.

## Reglas

- No crear proyectos, timelines ni renders hasta que el usuario haya elegido clip.
- No instalar ni descargar nada sin permiso explicito.
- No sobrescribir un `_master.mp4` sin avisar: volver a renderizar tarda y pesa.
- Si el MCP no conecta, leer el campo `remediation` del error antes de proponer otra via. ffmpeg solo como alternativa para el corte si el usuario lo acepta.
- Los fotogramas de revision van a una carpeta temporal, no a la carpeta del video.
