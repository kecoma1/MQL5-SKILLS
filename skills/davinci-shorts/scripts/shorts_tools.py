"""Herramientas para sacar shorts verticales de un video largo.

Subcomandos:
  silence  busca el silencio real mas cercano a un punto de corte
  subs     genera SRT + ASS (caja clara, palabras que se oscurecen al decirse) desde la transcripcion por palabras
  burn     quema el ASS en el video y genera la copia ligera para subir
  review   saca fotogramas y comprobaciones para revisar un render

Solo necesita Python 3 y ffmpeg/ffprobe en el PATH.
"""

import argparse
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

PUNCT = ".,;:!?¿¡\"'()"
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FONT = SKILL_DIR / "fonts" / "Poppins-Bold.ttf"

# Colores medidos en la muestra de referencia del usuario
BOX_COLOR = "ebe9ea"
TEXT_COLOR = "252324"
PENDING_COLOR = "bfbdbe"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def norm(token):
    return token.strip(PUNCT).lower()


def ass_color(hex_rgb):
    return f"&H{hex_rgb[4:6]}{hex_rgb[2:4]}{hex_rgb[0:2]}&".upper()


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


# ---------------------------------------------------------------- fuente

class Font:
    """Lee de un TTF lo justo para medir texto: la caja se dibuja a medida de cada subtitulo."""

    def __init__(self, path):
        data = Path(path).read_bytes()
        tables = {}
        for i in range(struct.unpack(">H", data[4:6])[0]):
            tag, _, offset, length = struct.unpack(">4sIII", data[12 + i * 16:28 + i * 16])
            tables[tag.decode()] = data[offset:offset + length]

        self.upm = struct.unpack(">H", tables["head"][18:20])[0]
        ascender, descender = struct.unpack(">hh", tables["hhea"][4:8])
        n_metrics = struct.unpack(">H", tables["hhea"][34:36])[0]
        win_ascent, win_descent = struct.unpack(">HH", tables["OS/2"][74:78])
        # libass escala la fuente para que estas dos medidas sumen el Fontsize
        self.ascent, self.descent = (win_ascent, win_descent) if win_ascent + win_descent else (ascender, -descender)

        hmtx = tables["hmtx"]
        self.advances = [struct.unpack(">H", hmtx[i * 4:i * 4 + 2])[0] for i in range(n_metrics)]
        self.cmap = self._read_cmap(tables["cmap"])
        self.family = self._read_family(tables["name"])

    @staticmethod
    def _read_cmap(cmap):
        best = None
        for i in range(struct.unpack(">H", cmap[2:4])[0]):
            platform, encoding, offset = struct.unpack(">HHI", cmap[4 + i * 8:12 + i * 8])
            fmt = struct.unpack(">H", cmap[offset:offset + 2])[0]
            if platform == 3 and fmt == 12:
                best = (12, offset)
                break
            if platform == 3 and fmt == 4 and best is None:
                best = (4, offset)
        if best is None:
            sys.exit("La fuente no tiene un cmap Unicode legible.")

        fmt, off = best
        mapping = {}
        if fmt == 12:
            for g in range(struct.unpack(">I", cmap[off + 12:off + 16])[0]):
                start, end, glyph = struct.unpack(">III", cmap[off + 16 + g * 12:off + 28 + g * 12])
                for code in range(start, end + 1):
                    mapping[code] = glyph + code - start
            return mapping

        seg = struct.unpack(">H", cmap[off + 6:off + 8])[0] // 2
        ends = struct.unpack(f">{seg}H", cmap[off + 14:off + 14 + seg * 2])
        base = off + 16 + seg * 2
        starts = struct.unpack(f">{seg}H", cmap[base:base + seg * 2])
        deltas = struct.unpack(f">{seg}h", cmap[base + seg * 2:base + seg * 4])
        range_pos = base + seg * 4
        ranges = struct.unpack(f">{seg}H", cmap[range_pos:range_pos + seg * 2])
        for s in range(seg):
            for code in range(starts[s], ends[s] + 1):
                if code == 0xFFFF:
                    continue
                if ranges[s] == 0:
                    glyph = (code + deltas[s]) & 0xFFFF
                else:
                    pos = range_pos + s * 2 + ranges[s] + (code - starts[s]) * 2
                    glyph = struct.unpack(">H", cmap[pos:pos + 2])[0]
                    if glyph:
                        glyph = (glyph + deltas[s]) & 0xFFFF
                mapping[code] = glyph
        return mapping

    @staticmethod
    def _read_family(name):
        count, string_offset = struct.unpack(">HH", name[2:6])
        for i in range(count):
            platform, _, _, name_id, length, offset = struct.unpack(">HHHHHH", name[6 + i * 12:18 + i * 12])
            if name_id == 1 and platform == 3:
                return name[string_offset + offset:string_offset + offset + length].decode("utf-16-be")
        return "Poppins"

    def width(self, text, em):
        units = 0
        for ch in text:
            glyph = self.cmap.get(ord(ch), 0)
            units += self.advances[min(glyph, len(self.advances) - 1)]
        return units / self.upm * em

    def ass_size(self, em):
        return em * (self.ascent + self.descent) / self.upm

    def baseline_offset(self, em):
        """Distancia del centro de la linea (\\an5) a la linea base."""
        return (self.ascent - self.descent) / 2 / self.upm * em


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
                    "text": w["text"].replace(" ", " "),  # "90 £" llega con espacio duro
                    "start": max(0.0, w["start"] - t_in),
                    "end": min(t_out, w_end) - t_in,
                    "eos": bool(w.get("eos")),
                })
    return words


