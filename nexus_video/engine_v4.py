from __future__ import annotations
import json, math, os, random, shutil, subprocess, sys, textwrap, uuid, wave
from array import array
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageStat, ImageFont
from .story_v4 import generate_story

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "output"
WORK_ROOT = ROOT / "work"
W, H, FPS = 1080, 1920, 30
BASE_W, BASE_H, RENDER_FPS = 540, 960, 15
SAMPLE_TEXT = "No respondas si el teléfono suena desde una habitación que ya no existe. A veces la llamada no busca hablar contigo; busca saber dónde estás."

VOICES = {
    "es_MX-claude-high": ("es_MX", "claude", "high"),
    "es_MX-ald-medium": ("es_MX", "ald", "medium"),
    "es_ES-davefx-medium": ("es_ES", "davefx", "medium"),
    "es_ES-sharvard-medium": ("es_ES", "sharvard", "medium"),
}
SCENE_NAMES = {
    "phone_room": "Teléfono en una habitación",
    "stairs": "Escalera en perspectiva",
    "receiver_close": "Primer plano del auricular",
    "hallway": "Pasillo y silueta",
    "floor_cable": "Cable en el suelo",
    "mobile_close": "Móvil con llamada entrante",
    "house_exterior": "Exterior de la casa",
    "front_door": "Puerta principal",
    "corridor_portrait": "Pasillo con retrato",
    "living_room": "Sala con paredes móviles",
    "stairwell": "Escalera interior",
    "locked_door": "Puerta cerrada",
    "bus_exterior": "Autobús exterior",
    "bus_interior": "Interior del autobús",
    "bus_passenger": "Pasajero en penumbra",
    "window_rain": "Ventana con lluvia",
    "empty_seat": "Asiento vacío",
    "ticket_close": "Primer plano del boleto",
    "bedroom_wide": "Dormitorio",
    "bed_edge": "Borde de la cama",
    "closet_door": "Armario entreabierto",
    "underbed_view": "Vista bajo la cama",
    "lamp_shadow": "Sombra de lámpara",
    "bedroom_door": "Puerta del dormitorio",
    "bathroom_wide": "Baño y espejo",
    "mirror_close": "Primer plano del espejo",
    "sink_close": "Lavabo",
    "mirror_message": "Mensaje en el espejo",
    "bathroom_door": "Puerta del baño",
    "mirror_break": "Espejo agrietado",
}

