---
name: captions-davinci
description: Generar y quemar subtitulos animados en un short vertical a partir de la transcripcion por palabras, con el estilo fijo del usuario guardado en style.json - caja clara redondeada, Poppins Bold, palabras que pasan de gris a oscuro al decirse y palabras clave en grande. Use when the user asks for subtitulos, captions, o texto en pantalla para un short o clip, cambiar el estilo de los subtitulos, corregir palabras mal transcritas, o elegir que palabras destacan.
---

# Captions DaVinci

Subtitulos quemados para shorts. El aspecto entero vive en `style.json`: con ese archivo, la fuente de `fonts/` y la misma transcripcion, `scripts/captions.py` genera siempre el mismo resultado.

Necesita Python 3 y ffmpeg en el PATH. El video de entrada es el master que sale de Resolve (skill `edit-davinci`).

## Archivos De La Skill

Todo lo necesario esta dentro de esta carpeta; las rutas son relativas a ella.

| Archivo | Para que |
|---|---|
| [scripts/captions.py](scripts/captions.py) | Genera el `.srt` y el `.ass` (`build`) y los quema en el video (`burn`) |
| [style.json](style.json) | La configuracion exacta del estilo. El script no lleva ningun valor de estilo dentro |
| [fonts/Poppins-Bold.ttf](fonts/Poppins-Bold.ttf) | La fuente. La leen el script, para medir cada caja, y ffmpeg, para dibujar el texto |
| [fonts/OFL.txt](fonts/OFL.txt) | Licencia de la fuente; va siempre con ella |
| [fonts/README.md](fonts/README.md) | Version de la fuente y por que no hay que cambiarla |
| [examples/clip-config.json](examples/clip-config.json) | Ejemplo real de config de un video: correcciones y palabras en grande |
| [agents/openai.yaml](agents/openai.yaml) | Ficha de la skill para Codex |

## Flujo

1. Generar los subtitulos del tramo:

```powershell
python scripts\captions.py build `
  --transcript "<n>\<video>-transcripcion.json" `
  --start 479.883 --end 555.2 `
  --clip-config "<n>\subtitulos-correcciones.json" `
  --outdir "<n>\shorts" --name Short01_Claude_vs_Codex
```

`--start` y `--end` son los segundos del video original donde empieza y acaba el corte (fotograma / fps). La transcripcion es un JSON con `segments[].words[]`, cada palabra con `start`, `duration`, `text` y `eos`.

Salen dos archivos: `.srt` con puntuacion (para subir a la plataforma o arrastrar a Resolve) y `.ass` para quemar.

2. Leer el `.srt` entero. Corregir en el JSON del video lo que este mal transcrito y decidir que va en grande (ver abajo). Regenerar.

3. Quemar sobre el master:

```powershell
python scripts\captions.py burn `
  --video "<n>\shorts\Short01_Claude_vs_Codex_master.mp4" `
  --ass "<n>\shorts\Short01_Claude_vs_Codex.ass" `
  --out "<n>\shorts\Short01_Claude_vs_Codex_subs.mp4"