def apply_corrections(words, rules):
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


def mark_emphasis(words, phrases):
    """Marca las palabras que van solas y en grande. Una frase de la lista puede abarcar varias palabras."""
    targets = sorted({" ".join(norm(t) for t in p.split()) for p in phrases}, key=lambda p: -len(p))
    i, tag = 0, 0
    while i < len(words):
        for n in (3, 2, 1):
            chunk = words[i:i + n]
            if len(chunk) == n and " ".join(norm(c["text"]) for c in chunk) in targets:
                tag += 1
                for c in chunk:
                    c["emph"] = tag
                i += n
                break
        else:
            i += 1
    return words


def group_words(words, max_chars, max_words, max_gap):
    groups, current = [], []

    def flush(big=False):
        nonlocal current
        if current:
            groups.append({"words": current, "big": big})
            current = []

    for idx, w in enumerate(words):
        nxt = words[idx + 1] if idx + 1 < len(words) else None
        if w.get("emph"):
            if current and current[-1].get("emph") != w["emph"]:
                flush(big=bool(current[-1].get("emph")))
            current.append(w)
            if nxt is None or nxt.get("emph") != w["emph"]:
                flush(big=True)
            continue

        length = len(" ".join(x["text"] for x in current + [w]))
        ends_phrase = w["eos"] or w["text"][-1] in ",;:.?!"
        full = length > max_chars or len(current) >= max_words
        # la palabra que cierra una frase se queda con su grupo aunque se pase un poco,
        # para no dejar subtitulos de una sola palabra ("antes,", "gente,")
        fits_as_tail = ends_phrase and length <= max_chars + 6 and len(current) <= max_words
        if current and full and not fits_as_tail:
            flush()
        current.append(w)
        long_gap = nxt is not None and nxt["start"] - w["end"] > max_gap
        if ends_phrase or long_gap or (nxt is not None and nxt.get("emph")):
            flush()
    flush()

    # una palabra corta suelta delante de una destacada ("una" + "locura") va con ella en grande
    merged = []
    for g in groups:
        prev = merged[-1] if merged else None
        if (g["big"] and prev and not prev["big"] and len(prev["words"]) == 1
                and len(prev["words"][0]["text"]) <= 4 and prev["words"][0]["text"][-1] not in ",;:.?!"):
            merged[-1] = {"words": prev["words"] + g["words"], "big": True}
        else:
            merged.append(g)
    return merged


def group_end(groups, i, hold, clip_len):
    last_end = groups[i]["words"][-1]["end"]
    nxt = groups[i + 1]["words"][0]["start"] if i + 1 < len(groups) else clip_len
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


def rounded_box(w, h, r):
    w, h, r = round(w), round(h), round(r)
    return (f"m {r} 0 l {w - r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h - r} b {w} {h} {w} {h} {w - r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h - r} l 0 {r} b 0 0 0 0 {r} 0")


def cmd_subs(args):
    clip_len = args.end - args.start
    config = json.loads(Path(args.corrections).read_text(encoding="utf-8")) if args.corrections else {}
    words = load_words(args.transcript, args.start, args.end)
    words = apply_corrections(words, config.get("replacements", []))
    if not words:
        sys.exit("No hay palabras en ese rango de la transcripcion.")
    words = mark_emphasis(words, config.get("emphasis", []))
    groups = group_words(words, args.max_chars, args.max_words, args.max_gap)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    srt = []
    for i, g in enumerate(groups):
        end = group_end(groups, i, args.hold, clip_len)
        srt.append(f"{i + 1}\n{ts_srt(g['words'][0]['start'])} --> {ts_srt(end)}\n{' '.join(w['text'] for w in g['words'])}\n")
    srt_path = outdir / f"{args.name}.srt"
    srt_path.write_text("\n".join(srt), encoding="utf-8")

    font = Font(args.font_file)
    scale = args.width / 1080
    cx, cy = args.width / 2, args.height * args.y
    box, dark, pending = ass_color(BOX_COLOR), ass_color(TEXT_COLOR), ass_color(PENDING_COLOR)
    pop = f"\\fad({args.fade},0)\\fscx94\\fscy94\\t(0,{args.fade},\\fscx100\\fscy100)"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {args.width}
