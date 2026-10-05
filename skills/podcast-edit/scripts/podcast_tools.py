"""Herramientas para montar un podcast en formato picture-in-picture con DaVinci Resolve.

Lo que la API de Resolve no da: el calculo de recuadros y transformaciones, el marco de
fondo con huecos redondeados y el clip de entrada animada de la persona.

  python podcast_tools.py layout --person <video> --screen <video>
  python podcast_tools.py frame  --person <video> --screen <video> --background <png> --out <png>
  python podcast_tools.py intro  --person <video> --screen <video> --background <png> --render <mp4> --out <mov>
  python podcast_tools.py alpha  --video <overlay>

Necesita Python 3 y ffmpeg/ffprobe en el PATH.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_LAYOUT = Path(__file__).resolve().parent.parent / "layouts" / "podcast-pip.json"


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        sys.exit(f"Fallo: {' '.join(str(c) for c in cmd)}\n{result.stderr}")
    return result


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height,r_frame_rate,nb_frames,pix_fmt", "-of", "json", str(path)]).stdout
    stream = json.loads(out)["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    return {
        "width": stream["width"],
        "height": stream["height"],
        "fps": float(num) / float(den),
        "frames": int(stream.get("nb_frames") or 0),
        "pix_fmt": stream.get("pix_fmt", ""),
    }


def even(value):
    return int(round(value / 2.0)) * 2


def resolve_transform(source_w, source_h, box, canvas):
    """Zoom y Pan de Resolve para que un clip cubra su recuadro (ajuste 'scaleToFit')."""
    canvas_w, canvas_h = canvas
    fit = min(canvas_w / source_w, canvas_h / source_h)
    fit_w, fit_h = source_w * fit, source_h * fit
    # Un 0,3 % de mas para que el clip tape el hueco entero y no asome el borde.
    zoom = max(box["w"] / fit_w, box["h"] / fit_h) * 1.003
    center_x = box["x"] + box["w"] / 2
    center_y = box["y"] + box["h"] / 2
    # Pan y Tilt no van en pixeles del timeline: se escalan con el tamano ajustado del clip.
    pan = (center_x - canvas_w / 2) * canvas_w / fit_w
    tilt = (canvas_h / 2 - center_y) * canvas_h / fit_h
    return {"ZoomX": round(zoom, 4), "ZoomY": round(zoom, 4), "Pan": round(pan, 1), "Tilt": round(tilt, 1)}


def compute(layout, person, screen):
    canvas_w, canvas_h = layout["canvas"]

    person_w = layout["person"]["width"]
    person_h = even(person_w * person["height"] / person["width"])
    person_box = {"x": layout["person"]["x"], "y": (canvas_h - person_h) // 2, "w": person_w, "h": person_h}

    area_x = layout["screen"]["x"]
    area_w = canvas_w - layout["screen"]["right_margin"] - area_x
    area_h = canvas_h - 2 * layout["screen"]["vertical_margin"]
    aspect = screen["width"] / screen["height"]
    screen_w, screen_h = area_w, even(area_w / aspect)
    if screen_h > area_h:
        screen_h, screen_w = area_h, even(area_h * aspect)
    screen_box = {"x": area_x + (area_w - screen_w) // 2, "y": (canvas_h - screen_h) // 2,
                  "w": screen_w, "h": screen_h}

    return {
        "canvas": layout["canvas"],
        "radius": layout["radius"],
        "person": {"box": person_box,
                   "resolve": resolve_transform(person["width"], person["height"], person_box, layout["canvas"])},
        "screen": {"box": screen_box,
                   "resolve": resolve_transform(screen["width"], screen["height"], screen_box, layout["canvas"])},
    }


def rounded_distance(box, radius, grow=0, local=False):
    """Expresion geq: 0 dentro del rectangulo redondeado, 1 fuera, con borde suavizado."""
    center_x = box["w"] / 2 + grow if local else box["x"] + box["w"] / 2
    center_y = box["h"] / 2 + grow if local else box["y"] + box["h"] / 2
    half_w = box["w"] / 2 - radius
    half_h = box["h"] / 2 - radius
    return (f"clip(hypot(max(abs(X-{center_x})-{half_w}\\,0)\\,max(abs(Y-{center_y})-{half_h}\\,0))"
            f"-{radius + grow}+0.5\\,0\\,1)")


def keep_rgb(alpha):
    return f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{alpha}'"


def cmd_layout(args, result):
    print(json.dumps(result, indent=2))


def cmd_frame(args, result):
    canvas_w, canvas_h = result["canvas"]
    outside = "min({}\\,{})".format(rounded_distance(result["person"]["box"], result["radius"]),
                                    rounded_distance(result["screen"]["box"], result["radius"]))
    filters = f"scale={canvas_w}:{canvas_h}:flags=lanczos,format=rgba,{keep_rgb(f'255*{outside}')}"
    run(["ffmpeg", "-v", "error", "-y", "-i", args.background, "-vf", filters, "-frames:v", "1", args.out])
    print(f"Marco: {args.out}")
    print(json.dumps(result, indent=2))


def cmd_intro(args, result, layout):
    canvas_w, canvas_h = result["canvas"]
    box, radius = result["person"]["box"], result["radius"]
    frames = args.frames or layout["intro"]["frames"]
    fade = layout["intro"]["fade_frames"]
    fps = probe(args.render)["fps"]
    grow = 3  # el relleno de fondo tapa 3 px de mas para que no asome el contorno del hueco

    fill = "255*(1-{})".format(rounded_distance(box, radius, grow=grow, local=True))
    person = "255*(1-{})*min(N/{}\\,1)".format(rounded_distance(box, radius, local=True), fade)
    travel = box["x"] + box["w"] + 20
    graph = (
        f"[1:v]scale={canvas_w}:{canvas_h}:flags=lanczos,"
        f"crop={box['w'] + 2 * grow}:{box['h'] + 2 * grow}:{box['x'] - grow}:{box['y'] - grow},"
        f"format=rgba,{keep_rgb(fill)}[fill];"
        f"[0:v]crop={box['w']}:{box['h']}:{box['x']}:{box['y']},format=rgba,{keep_rgb(person)}[person];"
        f"color=black@0:s={canvas_w}x{canvas_h}:r={fps},format=rgba[canvas];"
        f"[canvas][fill]overlay={box['x'] - grow}:{box['y'] - grow}:format=auto[base];"
        f"[base][person]overlay=x='{box['x']}-{travel}*pow(1-min(n/{frames}\\,1)\\,3)':y={box['y']}"
        f":format=auto:shortest=1,scale=out_color_matrix=bt709:out_range=tv,format=yuva444p10le[out]"
    )
    run(["ffmpeg", "-v", "error", "-y", "-t", str(frames / fps), "-i", args.render,
         "-loop", "1", "-framerate", str(fps), "-i", args.background,
         "-filter_complex", graph, "-map", "[out]", "-frames:v", str(frames), "-r", str(fps),
         "-c:v", "prores_ks", "-profile:v", "4444",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
         args.out])
    print(f"Entrada: {args.out} ({frames} fotogramas a {fps:g} fps)")


def cmd_alpha(args):
    info = probe(args.video)
    has_alpha = "a" in info["pix_fmt"].split("p")[0]
    audio = run(["ffmpeg", "-hide_banner", "-i", args.video, "-vn", "-af", "volumedetect", "-f", "null", "-"]).stderr
    peak = next((line.split("max_volume:")[1].strip() for line in audio.splitlines() if "max_volume" in line), None)
    orientation = "horizontal" if info["width"] >= info["height"] else "vertical"
    print(f"{info['width']}x{info['height']} ({orientation}), {info['fps']:g} fps, {info['frames']} fotogramas, {info['pix_fmt']}")
    print("Transparencia: " + ("si" if has_alpha else "NO - se veria con fondo opaco"))
    if peak is None:
        print("Audio: sin pista")
    elif float(peak.split()[0]) < -80:
        print(f"Audio: pista en silencio ({peak})")
    else:
        print(f"Audio: pico {peak}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_sources(p):
        p.add_argument("--person", required=True, help="video de la persona")
        p.add_argument("--screen", required=True, help="video de la pantalla")
        p.add_argument("--layout", default=str(DEFAULT_LAYOUT), help="JSON del formato")

    add_sources(sub.add_parser("layout", help="recuadros y transformaciones de Resolve"))

    p = sub.add_parser("frame", help="marco de fondo con huecos redondeados")
    add_sources(p)
    p.add_argument("--background", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("intro", help="clip de entrada de la persona (ProRes 4444 con alfa)")
    add_sources(p)
    p.add_argument("--background", required=True)
    p.add_argument("--render", required=True, help="render de prueba del arranque del timeline")
    p.add_argument("--out", required=True)
    p.add_argument("--frames", type=int)

    p = sub.add_parser("alpha", help="comprobar transparencia, orientacion y audio de un overlay")
    p.add_argument("--video", required=True)

    args = parser.parse_args()
    if args.command == "alpha":
        cmd_alpha(args)
        return

    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    result = compute(layout, probe(args.person), probe(args.screen))
    if args.command == "layout":
        cmd_layout(args, result)
    elif args.command == "frame":
        cmd_frame(args, result)
    else:
        cmd_intro(args, result, layout)


if __name__ == "__main__":
    main()
