"""Subtitulos quemados para shorts verticales, con el estilo guardado en style.json.

Subcomandos:
  build  genera SRT + ASS desde la transcripcion por palabras
  burn   quema el ASS en el video y genera la copia ligera para subir

Solo necesita Python 3 y ffmpeg en el PATH. Todo el aspecto sale de style.json:
con el mismo JSON, la misma fuente y la misma transcripcion el resultado es identico.
"""

import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

PUNCT = ".,;:!?¿¡\"'()"
PHRASE_END = ",;:.?!"
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STYLE = SKILL_DIR / "style.json"


def norm(token):
    return token.strip(PUNCT).lower()


def ass_color(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def load_style(path):
    path = Path(path)
    style = json.loads(path.read_text(encoding="utf-8"))
    font = Path(style["font_file"])
    style["font_path"] = font if font.is_absolute() else path.parent / font
    if not style["font_path"].is_file():
        sys.exit(f"Falta la fuente {style['font_path']}. Copiarla ahi o cambiar font_file en {path}.")
    return style


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


# ---------------------------------------------------------------- palabras

def load_words(transcript, t_in, t_out, min_inside):
    data = json.loads(Path(transcript).read_text(encoding="utf-8"))
    words = []
    for segment in data["segments"]:
        for w in segment["words"]:
            if w.get("type", "word") != "word":
                continue
            w_end = w["start"] + w["duration"]
            inside = min(w_end, t_out) - max(w["start"], t_in)
            # una palabra a caballo del corte solo entra si se oye casi entera
            if w["duration"] > 0 and inside / w["duration"] >= min_inside:
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


def mark_emphasis(words, phrases, max_words):
    """Marca las palabras que van solas y en grande. Una frase de la lista puede abarcar varias palabras."""
    targets = {" ".join(norm(t) for t in p.split()) for p in phrases}
    i, tag = 0, 0
    while i < len(words):
        for n in range(max_words, 0, -1):
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


def group_words(words, rules):
    max_chars, max_words = rules["max_chars"], rules["max_words"]
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
        ends_phrase = w["eos"] or w["text"][-1] in PHRASE_END
        full = length > max_chars or len(current) >= max_words
        # la palabra que cierra una frase se queda con su grupo aunque se pase un poco,
        # para no dejar subtitulos de una sola palabra ("antes,", "gente,")
        fits_as_tail = ends_phrase and length <= max_chars + rules["tail_extra_chars"] and len(current) <= max_words
        if current and full and not fits_as_tail:
            flush()
        current.append(w)
        long_gap = nxt is not None and nxt["start"] - w["end"] > rules["max_gap_s"]
        if ends_phrase or long_gap or (nxt is not None and nxt.get("emph")):
            flush()
    flush()

    # una palabra corta suelta delante de una destacada ("una" + "locura") va con ella en grande
    merged = []
    for g in groups:
        prev = merged[-1] if merged else None
        if (g["big"] and prev and not prev["big"] and len(prev["words"]) == 1
                and len(prev["words"][0]["text"]) <= rules["merge_short_word_chars"]
                and prev["words"][0]["text"][-1] not in PHRASE_END):
            merged[-1] = {"words": prev["words"] + g["words"], "big": True}
        else:
            merged.append(g)
    return merged


def group_end(groups, i, hold, clip_len):
    last_end = groups[i]["words"][-1]["end"]
    nxt = groups[i + 1]["words"][0]["start"] if i + 1 < len(groups) else clip_len
    # si el hueco es corto se mantiene en pantalla hasta el siguiente para que no parpadee
    return nxt if nxt - last_end <= hold else last_end + hold


# ---------------------------------------------------------------- salida

def ts_srt(t):
    ms = max(0, round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ts_ass(t):
    cs = max(0, round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def rounded_box(w, h, r):
    w, h = round(w), round(h)
    r = min(round(r), h // 2, w // 2)
    c = round(r * 0.448)  # puntos de control para que la esquina sea un arco de circulo
    return (f"m {r} 0 l {w - r} 0 b {w - c} 0 {w} {c} {w} {r} l {w} {h - r} b {w} {h - c} {w - c} {h} {w - r} {h} "
            f"l {r} {h} b {c} {h} 0 {h - c} 0 {h - r} l 0 {r} b 0 {c} {c} 0 {r} 0")


def cmd_build(args):
    style = load_style(args.style)
    box_s, anim, text_s = style["box"], style["animation"], style["text"]
    clip_len = args.end - args.start

    clip = json.loads(Path(args.clip_config).read_text(encoding="utf-8")) if args.clip_config else {}
    words = load_words(args.transcript, args.start, args.end, style["grouping"]["min_word_inside"])
    words = apply_corrections(words, clip.get("replacements", []))
    if not words:
        sys.exit("No hay palabras en ese rango de la transcripcion.")
    words = mark_emphasis(words, clip.get("emphasis", []), style["grouping"]["emphasis_max_words"])
    groups = group_words(words, style["grouping"])

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    srt = []
    for i, g in enumerate(groups):
        end = group_end(groups, i, anim["hold_s"], clip_len)
        srt.append(f"{i + 1}\n{ts_srt(g['words'][0]['start'])} --> {ts_srt(end)}\n{' '.join(w['text'] for w in g['words'])}\n")
    srt_path = outdir / f"{args.name}.srt"
    srt_path.write_text("\n".join(srt), encoding="utf-8")

    font = Font(style["font_path"])
    scale = args.width / style["reference_width"]
    cx, cy = args.width / 2, args.height * style["position_y"]
    box = ass_color(style["colors"]["box"])
    dark = ass_color(style["colors"]["text"])
    pending = ass_color(style["colors"]["pending"])
    fade, scale_from = anim["box_fade_ms"], anim["box_scale_from"]
    pop = f"\\fad({fade},0)\\fscx{scale_from}\\fscy{scale_from}\\t(0,{fade},\\fscx100\\fscy100)"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {args.width}
PlayResY: {args.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font.family},{font.ass_size(text_s['size'] * scale):.1f},&H00000000,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, g in enumerate(groups):
        gw = g["words"]
        start, end = gw[0]["start"], group_end(groups, i, anim["hold_s"], clip_len)
        tokens = [w["text"].rstrip(text_s["strip_trailing"]) for w in gw]
        em = (text_s["emphasis_size"] if g["big"] else text_s["size"]) * scale
        pad = box_s["padding_x"] * scale + em * box_s["padding_x_em"]
        text_w = font.width(" ".join(tokens), em)
        limit = args.width * box_s["max_width"] - 2 * pad
        if text_w > limit:  # nunca se sale del encuadre: se encoge
            em *= limit / text_w
            text_w = limit
        box_w, box_h = text_w + 2 * pad, em * box_s["height_em"]
        text_y = cy + box_h * (box_s["baseline"] - 0.5) - font.baseline_offset(em)

        events.append(
            f"Dialogue: 0,{ts_ass(start)},{ts_ass(end)},Caption,,0,0,0,,"
            f"{{\\an5\\pos({cx:.0f},{cy:.0f})\\1c{box}\\bord0\\shad0{pop}\\p1}}{rounded_box(box_w, box_h, box_h * box_s['roundness'])}{{\\p0}}"
        )
        parts = []
        for k, (w, token) in enumerate(zip(gw, tokens)):
            if k == 0:
                parts.append(f"{{\\1c{dark}}}{token}")
            else:
                at = round((w["start"] - start) * 1000)
                # el fundido se acorta si la caja se va antes, para que la palabra llegue a oscurecerse
                word_fade = min(anim["word_fade_ms"], max(anim["word_fade_min_ms"], round((end - w["start"]) * 1000)))
                parts.append(f"{{\\1c{pending}\\t({at},{at + word_fade},\\1c{dark})}}{token}")
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


def cmd_burn(args):
    style = load_style(args.style)
    enc = style["burn"]
    ass = Path(args.ass).resolve()
    fonts = style["font_path"].resolve().parent.as_posix().replace(":", "\\:")
    out = str(Path(args.out).resolve())
    # el filtro subtitles no traga rutas de Windows: se ejecuta en la carpeta del .ass
    res = subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(Path(args.video).resolve()),
        "-vf", f"subtitles={ass.name}:fontsdir='{fonts}'",
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", enc["preset"], "-crf", str(enc["crf"]),
        "-maxrate", enc["maxrate"], "-bufsize", enc["bufsize"], "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", enc["audio_bitrate"], "-movflags", "+faststart", out,
    ], cwd=str(ass.parent), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        sys.exit(res.stderr)
    if res.stderr.strip():
        print(res.stderr.strip())
    print(f"Listo: {out} ({Path(out).stat().st_size / 1e6:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="SRT + ASS del tramo")
    p.add_argument("--transcript", required=True, help="JSON con segments[].words[] (start, duration, text, eos)")
    p.add_argument("--start", type=float, required=True, help="segundo de entrada en el video original")
    p.add_argument("--end", type=float, required=True, help="segundo de salida en el video original")
    p.add_argument("--clip-config", help="JSON del video con replacements[{from, to}] y emphasis[]")
    p.add_argument("--outdir", required=True)
    p.add_argument("--name", required=True, help="nombre base, sin espacios ni extension")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--style", default=str(DEFAULT_STYLE))
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("burn", help="quema el ASS y genera la copia para subir")
    p.add_argument("--video", required=True)
    p.add_argument("--ass", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--style", default=str(DEFAULT_STYLE))
    p.set_defaults(func=cmd_burn)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