PlayResY: {args.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font.family},{font.ass_size(args.size * scale):.1f},&H00000000,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, g in enumerate(groups):
        gw = g["words"]
        start, end = gw[0]["start"], group_end(groups, i, args.hold, clip_len)
        tokens = [display(w["text"]) for w in gw]
        em = (args.big_size if g["big"] else args.size) * scale
        pad = 30 * scale + em * 0.06
        text_w = font.width(" ".join(tokens), em)
        limit = args.width * 0.9 - 2 * pad
        if text_w > limit:  # nunca se sale del encuadre: se encoge
            em *= limit / text_w
            text_w = limit
        box_w, box_h = text_w + 2 * pad, em * 1.65
        # la linea base cae al 67,5 % de la caja, como en la muestra
        text_y = cy + box_h * 0.175 - font.baseline_offset(em)

        events.append(
            f"Dialogue: 0,{ts_ass(start)},{ts_ass(end)},Caption,,0,0,0,,"
            f"{{\\an5\\pos({cx:.0f},{cy:.0f})\\1c{box}\\bord0\\shad0{pop}\\p1}}{rounded_box(box_w, box_h, args.radius * scale)}{{\\p0}}"
        )
        parts = []
        for k, (w, token) in enumerate(zip(gw, tokens)):
            if k == 0:
                parts.append(f"{{\\1c{dark}}}{token}")
            else:
                at = round((w["start"] - start) * 1000)
                parts.append(f"{{\\1c{pending}\\t({at},{at + 60},\\1c{dark})}}{token}")
        events.append(
            f"Dialogue: 1,{ts_ass(start)},{ts_ass(end)},Caption,,0,0,0,,"
            f"{{\\an5\\pos({cx:.0f},{text_y:.0f})\\fs{font.ass_size(em):.1f}{pop}}}{' '.join(parts)}"
        )
    ass_path = outdir / f"{args.name}.ass"
    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

    big = sum(1 for g in groups if g["big"])
    print(f"{len(words)} palabras, {len(groups)} subtitulos ({big} en grande)")
    print(f"SRT: {srt_path}")
    print(f"ASS: {ass_path}")


# ---------------------------------------------------------------- burn

def cmd_burn(args):
    ass = Path(args.ass).resolve()
    video = str(Path(args.video).resolve())
    out = str(Path(args.out).resolve())
    fonts = Path(args.fonts_dir).resolve().as_posix().replace(":", "\\:")
    # el filtro subtitles no traga rutas de Windows: se ejecuta en la carpeta del .ass
    res = run([
        "ffmpeg", "-v", "error", "-y", "-i", video,
        "-vf", f"subtitles={ass.name}:fontsdir='{fonts}'",
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf),
        "-maxrate", args.maxrate, "-bufsize", args.bufsize, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out,
    ], cwd=str(ass.parent))
    if res.returncode != 0:
        sys.exit(res.stderr)
    if res.stderr.strip():
        print(res.stderr.strip())
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
         "-frames:v", "1", "-update", "1", "-q:v", "3", str(outdir / "sheet.jpg")])
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-frames:v", "1", "-update", "1", "-vf", "scale=540:-2",
         "-q:v", "3", str(outdir / "first.jpg")])
    run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.05", "-i", video, "-frames:v", "1", "-update", "1",
         "-vf", "scale=540:-2", "-q:v", "3", str(outdir / "last.jpg")])
    for t in args.at or []:
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-update", "1",
             "-vf", "scale=540:-2", "-q:v", "3", str(outdir / f"at_{t:07.2f}.jpg")])
    for t in args.strip or []:
        # animaciones: 16 fotogramas seguidos de la mitad inferior, para ver entradas y cambios de palabra
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
    p.add_argument("--corrections", help="JSON con replacements[{from, to}] y emphasis[]")
    p.add_argument("--outdir", required=True)
    p.add_argument("--name", required=True, help="nombre base, sin espacios ni extension")
    p.add_argument("--max-chars", type=int, default=18)
    p.add_argument("--max-words", type=int, default=3)
    p.add_argument("--max-gap", type=float, default=0.5)
    p.add_argument("--hold", type=float, default=0.6, help="segundos que aguanta un subtitulo tras su ultima palabra")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--y", type=float, default=0.783, help="altura del centro de la caja (0 arriba, 1 abajo)")
    p.add_argument("--font-file", default=str(DEFAULT_FONT))
    p.add_argument("--size", type=float, default=56, help="cuerpo del texto normal, en px a 1080 de ancho")
    p.add_argument("--big-size", type=float, default=103, help="cuerpo de las palabras destacadas")
    p.add_argument("--radius", type=float, default=10)
    p.add_argument("--fade", type=int, default=90, help="ms de la entrada de cada caja")
    p.set_defaults(func=cmd_subs)

    p = sub.add_parser("burn", help="quema el ASS y genera la copia para subir")
    p.add_argument("--video", required=True)
    p.add_argument("--ass", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--fonts-dir", default=str(DEFAULT_FONT.parent))
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
    p.add_argument("--strip", type=float, nargs="*", help="segundos desde los que sacar 16 fotogramas seguidos de la zona de subtitulos")
    p.set_defaults(func=cmd_review)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
