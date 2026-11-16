# NEXUS VIDEO AI

Generador cloud de **historias originales de terror en español**. Esta prueba mejora el montaje para acercarlo al lenguaje de un cortometraje vertical: planos con movimiento, escenas ilustradas diferenciadas, transiciones, subtítulos compactos y diseño sonoro ambiental.

## Flujo de creación

1. Selecciona una categoría y ejecuta manualmente el workflow.
2. Piper genera la narración por párrafos para conservar pausas dramáticas.
3. Python/Pillow dibuja composiciones distintas según los acontecimientos (casa, sótano, autobús, dormitorio o espejo).
4. FFmpeg anima cada plano con zoom lento, desplazamiento lateral, variación sutil de luz, grano y fundidos entre escenas.
5. Subtítulos ASS discretos, con máximo dos líneas, se distribuyen según la duración de cada párrafo y las pausas.
6. La mezcla incluye voz procesada moderadamente, viento, drone grave y golpes sintéticos sincronizados con los beats narrativos.
7. Valida MP4 H.264/AAC, 1080×1920, 30 fps y duración de 30–60 segundos.

## Voz

La prueba usa `es_MX-claude-high`, voz masculina mexicana de calidad High del catálogo Piper. Se aplica un descenso moderado de tono y ecualización/compresión ligera. La calidad percibida y el carácter grave deben aprobarse escuchando el MP4 real; el catálogo no publica una medida objetiva de profundidad vocal.

## Seguridad y límites

- Solo ejecución manual con `workflow_dispatch`; no hay programación diaria.
- Una ejecución crea exactamente una historia.
- No se publica en TikTok, Instagram, YouTube ni ninguna red.
- No se conecta Make ni Google Drive en este flujo.
- No se incorporan APIs de pago ni se activa facturación.
- El arte se genera proceduralmente con Python/Pillow: hay movimiento de cámara y composición por escena, pero no es metraje real ni generación cinematográfica mediante un modelo de vídeo.
- Viento, drone y golpes son sonidos sintetizados por FFmpeg, no grabaciones Foley profesionales.
- Las cinco historias siguen siendo guiones predefinidos; aún no hay generación narrativa dinámica ni sistema anti-repetición.

## Prueba manual

Abre Actions → **NEXUS Video - Manual Cinematic Horror Test** → Run workflow y elige una categoría. Descarga el artefacto `nexus-cinematic-horror-test`. Incluye el MP4, `metadata.json` y `script.txt`.

**Estado:** los cambios de código y el workflow están guardados, pero esta revisión no ha ejecutado GitHub Actions ni ha generado/verificado un MP4. No se debe considerar aprobada la calidad audiovisual hasta escuchar y revisar el artefacto de esta prueba.
