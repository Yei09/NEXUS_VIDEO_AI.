from __future__ import annotations
import random

NAMES = ["Clara", "Mateo", "Lucía", "Elena", "Julián", "Inés", "Tomás", "Vera"]
TIMES = ["a las 2:17", "poco después de las tres", "a medianoche", "cuando el reloj marcó las 4:06"]
PLACES = ["el sótano", "el pasillo del tercer piso", "la estación abandonada", "la habitación del fondo"]

# Local, template-driven narrative generation. No paid API or external LLM is used.
# Each event is a typed production beat consumed by the scene, animation and audio engines.
STORIES = {
 "paranormal": [
  ("La llamada que no debía existir", "terror paranormal", [
   ("phone_room", "phone_ring", "ring", "fade", "{time}, el teléfono antiguo de {place} sonó aunque llevaba años sin estar conectado."),
   ("stairs", "walk_down", "steps", "cut", "{name} bajó despacio y encontró polvo intacto alrededor del aparato."),
   ("receiver_close", "receiver_lift", "static", "flash", "Al acercarlo al oído escuchó su propia voz: «No mires hacia la puerta»."),
   ("hallway", "shadow_cross", "impact", "impact", "Una silueta cruzó el pasillo y tres golpes respondieron desde el otro lado de la pared."),
   ("floor_cable", "cable_crawl", "scrape", "whip", "El cable se deslizó por el suelo y rodeó lentamente sus zapatos."),
   ("mobile_close", "screen_call", "mobile", "fade", "Su móvil vibró: la llamada entrante provenía del mismo teléfono que tenía delante.")
  ])],
 "casa_embrujada": [
  ("La casa que respiraba", "terror de casa embrujada", [
   ("house_exterior", "window_flicker", "wind", "fade", "{time}, {name} vio encenderse una ventana en la casa que llevaba veinte años vacía."),
   ("front_door", "door_open", "creak", "cut", "La puerta se abrió antes de que pudiera tocarla y dejó escapar un aire helado."),
   ("corridor_portrait", "portrait_turn", "scrape", "dissolve", "En el pasillo, un retrato giró hasta mostrar un rostro que se parecía al suyo."),
   ("living_room", "wall_breathe", "impact", "impact", "Las paredes se hincharon y contrajeron como si la casa estuviera respirando."),
   ("stairwell", "figure_descend", "steps", "whip", "Desde el piso superior bajaron pasos lentos, aunque {name} estaba a solas."),
   ("locked_door", "handle_rattle", "knocks", "fade", "La salida se cerró de golpe y una voz susurró desde dentro de la cerradura.")
  ])],
 "leyenda_urbana": [
  ("La última parada", "leyenda urbana", [
   ("bus_exterior", "bus_approach", "engine", "fade", "{time}, el último autobús se detuvo frente a una parada que no aparecía en la ruta."),
   ("bus_interior", "lights_flicker", "wind", "cut", "{name} subió y descubrió que todos los asientos estaban húmedos."),
   ("bus_passenger", "passenger_turn", "whisper", "dissolve", "Una niña del fondo levantó la cabeza y pidió bajar en un puente desaparecido."),
   ("window_rain", "rain_run", "impact", "impact", "Al mirar por la ventana, {name} vio el puente bajo el agua y figuras golpeando el cristal."),
   ("empty_seat", "seat_sink", "creak", "whip", "El asiento junto a ella se hundió como si alguien invisible acabara de sentarse."),
   ("ticket_close", "ticket_reveal", "static", "fade", "El boleto cambió de destino y mostró una sola palabra: «Regreso».")
  ])],
 "criaturas": [
  ("Lo que esperaba bajo la cama", "terror de criaturas", [
   ("bedroom_wide", "lamp_flicker", "wind", "fade", "{time}, {name} oyó tres arañazos debajo de la cama y apagó la música."),
   ("bed_edge", "hand_reach", "scrape", "cut", "Una mano demasiado larga apareció entre las sombras y rozó el suelo."),
   ("closet_door", "door_creep", "creak", "dissolve", "El armario se abrió unos centímetros aunque la habitación no tenía corriente."),
   ("underbed_view", "eyes_blink", "whisper", "flash", "Dos ojos parpadearon bajo la cama y pronunciaron su nombre."),
   ("lamp_shadow", "shadow_stretch", "impact", "impact", "La lámpara proyectó una sombra que no correspondía a ningún cuerpo."),
   ("bedroom_door", "handle_turn", "knocks", "fade", "La puerta se abrió desde fuera y algo susurró: «Ahora te toca esconderte».")
  ])],
 "psicologico": [
  ("El reflejo equivocado", "terror psicológico", [
   ("bathroom_wide", "mirror_delay", "drip", "fade", "{time}, {name} notó que su reflejo tardaba un segundo más en moverse."),
   ("mirror_close", "reflection_smile", "glass", "cut", "Cuando dejó de sonreír, la imagen mantuvo una sonrisa inmóvil."),
   ("sink_close", "tap_turn", "water", "dissolve", "El grifo se abrió solo y el agua comenzó a salir completamente negra."),
   ("mirror_message", "writing_appear", "scrape", "flash", "Sobre el espejo apareció un mensaje escrito desde el otro lado: «Déjame salir»."),
   ("bathroom_door", "shadow_approach", "steps", "impact", "Una sombra se detuvo detrás de {name}, pero el reflejo seguía mirando al frente."),
   ("mirror_break", "glass_crack", "impact", "fade", "El espejo se agrietó y cada fragmento mostró a {name} mirando en una dirección distinta.")
  ])]
}

def generate_story(category: str, seed: str) -> dict:
    rng = random.Random(seed)
    key = category if category in STORIES else rng.choice(sorted(STORIES))
    title, genre, beats = rng.choice(STORIES[key])
    name, time, place = rng.choice(NAMES), rng.choice(TIMES), rng.choice(PLACES)
    events = []
    for i, (scene, action, sfx, transition, template) in enumerate(beats, 1):
        events.append({
            "event_id": f"beat-{i:02d}",
            "scene": scene,
            "action": action,
            "sfx": sfx,
            "transition": transition,
            "text": template.format(name=name, time=time, place=place),
            "camera": ["slow_dolly", "lateral_track", "handheld", "push_in", "pull_back", "locked_reveal"][i-1],
            "visual_requirements": [scene, action]
        })
    return {
        "title": title,
        "genre": genre,
        "category": key,
        "protagonist": name,
        "events": events,
        "script": " ".join(e["text"] for e in events),
        "generation_method": "local_template_composition_v1",
        "seed": seed
    }
