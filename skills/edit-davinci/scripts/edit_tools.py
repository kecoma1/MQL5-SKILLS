"""Apoyo con ffmpeg para editar con DaVinci Resolve: lo que la API de Resolve no da.

Subcomandos:
  probe    resolucion, fps, duracion y fotogramas de un video
  silence  busca el silencio real mas cercano a un punto de corte
  frames   saca fotogramas del video fuente para decidir el encuadre
  encode   genera una copia ligera para subir a partir del master de Resolve
  review   fotogramas y comprobaciones para revisar un render antes de entregarlo

Solo necesita Python 3 y ffmpeg/ffprobe en el PATH.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(video):
    res = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames:format=duration,size,bit_rate",
               "-of", "json", video])
    if res.returncode != 0:
        sys.exit(res.stderr)
    info = json.loads(res.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return {
        "width": v["width"], "height": v["height"], "fps": float(num) / float(den),
        "frames": int(v.get("nb_frames", 0)), "duration": float(info["format"]["duration"]),
        "size_mb": int(info["format"]["size"]) / 1e6, "mbps": int(info["format"]["bit_rate"]) / 1e6,
        "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
    }


def cmd_probe(args):
    p = probe(args.video)
    print(f"{p['width']}x{p['height']}, {p['fps']:g} fps, {p['duration']:.2f}s, {p['frames']} fotogramas, "
          f"{p['size_mb']:.1f} MB, {p['mbps']:.1f} Mbps, audio: {'si' if p['has_audio'] else 'no'}")


def cmd_silence(args):
    fps = args.fps or probe(args.video)["fps"]
    start = max(0.0, args.at - args.window)
    res = run([
        "ffmpeg", "-hide_banner", "-nostats", "-ss", f"{start:.3f}", "-t", f"{args.window * 2:.3f}",
        "-i", args.video, "-vn",
        "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ])
    points, t = [], None
    for line in res.stderr.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"RMS_level=(-?[\d.]+|-inf)", line)
        if m and t is not None:
            level = -120.0 if m.group(1) == "-inf" else float(m.group(1))
            points.append((start + t, level))
    if not points:
        sys.exit("No se pudo medir el audio:\n" + res.stderr[-500:])

    runs, current = [], []
    for t, level in points:
        if level <= args.threshold:
            current.append(t)
        elif current:
            runs.append((current[0], current[-1]))
            current = []
    if current:
        runs.append((current[0], current[-1]))
    if not runs:
        quietest = min(points, key=lambda p: p[1])
        print(f"Sin silencio por debajo de {args.threshold} dB. Punto mas bajo: {quietest[0]:.3f}s "
              f"({quietest[1]:.1f} dB) = fotograma {round(quietest[0] * fps)} a {fps:g} fps")
        return

    runs.sort(key=lambda r: abs((r[0] + r[1]) / 2 - args.at))
    print(f"Silencios cerca de {args.at:.2f}s (umbral {args.threshold} dB), el mas cercano primero:")
    for a, b in runs[:5]:
        mid = (a + b) / 2
        print(f"  {a:.3f}s -> {b:.3f}s  ({(b - a) * 1000:.0f} ms)  corte sugerido {mid:.3f}s = fotograma {round(mid * fps)} a {fps:g} fps")


def grab(video, t, out, width=540, from_end=False):
    seek = ["-sseof", f"{t:.3f}"] if from_end else ["-ss", f"{t:.3f}"]
    run(["ffmpeg", "-v", "error", "-y", *seek, "-i", video, "-frames:v", "1", "-update", "1",
         "-vf", f"scale={width}:-2", "-q:v", "3", str(out)])


def cmd_frames(args):
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for t in args.at:
        out = outdir / f"src_{t:08.2f}.jpg"
        grab(args.video, t, out, args.width)
        print(out)


def cmd_encode(args):
    out = str(Path(args.out).resolve())
    res = run([
        "ffmpeg", "-v", "error", "-y", "-i", str(Path(args.video).resolve()),
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf),
        "-maxrate", args.maxrate, "-bufsize", args.bufsize, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out,
    ])
    if res.returncode != 0:
        sys.exit(res.stderr)
    print(f"Listo: {out} ({Path(out).stat().st_size / 1e6:.1f} MB)")


def cmd_review(args):
    video = str(Path(args.video).resolve())
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    p = probe(video)
    print(f"{p['width']}x{p['height']} {p['fps']:g} fps, {p['duration']:.2f}s, {p['size_mb']:.1f} MB, {p['mbps']:.1f} Mbps")

    count = int(p["duration"] // args.every) + 1
    rows = -(-count // args.cols)
    run(["ffmpeg", "-v", "error", "-y", "-i", video,
         "-vf", f"fps=1/{args.every},scale={args.thumb}:-2,tile={args.cols}x{rows}",
         "-frames:v", "1", "-update", "1", "-q:v", "3", str(outdir / "sheet.jpg")])
    grab(video, 0, outdir / "first.jpg")
    grab(video, -0.05, outdir / "last.jpg", from_end=True)
    for t in args.at or []:
        grab(video, t, outdir / f"at_{t:07.2f}.jpg")
    for t in args.strip or []:
        # animaciones: 16 fotogramas seguidos de la franja de subtitulos
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-update", "1",
             "-vf", "crop=iw:ih*0.22:0:ih*0.67,scale=540:-2,tile=2x8", "-q:v", "3",
             str(outdir / f"strip_{t:07.2f}.jpg")])

    checks = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video,
                  "-vf", "blackdetect=d=0.1:pix_th=0.10,freezedetect=n=-60dB:d=1",
                  "-af", "volumedetect", "-f", "null", "-"]).stderr
    problems = [l.strip() for l in checks.splitlines() if "black_start" in l or "freeze_start" in l]
    volume = [l.split("]")[-1].strip() for l in checks.splitlines() if "mean_volume" in l or "max_volume" in l]
    print("Audio: " + ", ".join(volume))
    print("Negros/congelados: " + ("; ".join(problems) if problems else "ninguno"))
    print(f"Fotogramas en {outdir} (sheet.jpg = uno cada {args.every}s, first.jpg, last.jpg)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe", help="propiedades del video")
    p.add_argument("--video", required=True)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("silence", help="silencio real mas cercano a un punto de corte")
    p.add_argument("--video", required=True)
    p.add_argument("--at", type=float, required=True, help="segundo aproximado del corte")
    p.add_argument("--window", type=float, default=1.5)
    p.add_argument("--threshold", type=float, default=-40.0, help="dB RMS")
    p.add_argument("--fps", type=float, help="por defecto, los del video")
    p.set_defaults(func=cmd_silence)

    p = sub.add_parser("frames", help="fotogramas sueltos del video fuente")
    p.add_argument("--video", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--at", type=float, nargs="+", required=True)
    p.add_argument("--width", type=int, default=960)
    p.set_defaults(func=cmd_frames)

    p = sub.add_parser("encode", help="copia ligera para subir, sin subtitulos")
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--maxrate", default="14M")
    p.add_argument("--bufsize", default="28M")
    p.set_defaults(func=cmd_encode)

    p = sub.add_parser("review", help="fotogramas y comprobaciones de un render")
    p.add_argument("--video", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--every", type=float, default=5.0)
    p.add_argument("--cols", type=int, default=8)
    p.add_argument("--thumb", type=int, default=270)
    p.add_argument("--at", type=float, nargs="*", help="segundos concretos a extraer a mayor tamano")
    p.add_argument("--strip", type=float, nargs="*", help="segundos desde los que sacar 16 fotogramas seguidos de la franja de subtitulos")
    p.set_defaults(func=cmd_review)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
