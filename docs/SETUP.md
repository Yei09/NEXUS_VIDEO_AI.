# Prueba cinematográfica de NEXUS VIDEO AI

## Alcance de esta prueba

Esta ejecución es manual y produce una sola historia de terror en español. No se conecta Google Drive ni Make, no se publica en redes sociales, no se activa ningún horario y no se requiere facturación.

## Ejecutar la prueba

1. Abre [GitHub Actions](https://github.com/Yei09/NEXUS_VIDEO_AI./actions/workflows/manual-video-test.yml).
2. Selecciona **NEXUS Video - Manual Cinematic Horror Test**.
3. Pulsa **Run workflow** y elige una categoría.
4. Espera a que termine la ejecución.
5. Descarga el artefacto **nexus-cinematic-horror-test**.
6. Dentro del ZIP encontrarás el MP4, `output/metadata.json` y `output/script.txt`.

## Qué cambia en esta versión

- Escenas ilustradas diferentes según el acontecimiento narrado.
- Zoom lento y desplazamiento lateral para evitar planos inmóviles.
- Variación sutil de iluminación, grano y transiciones por fundido.
- Voz Piper `es_MX-claude-high` (masculina, calidad High), narrada por párrafos con pausas.
- Procesamiento moderado de tono, ecualización y compresión.
- Subtítulos ASS compactos, con hasta dos líneas y márgenes seguros.
- Ambiente de viento, drone grave y golpes sintéticos en puntos narrativos.
- Validación de H.264/AAC, 1080×1920, 30 fps y duración de 30–60 segundos.

## Límites que deben tenerse presentes

Las escenas son ilustraciones procedurales, no vídeo real ni imágenes generadas por un modelo cinematográfico. El movimiento se crea en FFmpeg mediante cámara virtual, variaciones de luz y fundidos. Los sonidos son síntesis, no grabaciones Foley. La voz Claude High figura como masculina en el catálogo Piper, pero su profundidad y naturalidad deben juzgarse escuchando el resultado.

El motor conserva cinco historias predefinidas; todavía no crea relatos dinámicamente ni evita repeticiones entre ejecuciones.

## Estado de verificación

Los cambios de código están guardados en GitHub. La ejecución de Actions y la creación/validación del MP4 todavía están pendientes. No se debe afirmar que la prueba pasó hasta que el workflow termine y se revise su artefacto.
