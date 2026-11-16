from __future__ import annotations

from dataclasses import dataclass
import math
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class SceneLayer:
    """A separately rendered visual plane with its own transform and animation."""
    name: str
    image: Image.Image
    depth: float
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    blur: float = 0.0
    camera_weight: float = 1.0
    focus_weight: float = 1.0


def _transparent(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _actor_layer(size, event, t, frame_no):
    w, h = size
    layer = _transparent(size)
    d = ImageDraw.Draw(layer, "RGBA")
    action = event.get("action", "")
    if action not in {"walk_down", "figure_descend", "passenger_turn", "shadow_approach",
                      "portrait_turn", "eyes_blink", "hand_reach"}:
        return None
    progress = max(0.0, min(1.0, t))
    stride = math.sin(progress * math.pi * 8)
    x = int(w * (0.50 + 0.12 * (progress - .5)))
    y = int(h * (.43 + .012 * math.sin(progress * math.pi * 4)))
    scale = .72 + .12 * progress
    r = int(23 * scale)
    color = (2, 3, 7, 238)
    d.ellipse((x-r, y-r*2, x+r, y), fill=color)
    d.polygon([(x-r, y-4), (x+r, y-4), (x+int(45*scale), y+int(150*scale)),
               (x-int(45*scale), y+int(150*scale))], fill=color)
    swing = int(22 * scale * stride)
    d.line((x-8, y+int(120*scale), x-18-swing, y+int(205*scale)),
           fill=color, width=max(3, int(15*scale)))
    d.line((x+8, y+int(120*scale), x+18+swing, y+int(205*scale)),
           fill=color, width=max(3, int(15*scale)))
    return SceneLayer("character", layer, .58, camera_weight=1.0)


def _prop_layer(size, event, t, frame_no):
    w, h = size
    action = event.get("action", "")
    layer = _transparent(size)
    d = ImageDraw.Draw(layer, "RGBA")
    pulse = math.sin(frame_no * .72)
    if action in {"phone_ring", "receiver_lift"}:
        # Independent handset sprite; vibration and lift are tied to the phone beat.
        bob = int((5 if action == "phone_ring" else 22) * math.sin(t * math.pi * 6))
        cx, cy = int(w*.50), int(h*.61 - bob)
        d.rounded_rectangle((cx-145, cy-34, cx+145, cy+34), radius=28,
                            fill=(19, 20, 21, 255), outline=(190, 160, 119, 255), width=7)
        d.ellipse((cx-160, cy-30, cx-105, cy+30), fill=(8, 10, 12, 255),
                  outline=(174, 145, 111, 255), width=5)
        d.ellipse((cx+105, cy-30, cx+160, cy+30), fill=(8, 10, 12, 255),
                  outline=(174, 145, 111, 255), width=5)
        return SceneLayer("handset", layer, .78, y=float(-bob), rotation=0.8*pulse)
    if action in {"door_open", "door_creep", "handle_turn", "handle_rattle"}:
        angle = (8 + 42 * max(0.0, min(1.0, t))) if action == "door_open" else 3 + 4*math.sin(t*math.pi*3)
        # Draw the door leaf as an independent sprite and rotate around its hinge.
        sprite = _transparent((int(w*.42), int(h*.62)))
        sd = ImageDraw.Draw(sprite, "RGBA")
        sw, sh = sprite.size
        sd.rectangle((8, 8, sw-8, sh-8), fill=(27, 23, 22, 250),
                     outline=(145, 126, 98, 255), width=8)
        sd.ellipse((sw-38, sh//2, sw-18, sh//2+20), fill=(194, 160, 103, 255))
        return SceneLayer("door_leaf", sprite, .64, x=w*.29, y=h*.18,
                          rotation=-angle, camera_weight=1.0)
    if action in {"cable_crawl"}:
        points=[]
        for k in range(22):
            u=k/21
            x=w*.50 + (u-.5)*w*.48 + math.sin(u*math.pi*3+t*math.pi*2)*w*.035
            y=h*.42 + u*h*.42
            points.append((int(x),int(y)))
        d.line(points, fill=(4,5,7,255), width=19, joint="curve")
        d.line(points, fill=(185,160,124,255), width=10, joint="curve")
        return SceneLayer("moving_cable", layer, .88, camera_weight=1.1)
    if action in {"screen_call", "lights_flicker", "window_flicker"}:
        alpha=int(100+80*abs(pulse))
        d.ellipse((w*.37,h*.30,w*.63,h*.60), fill=(68,155,210,alpha))
        return SceneLayer("phone_screen_glow" if action=="screen_call" else "practical_light",
                          layer, .42, blur=18, camera_weight=.45)
    return None


def _shadow_layer(size, event, t):
    action=event.get("action","")
    if action not in {"shadow_cross","shadow_approach","shadow_stretch","portrait_turn",
                      "eyes_blink","handle_rattle"}:
        return None
    w,h=size
    layer=_transparent(size)
    d=ImageDraw.Draw(layer,"RGBA")
    x=int(w*(-.25+1.5*t)) if action in {"shadow_cross","portrait_turn"} else int(w*(.62-.22*t))
    d.ellipse((x-w*.07,h*.20,x+w*.07,h*.40),fill=(0,0,0,145))
    d.polygon([(x-w*.055,h*.37),(x+w*.055,h*.37),(x+w*.20,h*.82),(x-w*.17,h*.82)],
              fill=(0,0,0,135))
    return SceneLayer("cast_shadow",layer,.70,blur=13,camera_weight=1.0)


def _environment_layer(size, event, t, frame_no, seed):
    w,h=size
    layer=_transparent(size)
    d=ImageDraw.Draw(layer,"RGBA")
    action=event.get("action","")
    # Atmosphere is attached to the scene's practical event, not a generic full-frame filter.
    count=24
    for i in range(count):
        depth=0.25+(i%4)*0.22
        speed=(.25,.55,1.0,1.7)[i%4]
        x=int((i*83+frame_no*speed+seed%97)%w)
        y=int((i*137-frame_no*speed*1.4+seed%61)%h)
        r=max(1,int(depth*2.4))
        d.ellipse((x-r,y-r,x+r,y+r),fill=(195,207,218,35+int(depth*20)))
    return SceneLayer("environment_particles",layer,.25,camera_weight=.35,focus_weight=.4)


def compose_scene_layers(background, layers, camera_target=None, focus_depth=.55):
    """Composite independent depth planes. Camera parallax is proportional to layer depth."""
    base=background.convert("RGBA")
    w,h=base.size
    camera_x=camera_y=0.0
    if camera_target is not None:
        camera_x,camera_y=camera_target
    ordered=sorted(layers,key=lambda item:item.depth)
    for layer in ordered:
        sprite=layer.image.convert("RGBA")
        focus_blur=abs(layer.depth-focus_depth)*layer.focus_weight*2.0
        total_blur=layer.blur+focus_blur
        if total_blur>0:
            sprite=sprite.filter(ImageFilter.GaussianBlur(total_blur))
        if layer.rotation:
            sprite=sprite.rotate(layer.rotation,resample=Image.Resampling.BICUBIC,expand=True)
        if layer.scale!=1.0:
            sprite=sprite.resize((max(1,int(sprite.width*layer.scale)),
                                  max(1,int(sprite.height*layer.scale))),Image.Resampling.LANCZOS)
        px=int(layer.x-camera_x*layer.depth*layer.camera_weight)
        py=int(layer.y-camera_y*layer.depth*layer.camera_weight)
        # Each layer retains its own world transform and is clipped only at final composition.
        base.alpha_composite(sprite,(px,py))
    return base.convert("RGB")


def render_depth_scene(base_image, event, t, frame_no, total_frames, seed):
    """V4.2.1 depth compositor. Existing scene plate remains the fallback background."""
    size=base_image.size
    layers=[]
    for layer in (
        _actor_layer(size,event,t,frame_no),
        _prop_layer(size,event,t,frame_no),
        _shadow_layer(size,event,t),
        _environment_layer(size,event,t,frame_no,seed),
    ):
        if layer is not None:
            layers.append(layer)
    # Narrative tracking is tied to the animated subject's movement.
    target=(0.0, 0.0)
    if event.get("camera") in {"lateral_track","push_in"}:
        target=(math.sin(t*math.pi)*size[0]*.035, -t*size[1]*.012)
    focus_depth=.78 if event.get("action") in {"phone_ring","receiver_lift","screen_call","door_open","cable_crawl"} else .58
    return compose_scene_layers(base_image,layers,camera_target=target,focus_depth=focus_depth), [
        {"name":x.name,"depth":round(x.depth,3),"independent_transform":True,
         "camera_weight":x.camera_weight,"blur":x.blur} for x in layers
    ]
