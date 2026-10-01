"""Herramientas para sacar shorts verticales de un video largo.

Subcomandos:
  silence  busca el silencio real mas cercano a un punto de corte
  subs     genera SRT + ASS (palabra activa resaltada) desde la transcripcion por palabras
  burn     quema el ASS en el video y genera la copia ligera para subir
  review   saca fotogramas y comprobaciones para revisar un render

Solo necesita Python 3 y ffmpeg/ffprobe en el PATH.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PUNCT = ".,;:!?¿¡\"'()"

# Paleta "orange neon" (ASS usa &HBBGGRR&)
ASS_TEXT = "&HE6F4FF&"       # #fff4e6
ASS_HIGHLIGHT = "&H2A8AFF&"  # #ff8a2a
ASS_OUTLINE = "&H060405&"    # #050406


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def norm(token):
    return token.strip(PUNCT).lower()


# ---------------------------------------------------------------- silence

def cmd_silence(args):
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
        print(f"Sin silencio por debajo de {args.threshold} dB. Punto mas bajo: {quietest[0]:.3f}s ({quietest[1]:.1f} dB)")
        return

    runs.sort(key=lambda r: abs((r[0] + r[1]) / 2 - args.at))
    print(f"Silencios cerca de {args.at:.2f}s (umbral {args.threshold} dB), el mas cercano primero:")
    for a, b in runs[:5]:
        mid = (a + b) / 2
        print(f"  {a:.3f}s -> {b:.3f}s  ({(b - a) * 1000:.0f} ms)  corte sugerido {mid:.3f}s = fotograma {round(mid * args.fps)} a {args.fps:g} fps")


# ---------------------------------------------------------------- subs

def load_words(transcript, t_in, t_out):
    data = json.loads(Path(transcript).read_text(encoding="utf-8"))
    words = []
    for segment in data["segments"]:
        for w in segment["words"]:
            if w.get("type", "word") != "word":
                continue
            w_end = w["start"] + w["duration"]
            inside = min(w_end, t_out) - max(w["start"], t_in)
            # una palabra a caballo del corte solo entra si se oye casi entera
            if w["duration"] > 0 and inside / w["duration"] >= 0.6:
                words.append({
                    "text": w["text"],
                    "start": max(0.0, w["start"] - t_in),
                    "end": min(t_out, w["start"] + w["duration"]) - t_in,
                    "eos": bool(w.get("eos")),
                })
    return words


def apply_corrections(words, corrections_path):
    if not corrections_path:
        return words
    rules = json.loads(Path(corrections_path).read_text(encoding="utf-8"))["replacements"]
    rules = [(r["from"].split(), r["to"].split()) for r in rules]
    rules.sort(key=lambda r: -len(r[0]))  # las frases largas ganan a las cortas

    out, i = [], 0
    while i < len(words):
        for src, dst in rules:
            chunk = words[i:i + len(src)]
            if len(chunk) == len(src) and all(norm(c["text"]) == norm(s) for c, s in zip(chunk, src)):
                first, last = chunk[0], chunk[-1]
                lead = first["text"][:len(first["text"]) - len(first["text"].lstrip(PUNCT))]
                trail = last["text"][len(last["text"].rstrip(PUNCT)):]
                span = (last["end"] - first["start"]) / len(dst)
                for k, token in enumerate(dst):
                    text = token
                    if k == 0 and not token[0] in PUNCT:
                        text = lead + text
                    if k == len(dst) - 1 and not token[-1] in PUNCT:
                        text = text + trail
                    out.append({
                        "text": text,
                        "start": first["start"] + span * k,
                        "end": first["start"] + span * (k + 1),
                        "eos": last["eos"] and k == len(dst) - 1,
                    })
                i += len(src)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def group_words(words, max_chars, max_words, max_gap):
    groups, current = [], []
    for idx, w in enumerate(words):
        length = len(" ".join(x["text"] for x in current + [w]))
        ends_phrase = w["eos"] or w["text"][-1] in ",;:.?!"
        full = length > max_chars or len(current) >= max_words
        # la palabra que cierra una frase se queda con su grupo aunque se pase un poco,
        # para no dejar subtitulos de una sola palabra ("antes,", "gente,")
        fits_as_tail = ends_phrase and length <= max_chars + 6 and len(current) <= max_words
        if current and full and not fits_as_tail:
            groups.append(current)
            current = []
        current.append(w)
        nxt = words[idx + 1] if idx + 1 < len(words) else None
        long_gap = nxt is not None and nxt["start"] - w["end"] > max_gap
        if ends_phrase or long_gap:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def group_end(groups, i, hold, clip_len):
    last_end = groups[i][-1]["end"]
    nxt = groups[i + 1][0]["start"] if i + 1 < len(groups) else clip_len
    # si el hueco es corto se mantiene en pantalla hasta el siguiente para que no parpadee
    return nxt if nxt - last_end <= hold else last_end + hold


def ts_srt(t):
    ms = max(0, round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ts_ass(t):
    cs = max(0, round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def display(token):
    return token.rstrip(".,;:")


def cmd_subs(args):
    clip_len = args.end - args.start
    words = apply_corrections(load_words(args.transcript, args.start, args.end), args.corrections)
    if not words:
        sys.exit("No hay palabras en ese rango de la transcripcion.")
    groups = group_words(words, args.max_chars, args.max_words, args.max_gap)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    srt = []
    for i, g in enumerate(groups):
        end = group_end(groups, i, args.hold, clip_len)
        srt.append(f"{i + 1}\n{ts_srt(g[0]['start'])} --> {ts_srt(end)}\n{' '.join(w['text'] for w in g)}\n")
    srt_path = outdir / f"{args.name}.srt"
    srt_path.write_text("\n".join(srt), encoding="utf-8")

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {args.width}
PlayResY: {args.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Short,{args.font},{args.font_size},{ASS_TEXT.replace('&H', '&H00').rstrip('&')},&H000000FF,{ASS_OUTLINE.replace('&H', '&H00').rstrip('&')},&H96000000,0,0,0,0,100,100,0,0,1,{args.outline},3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pos = f"{{\\pos({args.width // 2},{round(args.height * args.y)})}}"
    events = []
    for i, g in enumerate(groups):
        end = group_end(groups, i, args.hold, clip_len)
        for k, w in enumerate(g):
            w_start = g[0]["start"] if k == 0 else w["start"]
            w_end = g[k + 1]["start"] if k + 1 < len(g) else end
            if w_end <= w_start:
                continue
            parts = []
            for j, other in enumerate(g):
                token = display(other["text"])
                if args.upper:
                    token = token.upper()
                parts.append(f"{{\\c{ASS_HIGHLIGHT}}}{token}{{\\c{ASS_TEXT}}}" if j == k else token)
            events.append(f"Dialogue: 0,{ts_ass(w_start)},{ts_ass(w_end)},Short,,0,0,0,,{pos}{' '.join(parts)}")
    ass_path = outdir / f"{args.name}.ass"
    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

    print(f"{len(words)} palabras, {len(groups)} subtitulos")
    print(f"SRT: {srt_path}")
    print(f"ASS: {ass_path}")


# ---------------------------------------------------------------- burn

def cmd_burn(args):
    ass = Path(args.ass).resolve()
    video = str(Path(args.video).resolve())
    out = str(Path(args.out).resolve())
    # el filtro subtitles no traga rutas de Windows: se ejecuta en la carpeta del .ass
    res = run([
        "ffmpeg", "-v", "error", "-y", "-i", video,
        "-vf", f"subtitles={ass.name}",
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf),
        "-maxrate", args.maxrate, "-bufsize", args.bufsize, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out,
    ], cwd=str(ass.parent))
    if res.returncode != 0:
        sys.exit(res.stderr)
    print(f"Listo: {out} ({Path(out).stat().st_size / 1e6:.1f} MB)")


# ---------------------------------------------------------------- review

def cmd_review(args):
    video = str(Path(args.video).resolve())
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    probe = run(["ffprobe", "-v", "error", "-show_entries",
                 "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames:format=duration,size,bit_rate",
                 "-of", "json", video])
    info = json.loads(probe.stdout)
    duration = float(info["format"]["duration"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    print(f"{v['width']}x{v['height']} {v['r_frame_rate']} fps, {duration:.2f}s, "
          f"{int(info['format']['size']) / 1e6:.1f} MB, {int(info['format']['bit_rate']) / 1e6:.1f} Mbps")

    cols = args.cols
    count = int(duration // args.every) + 1
    rows = -(-count // cols)
    run(["ffmpeg", "-v", "error", "-y", "-i", video,
         "-vf", f"fps=1/{args.every},scale={args.thumb}:-2,tile={cols}x{rows}",
         "-frames:v", "1", "-q:v", "3", str(outdir / "sheet.jpg")])
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3",
         str(outdir / "first.jpg")])
    run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.05", "-i", video, "-frames:v", "1", "-vf", "scale=540:-2",
         "-q:v", "3", str(outdir / "last.jpg")])
    for t in args.at or []:
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=540:-2",
             "-q:v", "3", str(outdir / f"at_{t:07.2f}.jpg")])

    checks = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video,
                  "-vf", "blackdetect=d=0.1:pix_th=0.10,freezedetect=n=-60dB:d=1",
                  "-af", "volumedetect", "-f", "null", "-"]).stderr
    problems = [l.strip() for l in checks.splitlines() if "black_start" in l or "freeze_start" in l]
    volume = [l.split("]")[-1].strip() for l in checks.splitlines() if "mean_volume" in l or "max_volume" in l]
    print("Audio: " + ", ".join(volume))
    print("Negros/congelados: " + ("; ".join(problems) if problems else "ninguno"))
    print(f"Fotogramas en {outdir} (sheet.jpg = uno cada {args.every}s, first.jpg, last.jpg)")


# ---------------------------------------------------------------- cli

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("silence", help="silencio real mas cercano a un punto de corte")
    p.add_argument("--video", required=True)
    p.add_argument("--at", type=float, required=True, help="segundo aproximado del corte")
    p.add_argument("--window", type=float, default=1.5)
    p.add_argument("--threshold", type=float, default=-40.0, help="dB RMS")
    p.add_argument("--fps", type=float, default=60.0)
    p.set_defaults(func=cmd_silence)

    p = sub.add_parser("subs", help="SRT + ASS del tramo")
    p.add_argument("--transcript", required=True, help="JSON con segments[].words[] (start, duration, text, eos)")
    p.add_argument("--start", type=float, required=True, help="segundo de entrada en el video original")
    p.add_argument("--end", type=float, required=True, help="segundo de salida en el video original")
    p.add_argument("--corrections", help="JSON con replacements[{from, to}]")
    p.add_argument("--outdir", required=True)
    p.add_argument("--name", required=True, help="nombre base, sin espacios ni extension")
    p.add_argument("--max-chars", type=int, default=16)
    p.add_argument("--max-words", type=int, default=3)
    p.add_argument("--max-gap", type=float, default=0.5)
    p.add_argument("--hold", type=float, default=0.6, help="segundos que aguanta un subtitulo tras su ultima palabra")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--y", type=float, default=0.77, help="altura del centro del texto (0 arriba, 1 abajo)")
    p.add_argument("--font", default="Segoe UI Black")
    p.add_argument("--font-size", type=int, default=104)
    p.add_argument("--outline", type=int, default=7)
    p.add_argument("--upper", action="store_true", help="texto en mayusculas")
    p.set_defaults(func=cmd_subs)

    p = sub.add_parser("burn", help="quema el ASS y genera la copia para subir")
    p.add_argument("--video", required=True)
    p.add_argument("--ass", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--maxrate", default="14M")
    p.add_argument("--bufsize", default="28M")
    p.set_defaults(func=cmd_burn)

    p = sub.add_parser("review", help="fotogramas y comprobaciones de un render")
    p.add_argument("--video", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--every", type=float, default=5.0)
    p.add_argument("--cols", type=int, default=8)
    p.add_argument("--thumb", type=int, default=270)
    p.add_argument("--at", type=float, nargs="*", help="segundos concretos a extraer a mayor tamano")
    p.set_defaults(func=cmd_review)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
