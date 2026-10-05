---
name: podcast-edit
description: Montar un video largo horizontal tipo podcast en DaVinci Resolve a partir de dos grabaciones sincronizadas (camara de la persona y pantalla del ordenador) - recuadros con esquinas redondeadas sobre un fondo propio, entrada animada de la persona, overlays de nombre y de suscripcion con su sonido, render y revision. Use when the user asks to editar o montar un podcast, un video largo, un video con la persona y la pantalla, un picture-in-picture, o anadir los overlays de usuario y suscripcion a un video largo. Para conectar con Resolve y para shorts verticales usar edit-davinci; para subtitulos, captions-davinci.
---

# Podcast Edit

Montaje de videos largos horizontales en DaVinci Resolve con el MCP `davinci-resolve`. Esta skill solo cubre lo propio del formato; la conexion con Resolve, los ajustes de render y la revision con fotogramas estan en `edit-davinci` (`..\edit-davinci\SKILL.md`) y hay que seguirlos.

## Archivos De La Skill

| Archivo | Para que |
|---|---|
| [scripts/podcast_tools.py](scripts/podcast_tools.py) | Calcular recuadros y transformaciones, generar el marco de fondo y la entrada animada, comprobar overlays |
| [layouts/podcast-pip.json](layouts/podcast-pip.json) | Medidas del formato: recuadros, radio, entrada y segundos de los overlays |
| [agents/openai.yaml](agents/openai.yaml) | Ficha de la skill para Codex |

```powershell
python scripts\podcast_tools.py layout --person "<person>" --screen "<pantalla>"
python scripts\podcast_tools.py frame  --person "<person>" --screen "<pantalla>" --background "<fondo>" --out "<n>\background_frame.png"
python scripts\podcast_tools.py intro  --person "<person>" --screen "<pantalla>" --background "<fondo>" --render "<render de prueba>" --out "<n>\person_intro.mov"
python scripts\podcast_tools.py alpha  --video "<overlay>"
```

## Formatos

| Formato | Layout | Resultado |
|---|---|---|
| `podcast-pip` | [layouts/podcast-pip.json](layouts/podcast-pip.json) | 1920x1080. Persona en recuadro vertical a la izquierda, pantalla grande a la derecha, fondo propio |

Un formato nuevo es otro JSON en `layouts/` con las mismas claves, y una fila en esta tabla. Se elige con `--layout`. Si el formato necesita algo que el script no calcula, ampliar el script antes que hacerlo a mano.

## Que Hace Falta

En la carpeta del video (`<n>/`):

- El video de la persona (vertical) y el de la pantalla, grabados a la vez. Tienen que durar lo mismo y tener los mismos fps: comprobarlo con `edit_tools.py probe`. Si no coinciden, parar y preguntar como se sincronizan.
- La imagen de fondo.

Preguntar antes de montar solo lo que no este dicho: que pista de audio se usa (normalmente la de la pantalla, sin la de la persona), si va entero o con cortes, y en que segundos van los overlays (por defecto los del layout).

## 1. Proyecto

Conectar como indica `edit-davinci`. En el proyecto, antes de crear ningun timeline:

1. `timelineFrameRate` = fps de los videos.
2. `timelineResolutionWidth` 1920 y `timelineResolutionHeight` 1080.
3. `timelineInputResMismatchBehavior` = `scaleToFit`. Las transformaciones del script dan por hecho este ajuste.

## 2. Marco De Fondo

Las esquinas redondeadas no se hacen en Resolve: Fusion desde la API no se respeta al renderizar en la 21.0.4. Se hace con un marco: el fondo a 1920x1080 con dos huecos transparentes redondeados, colocado por encima de los dos videos.

`podcast_tools.py frame` genera el marco e imprime, para cada video, su recuadro y los valores `ZoomX`, `ZoomY`, `Pan` y `Tilt` de Resolve. Mover o cambiar de tamano un recuadro es cambiar el layout y regenerar el marco, nunca ajustar el clip a mano.

## 3. Timeline

Importar los dos videos, el marco y los overlays. Pistas, de abajo arriba:

| Pista | Contenido |
|---|---|
| V1 + A1 | Pantalla, con su audio |
| V2 | Persona, solo video |
| V3 | Marco de fondo, toda la duracion |
| V4 | Entrada animada (desde 0) y overlays |
| A2 | Sonido de los overlays |

1. `media_pool create_timeline_from_clips` con la pantalla entera.
2. `timeline add_track` hasta tener V4 y A2. `append_to_timeline` falla con "missing timeline item" si la pista no existe.
3. `media_pool append_to_timeline` con `clip_infos`, `track_index` y `media_type` (1 = solo video, 2 = solo audio). La persona, con `media_type: 1`: asi su audio no entra.
4. Marco en V3. Las imagenes fijas se cuentan a 24 fps, no a los del timeline: `end_frame` = fotogramas del video x 24 / fps. Con 60 fps, pasar el valor con decimales (49179 x 24 / 60 = 19671.6). Leer la duracion despues: puede quedar un fotograma mas largo que los videos, y entonces se renderiza con `MarkOut`.
5. `timeline_item set_property` con los valores del script, una propiedad por llamada, en la pantalla (V1) y en la persona (V2).