```

El resultado es ya la copia para subir: H.264 CRF 18 con tope de 14 Mbps, AAC 192 kbps y `faststart`.

4. Revisar con fotogramas antes de avisar, con `edit_tools.py review` de la skill `edit-davinci`:

```powershell
python ..\edit-davinci\scripts\edit_tools.py review --video "<..._subs.mp4>" --outdir "<temp>" --every 2.5 --at 21.0 --strip 26.45
```

- Las cajas no tapan la boca ni se salen por los lados. Pedir con `--at` los subtitulos mas largos del `.srt`.
- Nombres propios y cifras bien escritos.
- Con `--strip` en un cambio de caja: la caja entra con fundido y las palabras se oscurecen progresivamente, no de golpe.

## Config Del Video

Un JSON por video, junto a el (`<n>\subtitulos-correcciones.json`). No es estilo: es lo propio de ese contenido. Para un video nuevo, partir de [examples/clip-config.json](examples/clip-config.json): sus correcciones de nombres (Claude, Codex, GPT-6...) valen para cualquier video del canal; la lista `emphasis` hay que rehacerla para cada clip.

```json
{
  "replacements": [
    { "from": "cloud", "to": "Claude" },
    { "from": "GPT seis", "to": "GPT-6" },
    { "from": "por cinco", "to": "x5" },
    { "from": "20 casi más uso", "to": "20, casi más uso" }
  ],
  "emphasis": ["Codex", "infumable", "locura", "Opus 5.5", "90 £"]
}
```

`replacements` arregla la transcripcion. Se compara por palabras, sin mayusculas ni puntuacion, y las frases largas ganan a las cortas. La puntuacion de la palabra original se conserva. Sirve tambien para mover comas, que es donde se parten las cajas.

`emphasis` son las palabras o frases de hasta 3 palabras que salen solas y en grande, escritas como quedan despues de las correcciones. Elegir las que cargan el mensaje del clip (nombres de producto, cifras, el adjetivo fuerte), mas o menos una de cada cuatro o cinco cajas: si todo va en grande, nada destaca.

## El Estilo

Lo eligio el usuario a partir de un video de muestra y lo afino despues. No cambiarlo salvo que lo pida; cuando lo pida, editar `style.json`, no el script.

| Clave | Valor | Que es |
|---|---|---|
| `font_file` | `fonts/Poppins-Bold.ttf` | Fuente, relativa a `style.json` |
| `reference_width` | 1080 | Ancho para el que estan dadas las medidas en px; se escalan al ancho real |
| `position_y` | 0.783 | Altura del centro de la caja (0 arriba, 1 abajo) |
| `colors.box` | `#ebe9ea` | Fondo de la caja |
| `colors.text` | `#252324` | Palabra ya dicha |
| `colors.pending` | `#bfbdbe` | Palabra aun no dicha |
| `text.size` | 56 | Cuerpo normal, en px |
| `text.emphasis_size` | 103 | Cuerpo de las palabras clave |
| `text.strip_trailing` | `.,;:` | Puntuacion final que no se muestra |
| `box.height_em` | 1.65 | Alto de la caja respecto al cuerpo |
| `box.padding_x` + `box.padding_x_em` | 30 px + 0.06 em | Margen lateral |
| `box.roundness` | 0.3 | Radio de las esquinas respecto al alto (0.5 = pastilla) |
| `box.baseline` | 0.675 | Donde cae la linea base dentro de la caja |
| `box.max_width` | 0.9 | Ancho maximo respecto al video; si no cabe, el texto se encoge |
| `animation.box_fade_ms` | 90 | Fundido de entrada de cada caja |
| `animation.box_scale_from` | 94 | Escala (%) desde la que crece al entrar |
| `animation.word_fade_ms` | 220 | Lo que tarda una palabra en pasar de gris a oscuro |
| `animation.word_fade_min_ms` | 60 | Minimo, cuando la caja se va antes |
| `animation.hold_s` | 0.6 | Cuanto aguanta la caja tras su ultima palabra si no entra otra |
| `grouping.max_chars` / `max_words` | 18 / 3 | Tamano maximo de un grupo |
| `grouping.max_gap_s` | 0.5 | Pausa que parte el grupo |
| `grouping.tail_extra_chars` | 6 | Margen para que la palabra que cierra frase no quede sola |
| `grouping.merge_short_word_chars` | 4 | Palabra corta suelta que se une a la clave siguiente ("una locura") |
| `grouping.emphasis_max_words` | 3 | Largo maximo de una frase de `emphasis` |
| `grouping.min_word_inside` | 0.6 | Parte de una palabra que debe caer dentro del corte para incluirla |
| `burn.*` | slow, CRF 18, 14M, 28M, 192k | Codificacion de la copia final |

Comportamiento que no esta en el JSON porque es la definicion del estilo:

- Una caja por grupo, ajustada al texto, sin borde ni sombra. Sale por corte seco cuando entra la siguiente.
- La primera palabra del grupo aparece ya oscura; las demas en gris hasta que se pronuncian.
- Los grupos se parten en comas, finales de frase y pausas.
- Minusculas y mayusculas tal cual vienen de la transcripcion corregida.

Para probar una variante sin tocar el estilo guardado, copiar `style.json`, editar la copia y pasarla con `--style`.

## La Fuente

[fonts/Poppins-Bold.ttf](fonts/Poppins-Bold.ttf) (Poppins Bold 4.004) va dentro de la skill junto a su licencia [fonts/OFL.txt](fonts/OFL.txt); no hace falta instalarla en el sistema. El script la lee para medir cada caja y ffmpeg la carga desde esa carpeta para dibujar el texto. Si falta, el script lo dice y no genera nada. Con otra fuente u otra version las cajas cambian de tamano y deja de ser el mismo estilo.

## Copiar Un Estilo De Un Video De Muestra

Cuando el usuario da un video de referencia:

1. Cortarlo en fotogramas cada 0,1 s y montarlos en hojas de 6x2 para ver la secuencia entera.
2. Sacar tiras a 60 fps de un cambio de caja y de un cambio de palabra para ver las animaciones.
3. Medir sobre los fotogramas, no a ojo: color de fondo y de texto, alto de la caja, margenes, posicion vertical.
4. Quemar una prueba de 15 s y comparar lado a lado antes de procesar el clip entero.

## Reglas

- No cambiar `style.json` sin que el usuario lo pida. Los ajustes de un video concreto van en su JSON, no en el estilo.
- No sobrescribir el `_master.mp4`: `burn` siempre escribe en otro archivo.
- No entregar sin revisar fotogramas.
- Al actualizar esta skill, mantener iguales la copia del workspace y la del repositorio de skills.