def run(cmd, *, input_text=None, check=True):
    p = subprocess.run(cmd, input=input_text, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError("Comando fallido: " + " ".join(map(str, cmd)) + "\n" + p.stderr[-4000:])
    return p

def ffprobe(path):
    p = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(p.stdout)

def media_duration(path):
    return float(ffprobe(path)["format"]["duration"])

def notify_progress(stage):
    if not os.getenv("MAKE_RESULT_WEBHOOK_URL") or not os.getenv("MAKE_WEBHOOK_API_KEY"):
        return
    try:
        from .notify_make_v4 import send
        send(stage, {"stage": stage})
    except Exception as exc:
        print(f"Make progress callback warning ({stage}): {exc}", file=sys.stderr)

def load_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def validate_request_id(value):
    if not value:
        return str(uuid.uuid4())
    parsed = uuid.UUID(value)
    if str(parsed) != value.lower():
        raise ValueError("request_id debe ser un UUID canónico.")
    return str(parsed)

def get_voice(voice_id):
    if voice_id not in VOICES:
        raise ValueError(f"Voz no permitida: {voice_id}")
    locale, speaker, quality = VOICES[voice_id]
    return {"id": voice_id, "locale": locale, "speaker": speaker, "quality": quality}

def download_voice(voice, work):
    folder = work / "voices" / voice["id"]
    folder.mkdir(parents=True, exist_ok=True)
    model, config = folder / "voice.onnx", folder / "voice.onnx.json"
    base = f'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/{voice["locale"]}/{voice["speaker"]}/{voice["quality"]}/{voice["id"]}'
    for suffix, target in ((".onnx", model), (".onnx.json", config)):
        if not target.exists():
            print(f"Descargando modelo Piper {voice['id']} ({suffix})")
            run(["python", "-c", "import urllib.request,sys; urllib.request.urlretrieve(sys.argv[1],sys.argv[2])", base + suffix, str(target)])
    if model.stat().st_size < 100_000 or config.stat().st_size < 100:
        raise RuntimeError(f"Modelo Piper incompleto: {voice['id']}")
    cfg = json.loads(config.read_text(encoding="utf-8"))
    return model, config, int(cfg.get("audio", {}).get("sample_rate", 22050))

def synthesize(text, voice, out, work, rate=1.0, pitch_semitones=-1.0, intensity="mysterious"):
    model, config, sample_rate = download_voice(voice, work)
    raw = out.with_name(out.stem + "-raw.wav")
    length_scale = max(0.80, min(1.30, 1.0 / rate))
    noise_scale = {"calm": 0.55, "mysterious": 0.68, "urgent": 0.78}[intensity]
    run([
        "piper", "--model", str(model), "--config", str(config),
        "--length_scale", f"{length_scale:.4f}",
        "--noise_scale", f"{noise_scale:.3f}", "--noise_w", "0.78",
        "--output_file", str(raw)
    ], input_text=text)
    ratio = 2 ** (pitch_semitones / 12.0)
    ratio = max(0.90, min(1.12, ratio))
    atempo = 1.0 / ratio
    run([
        "ffmpeg", "-y", "-i", str(raw), "-af",
        f"asetrate={sample_rate}*{ratio:.6f},aresample={sample_rate},atempo={atempo:.6f}",
        "-c:a", "pcm_s16le", str(out)
    ])
    raw.unlink(missing_ok=True)
    return out

def write_silence(path, seconds, sample_rate=22050, channels=1, sample_width=2):
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(sample_width)
        f.setframerate(sample_rate)
        f.writeframes(b"\0" * frames * channels * sample_width)

def concat_wavs(parts, out):
    listing = out.with_suffix(".concat.txt")
    listing.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c:a", "pcm_s16le", str(out)])
    listing.unlink(missing_ok=True)


def allocate_pause_durations(speech_lengths, target_seconds, requested_pause, intensity):
    """Distribute remaining runtime across story boundaries without altering speech speed."""
    if not speech_lengths:
        raise ValueError("Se necesita al menos un segmento de narración.")
    if requested_pause <= 0:
        raise ValueError("requested_pause debe ser positivo.")
    boundary_count = len(speech_lengths) - 1
    available = float(target_seconds) - sum(float(x) for x in speech_lengths)
    if boundary_count == 0:
        if abs(available) > 0.15:
            raise ValueError("No hay límites narrativos suficientes para ajustar la duración.")
        return []
    if available < boundary_count * 0.20:
        raise ValueError(
            f"La voz ocupa {sum(speech_lengths):.3f}s y no deja pausas naturales suficientes "
            f"para alcanzar {target_seconds:.3f}s."
        )
    base_pause = requested_pause * (0.67 if intensity == "urgent" else 1.0)
    base_pause = min(base_pause, available / boundary_count)
    remaining = available - base_pause * boundary_count
    # Longer dramatic holds before the reveal and final beat; shorter between setup beats.
    weights = [1.0, 1.12, 0.92, 1.28, 1.08][:boundary_count]
    if boundary_count > len(weights):
        weights.extend([1.0] * (boundary_count - len(weights)))
    weight_total = sum(weights)
    pauses = [base_pause + remaining * w / weight_total for w in weights]
    pauses[-1] += available - sum(pauses)
    return pauses


def build_scene_durations(speech_lengths, pauses):
    """Map every narration pause to its preceding scene, preserving the full timeline."""
    if len(pauses) != max(0, len(speech_lengths) - 1):
        raise ValueError("Debe existir exactamente una pausa entre cada par de segmentos.")
    return [
        float(length) + (float(pauses[i]) if i < len(pauses) else 0.0)
        for i, length in enumerate(speech_lengths)
    ]

def create_audio_beds(events, starts, total_seconds, sample_rate, music_path, effects_path, intensity):
    count = int(math.ceil(total_seconds * sample_rate))
    rng = random.Random("nexus-v4-audio")
    music = array("h")
    effects = array("h")
    intensity_gain = {"calm": 0.72, "mysterious": 1.0, "urgent": 1.18}[intensity]
    for i in range(count):
        t = i / sample_rate
        fade_in = min(1.0, t / 2.5)
        fade_out = min(1.0, max(0.0, (total_seconds - t) / 3.0))
        envelope = fade_in * fade_out
        pulse = 0.65 + 0.35 * math.sin(2 * math.pi * 0.075 * t)
        pad = (0.45 * math.sin(2 * math.pi * 43.0 * t)
               + 0.20 * math.sin(2 * math.pi * 64.8 * t)
               + 0.12 * math.sin(2 * math.pi * 86.4 * t)
               + 0.06 * math.sin(2 * math.pi * (180 + 4 * math.sin(t * 0.3)) * t))
        wind_noise = rng.uniform(-1.0, 1.0) * 0.035
        m = (pad * 0.040 * pulse + wind_noise) * envelope * intensity_gain
        music.append(max(-32767, min(32767, int(m * 32767))))
        fx = 0.0
        for idx, event in enumerate(events):
            start = starts[idx]
            cue = event["sfx"]
            local = t - start - 0.25
            if cue in ("ring", "mobile") and (0 <= local < 1.15):
                if local < 0.38 or 0.62 <= local < 1.0:
                    env = math.exp(-local * 1.7) if local < 0.38 else math.exp(-(local - 0.62) * 1.7)
                    fx += 0.22 * env * (math.sin(2 * math.pi * 760 * local) + 0.35 * math.sin(2 * math.pi * 1140 * local))
            elif cue in ("impact", "knocks") and 0 <= local < 0.78:
                pulse_at = local % 0.24
                if pulse_at < 0.11:
                    fx += 0.46 * math.exp(-pulse_at * 24) * math.sin(2 * math.pi * 72 * pulse_at)
            elif cue in ("steps", "engine") and 0 <= local < 1.0:
                pulse_at = local % 0.38
                if pulse_at < 0.15:
                    fx += 0.19 * math.exp(-pulse_at * 17) * math.sin(2 * math.pi * 92 * pulse_at)
            elif cue in ("static", "whisper") and 0 <= local < 0.75:
                fx += 0.08 * rng.uniform(-1, 1) * (1 - local / 0.75)
            elif cue in ("scrape", "creak", "glass") and 0 <= local < 0.8:
                fx += 0.12 * rng.uniform(-1, 1) * (1 - local / 0.8) * math.sin(math.pi * local / 0.8)
            elif cue in ("wind", "drip", "water") and 0 <= local < 1.0:
                fx += 0.06 * math.sin(2 * math.pi * 420 * local) * (1 - local)
        effects.append(max(-32767, min(32767, int(fx * intensity_gain * 32767))))
    for path, data in ((music_path, music), (effects_path, effects)):
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            f.writeframes(data.tobytes())

def scene_background(scene, variant):
    im = Image.new("RGB", (BASE_W, BASE_H), (5, 7, 13))
    d = ImageDraw.Draw(im, "RGBA")
    # Layered atmospheric gradient; each set has a different palette and geometry.
    palettes = {
        "phone": ((7, 9, 18), (48, 39, 29)), "stairs": ((6, 9, 18), (47, 47, 57)),
        "hall": ((5, 8, 17), (34, 45, 57)), "house": ((7, 9, 16), (43, 49, 61)),
        "bus": ((5, 10, 17), (40, 49, 55)), "bed": ((8, 7, 15), (54, 35, 37)),
        "bath": ((5, 10, 16), (39, 52, 58)), "object": ((7, 7, 13), (54, 46, 36)),
    }
    family = ("phone" if "phone" in scene or "receiver" in scene or "mobile" in scene or "cable" in scene
              else "stairs" if "stair" in scene else "hall" if "hall" in scene or "corridor" in scene
              else "house" if "house" in scene or "door" in scene or "living" in scene
              else "bus" if "bus" in scene or "ticket" in scene or "seat" in scene or "window" in scene
              else "bed" if "bed" in scene or "closet" in scene or "lamp" in scene
              else "bath" if "bath" in scene or "mirror" in scene or "sink" in scene
              else "object")
    top, bottom = palettes[family]
    for y in range(0, BASE_H, 8):
        mix = y / BASE_H
        color = tuple(int(top[k] * (1-mix) + bottom[k] * mix) for k in range(3))
        d.rectangle((0, y, BASE_W, y+8), fill=(*color, 255))
    # Practical light and depth cues.
    d.ellipse((BASE_W*0.58 + (variant % 5)*7, 80, BASE_W*1.10, 560), fill=(190, 174, 132, 20))
    d.rectangle((35 + (variant % 4)*24, 185, 75 + (variant % 4)*24, 310), fill=(85, 105, 120, 28), outline=(125, 140, 150, 75), width=2)
    d.rectangle((0, BASE_H-170, BASE_W, BASE_H), fill=(3, 4, 8, 210))
    if scene in ("phone_room", "mobile_close"):
        d.polygon([(0, 570), (BASE_W//2, 470), (BASE_W, 570), (BASE_W, BASE_H), (0, BASE_H)], fill=(13, 13, 19, 255))
        d.rectangle((60, 590, 480, 635), fill=(47, 38, 30, 255))
    elif scene == "receiver_close":
        # Intimate tabletop macro: warm wood plane, wall trim and a pool of amber light.
        d.rectangle((0, 0, BASE_W, 610), fill=(19, 16, 15, 255))
        d.rectangle((0, 500, BASE_W, 535), fill=(78, 57, 39, 255))
        d.polygon([(0, 590), (BASE_W, 535), (BASE_W, BASE_H), (0, BASE_H)], fill=(57, 38, 26, 255))
        for x in (80, 220, 360, 500):
            d.line((x, 650, x-55, BASE_H), fill=(91, 61, 39, 180), width=4)
        d.ellipse((260, 80, 590, 420), fill=(210, 155, 87, 24))
    elif scene == "floor_cable":
        # Ground-level hallway perspective: converging floorboards and a deep vanishing point.
        d.rectangle((0, 0, BASE_W, 455), fill=(7, 12, 19, 255))
        d.polygon([(0, 390), (BASE_W, 390), (BASE_W, BASE_H), (0, BASE_H)], fill=(25, 29, 35, 255))
        d.polygon([(0, 390), (BASE_W, 390), (BASE_W, 430), (0, 430)], fill=(66, 59, 49, 255))
        for x in range(-500, 1000, 105):
            d.line((BASE_W//2, 405, x, BASE_H), fill=(67, 66, 62, 210), width=4)
        for y in (540, 680, 830):
            d.line((0, y, BASE_W, y-35), fill=(48, 53, 60, 220), width=3)
        d.polygon([(0, 330), (85, 330), (125, 455), (0, 455)], fill=(13, 17, 23, 255))
        d.polygon([(455, 330), (BASE_W, 330), (BASE_W, 455), (415, 455)], fill=(13, 17, 23, 255))
    if scene == "stairs" or scene == "stairwell":
        for i in range(10):
            y = 280 + i*62
            inset = i*18
            d.polygon([(inset, y), (BASE_W-inset, y), (BASE_W-inset-12, y+20), (inset+12, y+20)], fill=(35-i, 37-i, 45-i, 255), outline=(100, 95, 86, 150))
    if scene in ("hallway", "corridor_portrait", "locked_door", "bathroom_door", "bedroom_door"):
        d.polygon([(65, 0), (475, 0), (390, BASE_H), (150, BASE_H)], fill=(12, 16, 25, 255))
        d.rectangle((195, 180, 345, 730), fill=(25, 27, 34, 255), outline=(110, 100, 84, 220), width=7)
    if scene in ("house_exterior", "front_door"):
        d.polygon([(50, 390), (270, 180), (490, 390)], fill=(4, 5, 10, 255), outline=(110, 110, 120, 220))
        d.rectangle((85, 390, 455, 820), fill=(12, 15, 22, 255), outline=(75, 79, 88, 255), width=8)
        d.rectangle((220, 510, 320, 820), fill=(3, 5, 9, 255), outline=(95, 85, 72, 255), width=5)
        d.rectangle((120, 465, 185, 570), fill=(22, 37, 48, 255))
        d.rectangle((355, 465, 420, 570), fill=(22, 37, 48, 255))
    if scene.startswith("bus"):
        d.polygon([(50, 250), (490, 250), (450, 760), (90, 760)], fill=(14, 20, 26, 255), outline=(100, 110, 115, 255))
        for x in (115, 230, 345):
            d.rectangle((x, 320, x+80, 485), fill=(4, 12, 20, 255), outline=(88, 104, 112, 255), width=4)
    if "bed" in scene or scene in ("closet_door", "underbed_view", "lamp_shadow"):
        d.rectangle((35, 590, 505, 815), fill=(25, 24, 33, 255))
        d.polygon([(50, 610), (470, 610), (520, 770), (15, 770)], fill=(47, 42, 51, 255))
    if "bath" in scene or "mirror" in scene or scene == "sink_close":
        d.rounded_rectangle((125, 130, 415, 730), radius=20, fill=(4, 8, 14, 255), outline=(135, 145, 150, 255), width=10)
        d.rectangle((145, 150, 395, 710), fill=(17, 27, 34, 255))
        d.rectangle((75, 735, 465, 790), fill=(49, 52, 55, 255))
    return im

def draw_character(draw, x, y, scale=1.0, pose="standing", alpha=245):
    r = int(25*scale)
    draw.ellipse((x-r, y-r*2, x+r, y), fill=(1, 2, 5, alpha))
    draw.polygon([(x-r, y-4), (x+r, y-4), (x+int(45*scale), y+int(150*scale)), (x-int(45*scale), y+int(150*scale))], fill=(2, 3, 7, alpha))
    if pose == "walking":
        swing = int(25*scale)
        draw.line((x-8, y+int(120*scale), x-swing, y+int(205*scale)), fill=(2, 3, 7, alpha), width=max(3, int(17*scale)))
        draw.line((x+8, y+int(120*scale), x+swing, y+int(205*scale)), fill=(2, 3, 7, alpha), width=max(3, int(17*scale)))
    else:
        draw.line((x-8, y+int(120*scale), x-18, y+int(205*scale)), fill=(2, 3, 7, alpha), width=max(3, int(17*scale)))
        draw.line((x+8, y+int(120*scale), x+18, y+int(205*scale)), fill=(2, 3, 7, alpha), width=max(3, int(17*scale)))

def render_frame(event, t, frame_no, total_frames, seed):
    scene = event["scene"]
    im = scene_background(scene, seed).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    phase = t * 2 * math.pi
    # Event-specific foreground action; no single scene plate is reused.
    if event["action"] == "phone_ring":
        # Wide establishing composition: a heavy tabletop landline in a lived-in room.
        im = Image.new("RGBA", (BASE_W, BASE_H), (7, 8, 13, 255))
        ld = ImageDraw.Draw(im, "RGBA")
        for y in range(BASE_H):
            shade = int(12 + 25*y/BASE_H)
            ld.line((0, y, BASE_W, y), fill=(shade, shade-2, shade-1, 255))
        # Wall panels, a dim practical lamp and a strong horizontal desk plane.
        ld.rectangle((35, 90, 505, 535), fill=(19, 17, 19, 255), outline=(74, 62, 49, 255), width=5)
        ld.rectangle((58, 118, 482, 500), outline=(43, 39, 38, 255), width=3)
        ld.ellipse((330, 85, 560, 315), fill=(206, 157, 92, 28))
        ld.line((0, 600, BASE_W, 505), fill=(119, 91, 61, 180), width=8)
        ld.polygon([(0, 625), (BASE_W, 535), (BASE_W, BASE_H), (0, BASE_H)], fill=(42, 27, 20, 255))
        for y in (690, 790, 900):
            ld.line((0, y, BASE_W, y-85), fill=(88, 57, 37, 170), width=4)
        # Broad, horizontal base with a real cradle, keypad and separate handset.
        wobble = int(5 * math.sin(phase * 5))
        ld.ellipse((45, 690, 500, 870), fill=(0, 0, 0, 100))
        ld.rounded_rectangle((70+wobble, 590, 465+wobble, 810), radius=34,
                             fill=(27, 28, 29, 255), outline=(174, 143, 103, 255), width=9)
        ld.polygon([(100+wobble, 625), (430+wobble, 625), (410+wobble, 770), (120+wobble, 770)],
                   fill=(42, 43, 42, 255), outline=(103, 91, 76, 255))
        for row in range(3):
            for col in range(4):
                x, y = 180+col*35+wobble, 660+row*31
                ld.ellipse((x, y, x+19, y+19), fill=(7, 8, 9, 255), outline=(132, 122, 106, 255), width=2)
        # Handset is visibly separate from the base and connected by a coiled cord.
        hx = 265 + wobble
        ld.rounded_rectangle((hx-155, 530, hx+155, 605), radius=35,
                             fill=(18, 19, 20, 255), outline=(190, 164, 124, 255), width=8)
        ld.ellipse((hx-170, 535, hx-115, 600), fill=(10, 11, 12, 255), outline=(170, 145, 111, 255), width=6)
        ld.ellipse((hx+115, 535, hx+170, 600), fill=(10, 11, 12, 255), outline=(170, 145, 111, 255), width=6)
        cord = [(420, 595), (450, 610), (430, 628), (458, 646), (438, 664), (463, 682), (440, 700)]
        ld.line(cord, fill=(190, 169, 133, 255), width=5)
        ld.ellipse((35, 160, 95, 220), fill=(224, 174, 100, int(35+25*abs(math.sin(phase*2)))))
        # A subtle shadow anchors the apparatus to the room rather than floating.
    elif event["action"] == "screen_call":
        # Contrasting close-up: handheld smartphone at a diagonal, cold screen light,
        # shallow-focus night window and no desk/landline geometry.
        im = Image.new("RGBA", (BASE_W, BASE_H), (3, 8, 18, 255))
        md = ImageDraw.Draw(im, "RGBA")
        for y in range(BASE_H):
            glow = int(5 + 22*(1-y/BASE_H))
            md.line((0, y, BASE_W, y), fill=(glow//2, glow, glow+12, 255))
        # Night window in deep perspective; rain streaks and distant lights.
        md.polygon([(0, 0), (BASE_W, 0), (BASE_W, 560), (0, 760)], fill=(5, 17, 32, 255))
        md.line((35, 0, 115, 690), fill=(72, 104, 132, 130), width=7)
        md.line((310, 0, 250, 650), fill=(72, 104, 132, 100), width=5)
        for k in range(18):
            x = (k*83 + 29) % BASE_W
            y = (k*47 + 80) % 560
            md.ellipse((x, y, x+8, y+8), fill=(124, 170, 205, 90))
        # A hand/forearm silhouette enters from the lower edge holding the device.
        md.polygon([(120, BASE_H), (220, 735), (360, 690), (470, BASE_H)], fill=(13, 16, 23, 255))
        # Draw the smartphone and its interface on a transparent layer, then rotate
        # the whole device to create a clear oblique perspective.
        device = Image.new("RGBA", (300, 560), (0, 0, 0, 0))
        sd = ImageDraw.Draw(device, "RGBA")
        sd.rounded_rectangle((28, 18, 272, 540), radius=38, fill=(1, 3, 8, 255),
                             outline=(154, 177, 195, 255), width=10)
        sd.rounded_rectangle((45, 42, 255, 516), radius=25, fill=(13, 35, 57, 255),
                             outline=(73, 119, 153, 255), width=3)
        sd.ellipse((116, 100, 184, 168), fill=(105, 150, 180, 255))
        sd.ellipse((128, 110, 172, 154), fill=(28, 48, 69, 255))
        sd.rounded_rectangle((83, 190, 217, 207), radius=8, fill=(226, 237, 244, 245))
        sd.rounded_rectangle((103, 220, 197, 231), radius=5, fill=(147, 181, 202, 220))
        sd.text((87, 270), "LLAMADA", font=load_font(17), fill=(223, 235, 244, 255))
        sd.text((96, 296), "ENTRANTE", font=load_font(15), fill=(155, 187, 210, 255))
        sd.ellipse((68, 405, 132, 469), fill=(44, 190, 112, 255))
        sd.ellipse((168, 405, 232, 469), fill=(206, 62, 72, 255))
        # handset glyphs inside the accept/reject controls
        sd.arc((84, 419, 116, 451), 190, 345, fill=(255, 255, 255, 255), width=6)
        sd.arc((184, 419, 216, 451), 195, 350, fill=(255, 255, 255, 255), width=6)
        rotated = device.rotate(-13 + 1.8*math.sin(phase*3), resample=Image.Resampling.BICUBIC, expand=True)
        # Screen glow is rendered as a blurred light layer behind the actual phone.
        glow_layer = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer, "RGBA")
        gd.ellipse((80, 390, 520, 1120), fill=(50, 145, 210, 72))
        im = Image.alpha_composite(im, glow_layer.filter(ImageFilter.GaussianBlur(62)))
        im.alpha_composite(rotated, (115, 335))
        md = ImageDraw.Draw(im, "RGBA")
        md.line((80, 180, 55, 520), fill=(160, 200, 225, 90), width=4)
        md.line((470, 120, 415, 570), fill=(160, 200, 225, 70), width=3)
    elif event["action"] in ("walk_down", "figure_descend", "shadow_approach", "passenger_turn"):
        x = int(265 + 26*math.sin(phase))
        draw_character(d, x, 430 + int(10*math.sin(phase*2)), 0.95, "walking")
        d.ellipse((x-75, 650, x+75, 700), fill=(140, 150, 165, 18))
    elif event["action"] == "receiver_lift":
        # Extreme close-up of the vintage handset, diagonal across the frame.
        # Seed-driven framing variants make a retry alter the actual composition.
        variant = seed % 3
        dx = (-34, 0, 34)[variant]
        bob = int(7 * math.sin(phase * 2))
        # Deep, defocused room behind a narrow strip of amber tabletop.
        d.rectangle((0, 0, BASE_W, 520), fill=(12, 11, 15, 255))
        d.ellipse((245+dx, 100, 600+dx, 510), fill=(185, 130, 75, 22))
        d.polygon([(0, 585), (BASE_W, 540), (BASE_W, BASE_H), (0, BASE_H)], fill=(54, 35, 24, 255))
        # Ear cup and mouth cup are distinct oversized forms, joined by a curved grip.
        handset = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(handset, "RGBA")
        hd.line([(80+dx, 275+bob), (170+dx, 330+bob), (275+dx, 405+bob),
                 (375+dx, 480+bob), (455+dx, 545+bob)], fill=(8, 9, 11, 255), width=72)
        hd.line([(80+dx, 275+bob), (170+dx, 330+bob), (275+dx, 405+bob),
                 (375+dx, 480+bob), (455+dx, 545+bob)], fill=(92, 88, 82, 255), width=56)
        hd.ellipse((15+dx, 205+bob, 155+dx, 345+bob), fill=(15, 17, 19, 255),
                   outline=(190, 158, 116, 255), width=9)
        hd.ellipse((370+dx, 475+bob, 510+dx, 615+bob), fill=(12, 14, 16, 255),
                   outline=(190, 158, 116, 255), width=9)
        hd.ellipse((42+dx, 232+bob, 128+dx, 318+bob), fill=(3, 5, 7, 255))
        hd.ellipse((397+dx, 502+bob, 483+dx, 588+bob), fill=(3, 5, 7, 255))
        # Visible perforations, metal seam and coiled cord anchor the object in the shot.
        for k in range(9):
            px = 56+dx+(k%3)*23
            py = 247+bob+(k//3)*23
            hd.ellipse((px, py, px+7, py+7), fill=(112, 119, 121, 210))
        hd.arc((115+dx, 280+bob, 355+dx, 500+bob), 15, 165, fill=(210, 187, 150, 220), width=4)
        hd.line([(440+dx, 560+bob), (485+dx, 605), (465+dx, 650),
                 (500+dx, 690), (475+dx, 730)], fill=(183, 157, 119, 255), width=5)
        im = Image.alpha_composite(im, handset)
        d = ImageDraw.Draw(im, "RGBA")
    elif event["action"] in ("shadow_cross", "shadow_stretch", "portrait_turn", "eyes_blink"):
        x = int(-110 + (BASE_W+220)*t)
        d.ellipse((x, 260, x+88, 360), fill=(0, 0, 0, 245))
        d.polygon([(x+18, 350), (x+72, 350), (x+150, 850), (x-65, 850)], fill=(0, 0, 0, 245))
    elif event["action"] == "cable_crawl":
        # Low floor-level tracking shot: a long cable snakes from the distant doorway
        # into the extreme foreground, with perspective-scaled width and a moving tip.
        variant = seed % 3
        offset = (-42, 0, 42)[variant]
        d.rectangle((0, 0, BASE_W, 430), fill=(6, 10, 17, 255))
        d.polygon([(0, 350), (BASE_W, 350), (BASE_W, BASE_H), (0, BASE_H)], fill=(24, 28, 34, 255))
        # Baseboards and a door threshold establish a recognizable hallway.
        d.polygon([(0, 300), (92, 300), (135, 440), (0, 440)], fill=(12, 16, 22, 255))
        d.polygon([(448, 300), (BASE_W, 300), (BASE_W, 440), (405, 440)], fill=(12, 16, 22, 255))
        d.line((0, 432, BASE_W//2, 390), fill=(107, 86, 62, 255), width=13)
        d.line((BASE_W//2, 390, BASE_W, 432), fill=(107, 86, 62, 255), width=13)
        # Perspective floor seams converge toward the hallway's vanishing point.
        for x in range(-420, 1000, 115):
            d.line((BASE_W//2, 405, x, BASE_H), fill=(72, 75, 78, 200), width=3)
        # Cable path uses a large perspective curve rather than a short horizontal stroke.
        pts = []
        for k in range(18):
            u = k / 17
            x = int(BASE_W/2 + offset + (u-0.5)*360 + 65*math.sin(u*math.pi*2 + phase*0.7))
            y = int(405 + u*520 + 18*math.sin(u*math.pi*3 + phase*2))
            pts.append((x, y))
        for k in range(len(pts)-1):
            width = int(3 + 13*(k/(len(pts)-1)))
            d.line((pts[k], pts[k+1]), fill=(3, 4, 6, 255), width=width+5)
            d.line((pts[k], pts[k+1]), fill=(177, 154, 119, 255), width=width)
        # Plug/connector lies near the distant vanishing point.
        tip_x, tip_y = pts[0]
        d.rounded_rectangle((tip_x-12, tip_y-18, tip_x+12, tip_y+18), radius=5,
                            fill=(18, 19, 20, 255), outline=(197, 175, 137, 255), width=3)
    elif event["action"] in ("door_open", "door_creep", "handle_turn", "handle_rattle"):
        angle = int(38 + 15*math.sin(phase*2))
        d.polygon([(220, 200), (330, 210), (330+angle, 740), (220+angle, 735)], fill=(25, 23, 22, 255), outline=(140, 125, 100, 255))
        d.ellipse((300+angle, 450, 318+angle, 468), fill=(180, 150, 100, 255))
    elif event["action"] in ("bus_approach", "lights_flicker", "rain_run", "ticket_reveal"):
        x = int(30 + 100*math.sin(phase))
        d.rectangle((130+x, 320, 410+x, 600), fill=(7, 16, 24, 255), outline=(140, 150, 155, 255), width=6)
        d.rectangle((150+x, 345, 260+x, 475), fill=(30, 50, 62, 255))
        d.rectangle((280+x, 345, 390+x, 475), fill=(30, 50, 62, 255))
    elif event["action"] in ("wall_breathe", "lamp_flicker", "window_flicker", "mirror_delay"):
        glow = int(35 + 80*abs(math.sin(phase*3)))
        d.ellipse((170, 260, 370, 470), fill=(190, 205, 220, glow))
        d.rectangle((195, 490, 345, 510), fill=(180, 195, 210, glow//2))
    elif event["action"] in ("mirror_message", "writing_appear", "mirror_break", "glass_crack"):
        d.line((180, 360, 360, 360+int(15*math.sin(phase))), fill=(210, 215, 220, 220), width=5)
        d.line((270, 250, 250+int(12*math.sin(phase)), 650), fill=(180, 195, 205, 180), width=3)
        if event["action"] in ("mirror_message", "writing_appear"):
            d.text((180, 520), "SAL DE AQUÍ", font=load_font(20), fill=(225, 230, 230, 220))
    else:
        draw_character(d, int(270+20*math.sin(phase)), 440, 0.9)
    # Rebind the drawing context because phone shots replace the background image.
    d = ImageDraw.Draw(im, "RGBA")
    # A practical light flickers with the beat, while atmospheric layers drift continuously.
    flicker = 0.70 + 0.30 * abs(math.sin(frame_no * 0.23))
    d.ellipse((385, 90, 510, 215), fill=(210, 190, 145, int(18+45*flicker)))
    fog = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog, "RGBA")
    for k in range(8):
        x = int((k*92 + frame_no*(1.0 + k*0.08)) % (BASE_W+230)) - 115
        y = 690 + k*27 + int(14*math.sin(phase+k))
        fd.ellipse((x, y, x+230, y+55), fill=(165, 178, 190, 18))
    for k in range(34):
        x = (k*61 + frame_no*(1+k%3)) % BASE_W
        y = (k*137 + frame_no*2) % BASE_H
        fd.ellipse((x, y, x+2, y+2), fill=(220, 225, 230, 100))
    im = Image.alpha_composite(im, fog.filter(ImageFilter.GaussianBlur(11)))
    # Scene transition is event-defined and visibly different from a simple camera zoom.
    if event["transition"] in ("flash", "impact") and frame_no < 5:
        alpha = int(180 * (1-frame_no/5))
        im = Image.alpha_composite(im, Image.new("RGBA", (BASE_W, BASE_H), (235, 232, 220, alpha)))
    elif event["transition"] == "dissolve" and frame_no < 8:
        alpha = int(180 * (1-frame_no/8))
        im = Image.alpha_composite(im, Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, alpha)))
    elif event["transition"] == "whip" and frame_no > total_frames-7:
        streak = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(streak, "RGBA")
        for k in range(15):
            y = k*68
            sd.line((0, y, BASE_W, y-90), fill=(200, 210, 220, 40), width=6)
        im = Image.alpha_composite(im, streak)
    # Short handheld impact, independent of the slow dolly/pan path.
    if event["transition"] == "impact" and frame_no % 24 < 3:
        dx = random.Random(seed+frame_no).randint(-7, 7)
        dy = random.Random(seed-frame_no).randint(-6, 6)
        shifted = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 255))
        shifted.alpha_composite(im, (dx, dy))
        im = shifted
    # Slow camera push-in and pan; subject animation remains visible within the shot.
    zoom = 1.015 + 0.035*t
    sw, sh = int(BASE_W*zoom), int(BASE_H*zoom)
    enlarged = im.resize((sw, sh), Image.Resampling.LANCZOS)
    max_x, max_y = sw-BASE_W, sh-BASE_H
    left = max(0, min(max_x, int(max_x*(0.5+0.35*math.sin(phase*0.22)))))
    top = max(0, min(max_y, int(max_y*(0.5+0.30*math.cos(phase*0.18)))))
    return enlarged.crop((left, top, left+BASE_W, top+BASE_H)).convert("RGB")

def image_difference(a, b):
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    return sum(ImageStat.Stat(diff).mean) / 3.0

def render_scene(event, seconds, work, index, variant_offset=0):
    frame_count = max(45, int(math.ceil(seconds*RENDER_FPS)))
    scene_dir = work / f"scene-{index:02d}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    accepted = None
    score = 0.0
    retries = 0
    for attempt in range(3):
        for old in scene_dir.glob("frame-*.jpg"):
            old.unlink()
        seed = 7019 + index*997 + attempt*137 + variant_offset*1009
        for n in range(frame_count):
            frame = render_frame(event, n/max(1, frame_count-1), n, frame_count, seed)
            frame.save(scene_dir/f"frame-{n:04d}.jpg", quality=88)
        first = Image.open(scene_dir/"frame-0000.jpg").convert("RGB")
        middle = Image.open(scene_dir/f"frame-{frame_count//2:04d}.jpg").convert("RGB")
        score = image_difference(first, middle)
        if score >= 1.25:
            accepted = (first, middle)
            retries = attempt
            break
    if accepted is None:
        raise RuntimeError(f"Escena {event['event_id']} no mostró movimiento perceptible tras 3 intentos (score={score:.3f}).")
    clip = work / f"scene-{index:02d}.mp4"
    run(["ffmpeg", "-y", "-framerate", str(RENDER_FPS), "-i", str(scene_dir/"frame-%04d.jpg"),
         "-vf", "fps=30,scale=1080:1920:flags=lanczos,format=yuv420p", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", "30", str(clip)])
    # Compare the representative action at mid-shot, not the opening frame.
    # Some actions (e.g. a shadow crossing) are intentionally off-screen at t=0.
    return clip, accepted[1], {"event_id": event["event_id"], "scene": event["scene"],
        "scene_label": SCENE_NAMES.get(event["scene"], event["scene"]), "mean_frame_difference": round(score, 3),
        "diversity_sample": "midpoint", "frames_checked": frame_count,
        "retry_count": retries, "diversity_regeneration_count": 0}

def write_subtitles(events, starts, lengths, path):
    def ts(v):
        cs = max(0, int(v*100))
        h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
        return f"{h}:{m:02}:{s:02}.{cs:02}"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,DejaVu Sans,38,&H00F5F3F0,&H000000FF,&HCC000000,&H66000000,0,0,0,0,100,100,0,0,1,2.4,1.4,2,110,110,155,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [header]
    for event, start, length in zip(events, starts, lengths):
        chunks = textwrap.wrap(event["text"], width=44, break_long_words=False, break_on_hyphens=False)
        if len(chunks) > 2:
            words = event["text"].split()
            midpoint = max(1, len(words)//2)
            chunks = [" ".join(words[:midpoint]), " ".join(words[midpoint:])]
        caption = r"\N".join(chunks[:2])
        lines.append(f"Dialogue: 0,{ts(start)},{ts(start+length)},Default,,0,0,0,,{caption}\n")
    path.write_text("".join(lines), encoding="utf-8")

def write_reports(out, story, events, scene_metrics, first_frames, starts, lengths, mp4, narration, audio_mix, request):
    pairwise = []
    for i in range(len(first_frames)):
        for j in range(i+1, len(first_frames)):
            pairwise.append({"scene_a": events[i]["scene"], "scene_b": events[j]["scene"],
                             "mean_image_difference": round(image_difference(first_frames[i], first_frames[j]), 3)})
    motion_pass = all(x["mean_frame_difference"] >= 1.25 for x in scene_metrics)
    diversity_pass = all(x["mean_image_difference"] >= 7.0 for x in pairwise)
    report = {
        "motion_threshold": 1.25, "scene_diversity_threshold": 7.0,
        "motion_pass": motion_pass, "scene_diversity_pass": diversity_pass,
        "scene_metrics": scene_metrics, "pairwise_scene_comparison": pairwise,
        "scene_count": len(events), "regeneration_limit_per_scene": 2,
        "note": "Las métricas comparan fotogramas renderizados; la aprobación estética final requiere revisión humana."
    }
    (out/"motion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    probe = ffprobe(mp4)
    video = next((s for s in probe["streams"] if s.get("codec_type") == "video"), {})
    audio = next((s for s in probe["streams"] if s.get("codec_type") == "audio"), {})
    duration = float(probe["format"]["duration"])
    render_report = {
        "valid": bool(video and audio and video.get("codec_name") == "h264" and audio.get("codec_name") == "aac"
                      and video.get("width") == W and video.get("height") == H
                      and video.get("r_frame_rate") == "30/1" and 30 <= duration <= 60
                      and abs(duration-request["duration_target"]) <= 0.15
                      and abs(media_duration(narration)-request["duration_target"]) <= 0.15
                      and abs(duration-media_duration(audio_mix)) <= 0.15
                      and motion_pass and diversity_pass),
        "duration_seconds": round(duration, 3), "width": video.get("width"), "height": video.get("height"),
        "fps": video.get("r_frame_rate"), "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"), "pixel_format": video.get("pix_fmt"),
        "video_size_bytes": mp4.stat().st_size, "narration_duration_seconds": round(media_duration(narration), 3),
        "audio_mix_duration_seconds": round(media_duration(audio_mix), 3),
        "audio_video_duration_delta_seconds": round(abs(duration-media_duration(audio_mix)), 3),
        "requested_duration_seconds": request["duration_target"],
        "scene_timeline_duration_seconds": round(scene_timeline_total, 3),
        "duration_error_seconds": round(abs(duration-request["duration_target"]), 3),
        "narration_file": narration.name, "audio_mix_file": audio_mix.name,
        "ffprobe_format": probe.get("format", {}).get("format_name"),
    }
    (out/"render_report.json").write_text(json.dumps(render_report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not render_report["valid"]:
        raise RuntimeError("El MP4 no superó todos los criterios técnicos y visuales; revisa render_report.json y motion_report.json.")
    metadata = {
        "schema_version": "1.0", "project": "NEXUS VIDEO AI", "version": "V4",
        "request_id": request["request_id"], "status": "rendered",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "category": story["category"], "genre": story["genre"], "title": story["title"],
        "protagonist": story["protagonist"], "generation_method": story["generation_method"],
        "events": [{"event_id": e["event_id"], "scene": e["scene"], "action": e["action"], "sfx": e["sfx"],
                    "start_seconds": round(starts[i], 3), "duration_seconds": round(lengths[i], 3),
                    "text": e["text"]} for i, e in enumerate(events)],
        "voice": request["voice"], "voice_rate": request["voice_rate"],
        "pitch_semitones": request["pitch_semitones"], "voice_volume": request["voice_volume"],
        "pause_seconds": request["pause_seconds"], "duration_target_seconds": request["duration_target"],
        "duration_error_seconds": round(abs(duration-request["duration_target"]), 3),
        "narration_intensity": request["intensity"],
        "duration_seconds": round(duration, 3), "width": W, "height": H, "fps": FPS,
        "video_codec": "h264", "audio_codec": "aac", "scene_count": len(events),
        "scene_diversity_verified": diversity_pass, "motion_verified": motion_pass,
        "files": {"video": mp4.name, "narration": narration.name, "audio_mix": audio_mix.name,
                  "story": "historia.txt", "script": "script.txt", "motion_report": "motion_report.json",
                  "render_report": "render_report.json", "thumbnail": "thumbnail.jpg"},
        "social_publishing": False, "make_status": "pending_callback", "drive_status": "pending"
    }
    (out/"metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata

def main():
    for tool in ("ffmpeg", "ffprobe", "piper"):
        if not shutil.which(tool):
            raise RuntimeError(f"No se encontró {tool} en PATH.")
    request_id = validate_request_id(os.getenv("REQUEST_ID", ""))
    out = OUT_ROOT / request_id
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"request_id ya existe y no se sobrescribe: {request_id}. Para reintentar Drive usa operation=upload_only.")
    out.mkdir(parents=True, exist_ok=True)
    work = WORK_ROOT / request_id
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    request = {
        "request_id": request_id,
        "category": os.getenv("CATEGORY", "paranormal"),
        "duration_target": int(os.getenv("DURATION_SECONDS", "45")),
        "voice": os.getenv("PIPER_VOICE", "es_MX-claude-high"),
        "voice_rate": float(os.getenv("VOICE_RATE", "1.0")),
        "pitch_semitones": float(os.getenv("PITCH_SEMITONES", "-1.0")),
        "voice_volume": float(os.getenv("VOICE_VOLUME", "1.0")),
        "pause_seconds": float(os.getenv("PAUSE_SECONDS", "0.78")),
        "intensity": os.getenv("NARRATION_INTENSITY", "mysterious"),
        "voice_auditions": os.getenv("VOICE_AUDITIONS", "false").lower() == "true"
    }
    (out/"errors").mkdir(exist_ok=True)
    try:
        if not 30 <= request["duration_target"] <= 60:
            raise ValueError("duration_seconds debe estar entre 30 y 60.")
        if not 0.75 <= request["voice_rate"] <= 1.25:
            raise ValueError("voice_rate debe estar entre 0.75 y 1.25.")
        if not -2.0 <= request["pitch_semitones"] <= 2.0:
            raise ValueError("pitch_semitones debe estar entre -2 y 2.")
        if not 0.5 <= request["voice_volume"] <= 1.5:
            raise ValueError("voice_volume debe estar entre 0.5 y 1.5.")
        if not 0.2 <= request["pause_seconds"] <= 1.5:
            raise ValueError("pause_seconds debe estar entre 0.2 y 1.5.")
        if request["intensity"] not in ("calm", "mysterious", "urgent"):
            raise ValueError("narration_intensity no válido.")
        voice = get_voice(request["voice"])
    except Exception as exc:
        (out/"errors"/"render_error.log").write_text(
            f"{datetime.now(timezone.utc).isoformat()}\n{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise
    story = generate_story(request["category"], request_id)
    (out/"story.txt").write_text(story["script"], encoding="utf-8")
    (out/"historia.txt").write_text(story["script"], encoding="utf-8")
    (out/"script.txt").write_text("\n".join(e["text"] for e in story["events"]), encoding="utf-8")
    (out/"story_events.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    (out/"errors").mkdir(exist_ok=True)
    notify_progress("story_created")
    try:
        notify_progress("narrating")
        if request["voice_auditions"]:
            sample_dir = out/"audios"/"voice_samples"
            sample_dir.mkdir(parents=True, exist_ok=True)
            for voice_id in VOICES:
                audition_voice = get_voice(voice_id)
                synthesize(SAMPLE_TEXT, audition_voice, sample_dir/f"{voice_id}.wav", work,
                           request["voice_rate"], request["pitch_semitones"], request["intensity"])
        narration_dir = out/"audios"
        narration_dir.mkdir(exist_ok=True)
        speech_parts, lengths = [], []
        for i, event in enumerate(story["events"]):
            wav = work/f"speech-{i:02d}.wav"
            synthesize(event["text"], voice, wav, work, request["voice_rate"],
                       request["pitch_semitones"], request["intensity"])
            speech_parts.append(wav)
            lengths.append(media_duration(wav))
        pauses = allocate_pause_durations(
            lengths, request["duration_target"], request["pause_seconds"], request["intensity"]
        )
        with wave.open(str(speech_parts[0]), "rb") as f:
            sample_rate, channels, sample_width = f.getframerate(), f.getnchannels(), f.getsampwidth()
        audio_parts = []
        starts, cursor = [], 0.0
        for i, part in enumerate(speech_parts):
            starts.append(cursor)
            audio_parts.append(part)
            cursor += lengths[i]
            if i < len(speech_parts)-1:
                silence = work/f"pause-{i:02d}.wav"
                write_silence(silence, pauses[i], sample_rate, channels, sample_width)
                audio_parts.append(silence)
                cursor += pauses[i]
        narration = narration_dir/"narration.wav"
        concat_wavs(audio_parts, narration)
        total = media_duration(narration)
        if abs(total - request["duration_target"]) > 0.15:
            raise RuntimeError(f"La narración quedó en {total:.3f}s; objetivo {request['duration_target']}s (tolerancia 0.15s).")
        lengths_for_captions = [lengths[i] for i in range(len(lengths))]
        notify_progress("scenes_rendering")
        clips, first_frames, scene_metrics = [], [], []
        scene_durations = build_scene_durations(lengths, pauses)
        scene_timeline_total = sum(scene_durations)
        if abs(scene_timeline_total - total) > 0.15:
            raise RuntimeError(
                f"La línea temporal visual suma {scene_timeline_total:.3f}s, "
                f"pero la narración suma {total:.3f}s."
            )
        for i, event in enumerate(story["events"]):
            clip, first, metric = render_scene(event, scene_durations[i], work, i)
            clips.append(clip)
            first_frames.append(first)
            scene_metrics.append(metric)
        pair_diffs = [image_difference(first_frames[i], first_frames[j])
                      for i in range(len(first_frames)) for j in range(i+1, len(first_frames))]
        # Limited visual-regeneration pass: vary the composition seed for the weaker member of any pair.
        for diversity_attempt in range(1, 3):
            weak_pairs = [(i, j) for i in range(len(first_frames)) for j in range(i+1, len(first_frames))
                          if image_difference(first_frames[i], first_frames[j]) < 7.0]
            if not weak_pairs:
                break
            weak_index = weak_pairs[0][1]
            clips[weak_index], first_frames[weak_index], scene_metrics[weak_index] = render_scene(
                story["events"][weak_index], lengths[weak_index]+(pauses[weak_index] if weak_index < len(pauses)-1 else 0),
                work, weak_index, variant_offset=diversity_attempt)
            scene_metrics[weak_index]["diversity_regeneration_count"] = diversity_attempt
        pair_diffs = [image_difference(first_frames[i], first_frames[j])
                      for i in range(len(first_frames)) for j in range(i+1, len(first_frames))]
        if any(v < 7.0 for v in pair_diffs):
            weak = []
            for i in range(len(first_frames)):
                for j in range(i+1, len(first_frames)):
                    score = image_difference(first_frames[i], first_frames[j])
                    if score < 7.0:
                        weak.append(f"{story['events'][i]['scene']} vs {story['events'][j]['scene']}={score:.3f}")
            raise RuntimeError(
                "La diversidad visual entre fotogramas representativos siguió por debajo de 7.0 "
                "tras 2 regeneraciones; render detenido. Pares: " + "; ".join(weak)
            )
        concat_file = work/"video-scenes.txt"
        concat_file.write_text("".join(f"file '{p.resolve()}'\n" for p in clips), encoding="utf-8")
        silent_video = work/"silent-video.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", str(silent_video)])
        subtitles = work/"captions.ass"
        write_subtitles(story["events"], starts, lengths_for_captions, subtitles)
        music, effects = narration_dir/"music.wav", narration_dir/"effects.wav"
        create_audio_beds(story["events"], starts, total, sample_rate, music, effects, request["intensity"])
        notify_progress("audio_mixing")
        audio_mix = narration_dir/"audio_mix.wav"
        mix_filter = f"[0:a]highpass=f=70,lowpass=f=11500,acompressor=threshold=0.12:ratio=2.1:attack=18:release=180,volume={request['voice_volume']:.3f}[voice];[1:a]volume=0.34[music0];[music0][voice]sidechaincompress=threshold=0.025:ratio=5:attack=25:release=420[music];[2:a]volume=0.55[fx];[voice][music][fx]amix=inputs=3:duration=first:weights='1 0.28 0.42',loudnorm=I=-16:TP=-1.5:LRA=10[mix]"
        run(["ffmpeg", "-y", "-i", str(narration), "-i", str(music), "-i", str(effects),
             "-filter_complex", mix_filter, "-map", "[mix]", "-c:a", "pcm_s16le", str(audio_mix)])
        video_dir = out/"videos"
        video_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        mp4 = video_dir/f"nexus-v4-{stamp}.mp4"
        run(["ffmpeg", "-y", "-i", str(silent_video), "-i", str(audio_mix),
             "-vf", f"subtitles={subtitles}:fontsdir=/usr/share/fonts/truetype/dejavu,format=yuv420p",
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
             "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
             "-movflags", "+faststart", "-shortest", str(mp4)])
        first_frames[0].save(out/"thumbnail.jpg", quality=92)
        report_dir = out/"reports"
        report_dir.mkdir(exist_ok=True)
        # Write the formal reports under the requested folder and retain a root metadata file.
        metadata = write_reports(report_dir, story, story["events"], scene_metrics, first_frames,
                                 starts, lengths, mp4, narration, audio_mix, request)
        (report_dir/"metadata.json").unlink(missing_ok=True)
        # Normalize report paths for Drive and artifact consumers.
        (out/"motion_report.json").write_text((report_dir/"motion_report.json").read_text(encoding="utf-8"), encoding="utf-8")
        (out/"render_report.json").write_text((report_dir/"render_report.json").read_text(encoding="utf-8"), encoding="utf-8")
        metadata["files"]["video"] = str(mp4.relative_to(out))
        metadata["files"]["narration"] = str(narration.relative_to(out))
        metadata["files"]["audio_mix"] = str(audio_mix.relative_to(out))
        (out/"metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        notify_progress("rendered")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        print(f"V4_RENDER_OK request_id={request_id} duration={metadata['duration_seconds']}")
    except Exception as exc:
        error_file = out/"errors"/"render_error.log"
        error_file.parent.mkdir(parents=True, exist_ok=True)
        error_file.write_text(f"{datetime.now(timezone.utc).isoformat()}\n{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise

if __name__ == "__main__":
    main()