`Pan` no va en pixeles del timeline: se escala con el ancho que ocupa el clip ya ajustado. Un video vertical necesita un `Pan` de miles para moverse unos cientos de pixeles. Usar siempre los valores del script.

## 4. Render De Prueba

Antes de seguir, renderizar el primer segundo y mirar un fotograma. Con `SelectAllFrames` false, `MarkIn` y `MarkOut` van en fotogramas absolutos: el timeline empieza en 01:00:00:00, que a 60 fps es 216000.

Comprobar que los dos videos llenan sus huecos, sin franjas negras ni recuadros descolocados. Este render sirve ademas para el paso siguiente.

## 5. Entrada De La Persona

El recuadro entra desde la izquierda con fundido. No se hace con keyframes: al moverse el clip, el hueco del marco se quedaria quieto y no se veria deslizarse. Se hace con un clip corto con transparencia que tapa el hueco durante la entrada:

```powershell
python scripts\podcast_tools.py intro --person "<person>" --screen "<pantalla>" --background "<fondo>" --render "<render de prueba>" --out "<n>\person_intro.mov"
```

El script recorta a la persona del render de prueba, asi que al acabar la entrada la imagen coincide con la del timeline y no hay salto. Colocarlo en V4 desde el fotograma 0, con `media_type: 1`. Cambiar la duracion o la direccion es regenerarlo.

Si se regenera, usar otro nombre de archivo y sustituir el clip: Resolve puede tener abierto el anterior.

## 6. Overlays

Los overlays del usuario estan en `C:\Users\kecom\Videos\Assets` (`username` y `overlays`): uno con su nombre y otro de suscripcion. Comprobar cada archivo antes de usarlo:

```powershell
python scripts\podcast_tools.py alpha --video "<overlay>"
```

- **Transparencia.** Tiene que ser `.mov` ProRes 4444 con alfa. Un `.mp4` H.264 no guarda transparencia y taparia el video con su fondo negro.
- **Orientacion.** Para este formato, la version horizontal (1920x1080). La vertical es para shorts.
- **Audio.** Puede traer una pista en silencio. Si avisa de silencio, colocarlo solo como video.

Si existe la version horizontal con sonido, va tal cual en V4 y A2. Si solo la vertical tiene sonido, usar la imagen de la horizontal (`media_type: 1`) y el audio de la vertical (`media_type: 2`) en el mismo `record_frame`, y decirselo al usuario.

`record_frame` = segundo x fps (segundo 3 a 60 fps = 180).

Si el usuario tiene que exportar un overlay desde Premiere: formato QuickTime, ajuste `Apple ProRes 4444 con Alpha` (el de QuickTime, categoria Difusion; no los MXF ni los HLG o PQ), audio activado, sin ningun clip de fondo en la secuencia y la secuencia en 1920x1080 para la version horizontal.

## 7. Render Y Revision

Renderizar como indica `edit-davinci`, con `MarkIn` 216000 y `MarkOut` = 216000 + fotogramas del video - 1. El proyecto no se puede guardar mientras renderiza: guardar al acabar.

Revisar con `edit_tools.py review` y ademas:

- Fotogramas 0, 6, 12, 20 y el ultimo de la entrada, recortando la zona de la persona: se desliza, no asoma el contorno del hueco y no hay salto al terminar.
- Un fotograma dentro de cada overlay y otro entre los dos.
- Sonido de los overlays: comparar el audio con y sin ellos, o medir el nivel en sus tramos.
- El ultimo fotograma: que el marco llegue hasta el final.

`review` marca como congelados los tramos en los que la pantalla esta quieta. Antes de darlo por error, medir solo el recuadro de la persona con `crop` y `freezedetect`.

## 8. Informar

Decir que archivo es el bueno, que se ha comprobado, y lo que no: la sincronia entre la imagen de la persona y el audio de la pantalla no se puede verificar desde aqui, hay que pedirle al usuario que mire un tramo en el que hable. Avisar si un efecto de sonido llega casi a 0 dB frente a la voz.

## Estructura De Carpetas

```text
<n>/
  person.mp4
  ordenador.mp4
  background.png
  background_frame.png        marco generado
  person_intro.mov            entrada generada
  <nombre>_master.mp4         render de Resolve
```

Cada cambio que pida el usuario se renderiza con un nombre nuevo (`_v2_master`, `_v3_master`); no sobrescribir un master sin avisar.

## Reglas

- No ajustar recuadros a mano en Resolve: layout, script y regenerar.
- No dar por buena la transparencia ni el sonido de un overlay sin pasar `alpha`.
- Los renders de prueba van a `~\Movies` y se borran al terminar; los archivos generados que se usan en el timeline se quedan en la carpeta del video.
- Antes de una operacion que no este aqui, consultar `knowledge search` del MCP.
