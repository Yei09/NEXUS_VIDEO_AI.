# NEXUS VIDEO AI — Cinematic V3

## Objetivo y cambios

La rama cinematic-v3 añade un motor paralelo (nexus_video/engine_v3.py) y un workflow manual propio. El motor anterior y el workflow anterior se conservan sin modificaciones.

La historia se modela como acontecimientos estructurados. Cada acontecimiento define texto narrado, tipo de escena y composición, acción animada del objeto o silueta, efecto sonoro asociado y transición de entrada/salida.

La prueba usa seis acontecimientos distintos: plano general del teléfono, escalera, primer plano del auricular, pasillo con sombra, cable en el suelo y móvil con llamada entrante. Cada plano se dibuja como una secuencia de fotogramas, no como una ilustración fija con zoom. Se mueven objetos, sombras, niebla y partículas; hay parpadeo, vibración en el impacto y transiciones de fundido/destello/estela.

## Voces Piper incluidas para audición

Las cuatro muestras usan exactamente el mismo texto y el mismo procesamiento de tono. En Sharvard se fuerza speaker 0 (masculino) para que la comparación no mezcle voces. Los archivos WAV se generan por separado en output/voice-samples/.

| Modelo | Acento | Nivel de modelo | Nota de licencia del modelo |
|---|---|---:|---|
| es_MX-claude-high | México | high | Apache-2.0 |
| es_MX-ald-medium | México | medium | Unlicense |
| es_ES-davefx-medium | España | medium | CC0 según su ficha de modelo |
| es_ES-sharvard-medium | España | medium | CC BY 3.0; speaker 0 masculino, speaker 1 femenino; requiere atribución |

“High” y “medium” describen el tamaño/calidad de distribución del modelo, no garantizan una voz más grave, masculina o más natural. El catálogo oficial enumera idioma, modelo y nivel, pero no ofrece una clasificación fiable de profundidad vocal. La elección final queda pendiente de escuchar las muestras. No se aprueba ninguna voz automáticamente.

Fuentes de modelos y fichas:
- https://github.com/rhasspy/piper/blob/master/VOICES.md
- https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/claude/high
- https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/ald/medium
- https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/davefx/medium
- https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium

## Ejecución manual

1. Abre GitHub → Actions.
2. Selecciona NEXUS Video - Cinematic V3 Manual Test.
3. Pulsa Run workflow en la rama cinematic-v3.
4. Deja es_MX-claude-high como voz temporal si aún no has comparado las muestras. El workflow genera las cuatro audiciones de todos modos.
5. Descarga nexus-cinematic-v3-manual-test cuando termine.

El artefacto contiene MP4 vertical H.264/AAC, narration.wav sin música ni efectos, cuatro WAV de audición, metadata.json, motion_report.json con diferencia de fotogramas y comparación entre escenas, y script.txt.

## Criterios de aceptación automatizados

El workflow comprueba 1080×1920, 30 FPS, H.264 y AAC; duración de 30–60 segundos; seis composiciones distintas; diferencia perceptible entre fotogramas iniciales y medios de cada escena; cuatro muestras de voz y WAV de narración independiente.

Estas comprobaciones son automáticas; la aprobación estética final sigue requiriendo revisión humana del MP4 y escucha de los WAV. El arte se genera proceduralmente con Pillow, no es metraje real ni vídeo generativo.

## Límites y seguridad

- Solo workflow_dispatch; ninguna programación.
- Una ejecución genera una historia.
- No hay publicación en redes.
- No se conecta Make ni Google Drive.
- No hay APIs de pago ni servicios de facturación.
- El motor anterior no se borra ni se modifica.
