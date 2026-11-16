from __future__ import annotations

import math
from PIL import Image, ImageDraw, ImageFilter


def _light_layer(size, center, radius, color, strength, blur):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    x, y = center
    rx, ry = radius
    draw.ellipse((x-rx, y-ry, x+rx, y+ry), fill=(*color, max(0, min(255, int(strength)))))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def cinematic_finish(image, event, t, frame_no, total_frames, seed):
    """Add deterministic, layered 2D cinematic lighting, depth haze and moving atmosphere."""
    im = image.convert("RGBA")
    w, h = im.size
    action = event.get("action", "")
    scene = event.get("scene", "")
    tension = 0.5 + 0.5 * math.sin(math.pi * max(0.0, min(1.0, t)))
    pulse = 0.78 + 0.22 * math.sin(frame_no * (0.11 if action not in ("shadow_cross", "shadow_approach") else 0.19))
    cold = scene in ("stairs", "hallway", "floor_cable", "mobile_close") or "mirror" in scene
    key_color = (105, 155, 205) if cold else (226, 163, 91)
    key_x = int(w * (0.73 if action not in ("walk_down", "figure_descend") else 0.50))
    key_y = int(h * (0.27 + 0.035 * math.sin(t * math.pi * 2)))
    # Localized key light and a weaker, differently colored rim light.
    im = Image.alpha_composite(im, _light_layer(
        (w, h), (key_x, key_y), (int(w*0.60), int(h*0.38)),
        key_color, 28 + 24*pulse + 16*tension, 72))
    im = Image.alpha_composite(im, _light_layer(
        (w, h), (int(w*0.08), int(h*0.55)), (int(w*0.34), int(h*0.24)),
        (75, 105, 145), 16 + 12*(1-tension), 58))

    # Soft volumetric shafts, displaced over time to imply a real light source in space.
    beams = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beams, "RGBA")
    drift = int(18 * math.sin(t * math.pi * 2))
    beam_alpha = int(17 + 17*pulse)
    bd.polygon([(int(w*.62)+drift, 0), (int(w*.72)+drift, 0),
                (int(w*.48)+drift, int(h*.72)), (int(w*.39)+drift, int(h*.72))],
               fill=(*key_color, beam_alpha))
    bd.polygon([(int(w*.84)-drift, 0), (int(w*.91)-drift, 0),
                (int(w*.62)-drift, int(h*.58)), (int(w*.56)-drift, int(h*.58))],
               fill=(185, 205, 220, int(beam_alpha*.55)))
    im = Image.alpha_composite(im, beams.filter(ImageFilter.GaussianBlur(28)))

    # Three atmospheric depth planes move at different speeds (foreground parallax cue).
    for layer_index, (speed, blur, alpha, ybase) in enumerate((
        (0.32, 22, 18, 0.36), (0.78, 13, 24, 0.58), (1.55, 7, 31, 0.79)
    )):
        haze = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        hd = ImageDraw.Draw(haze, "RGBA")
        for k in range(4):
            x = int((k*w*.34 + frame_no*speed + seed % 71) % (w+260)) - 130
            y = int(h*ybase + 25*math.sin(t*math.pi*2 + k + layer_index))
            hd.ellipse((x, y, x+int(w*.58), y+int(h*.075)),
                       fill=(150, 170, 185, alpha))
        im = Image.alpha_composite(im, haze.filter(ImageFilter.GaussianBlur(blur)))

    # A cast shadow moves only in beats that imply an unseen presence.
    if action in ("shadow_cross", "shadow_approach", "shadow_stretch", "portrait_turn",
                  "eyes_blink", "handle_rattle"):
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow, "RGBA")
        sx = int(-w*.30 + (w*1.6)*t) if action in ("shadow_cross", "portrait_turn") else int(w*(.58-.20*t))
        sd.ellipse((sx-int(w*.07), int(h*.20), sx+int(w*.07), int(h*.40)),
                   fill=(0, 0, 0, 112))
        sd.polygon([(sx-int(w*.055), int(h*.37)), (sx+int(w*.055), int(h*.37)),
                    (sx+int(w*.20), int(h*.82)), (sx-int(w*.17), int(h*.82))],
                   fill=(0, 0, 0, 104))
        im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(19)))

    # Foreground motes and dust: size/velocity encode three apparent depth planes.
    particles = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(particles, "RGBA")
    for k in range(42):
        depth = 1 + (k % 3)
        speed = (0.55, 1.35, 2.65)[depth-1]
        x = int((k*79 + frame_no*speed + seed % 113) % w)
        y = int((k*151 - frame_no*(0.35 + depth*.32) + seed % 97) % h)
        r = depth
        pd.ellipse((x-r, y-r, x+r, y+r), fill=(220, 226, 232, 42 + depth*15))
    im = Image.alpha_composite(im, particles.filter(ImageFilter.GaussianBlur(0.5)))

    # Subtle anamorphic vignette, retaining readable action and subtitle-safe center.
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette, "RGBA")
    for i in range(9):
        inset = i * 17
        alpha = int(4 + i*1.8)
        vd.rectangle((inset, inset, w-inset, h-inset),
                     outline=(0, 0, 0, alpha), width=18)
    im = Image.alpha_composite(im, vignette.filter(ImageFilter.GaussianBlur(26)))
    return im


def cinematic_camera(image, event, t, frame_no, total_frames, seed):
    """Narrative camera paths: each beat has its own pan, dolly, tilt or restrained handheld move."""
    w, h = image.size
    camera = event.get("camera", "")
    action = event.get("action", "")
    phase = 2 * math.pi * t
    zoom = 1.025 + 0.055 * t
    pan_x = 0.0
    pan_y = 0.0
    if camera == "slow_dolly" or action in ("phone_ring", "bus_approach", "window_flicker"):
        pan_x = 0.035 * math.sin(phase*.35)
        pan_y = -0.025 * t
        zoom += 0.018 * t
    elif camera == "lateral_track" or action in ("walk_down", "shadow_cross", "cable_crawl", "rain_run"):
        pan_x = 0.105 * (t-.5)
        pan_y = 0.018 * math.sin(phase*.5)
    elif camera == "handheld" or action in ("receiver_lift", "handle_rattle", "glass_crack"):
        pan_x = 0.012 * math.sin(frame_no*.71)
        pan_y = 0.010 * math.cos(frame_no*.83)
        zoom += 0.012 * math.sin(phase*1.5)
    elif camera == "push_in" or action in ("screen_call", "mirror_message", "eyes_blink"):
        zoom += 0.065 * t
        pan_y = -0.025 * t
    elif camera == "pull_back":
        zoom += 0.025 * (1-t)
        pan_x = 0.045 * math.sin(phase*.25)
    elif camera == "locked_reveal":
        zoom += 0.012 * t
        pan_x = 0.008 * math.sin(phase*.2)
    sw, sh = int(w*zoom), int(h*zoom)
    enlarged = image.resize((sw, sh), Image.Resampling.LANCZOS)
    max_x, max_y = sw-w, sh-h
    cx = max_x*(.5 + pan_x)
    cy = max_y*(.5 + pan_y)
    left = max(0, min(max_x, int(cx)))
    top = max(0, min(max_y, int(cy)))
    return enlarged.crop((left, top, left+w, top+h)).convert("RGB")
