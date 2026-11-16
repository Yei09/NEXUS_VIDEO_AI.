# NEXUS VIDEO AI

Generador cloud de **historias originales de terror en español** para vídeos verticales cortos. Incluye terror psicológico, paranormal, leyendas urbanas, casas embrujadas, criaturas y sucesos inexplicables.

## Flujo de creación

1. Selecciona una categoría de terror.
2. El motor crea un relato breve original con gancho inicial y giro final.
3. Piper TTS genera la narración en español.
4. Python/Pillow crea escenas ilustradas originales localmente (sin bancos de imágenes ni API de pago).
5. FFmpeg monta las escenas, subtítulos sincronizados, voz y ambiente de terror sintetizado.
6. Valida MP4 H.264/AAC, 1080×1920 y duración de 25–60 segundos.
7. Puede guardar el MP4 en Google Drive cuando se configuren credenciales OAuth.

## Seguridad y límites

- Solo ejecución manual con workflow_dispatch. No hay programación diaria.
- Una ejecución crea exactamente una historia.
- No se publica en TikTok, Instagram, YouTube ni ninguna red.
- No se integra ningún servicio de pago ni se habilita facturación.
- Drive es opcional y se omite sin credenciales válidas.
- Make recibe metadatos solamente; nunca recibe el vídeo.
- El panel web es una maqueta de control; no tiene aún backend conectado.

## Prueba manual

Abre Actions → **NEXUS Video - Manual Horror Test** → Run workflow y elige una categoría. Descarga el artefacto `nexus-horror-story-test`. Para Drive, sigue `docs/SETUP.md`.

## Importante

Las escenas de prueba son ilustraciones procedurales generadas por código y el ambiente sonoro se sintetiza en FFmpeg. No son todavía imágenes cinematográficas generadas por un modelo de imagen ni efectos Foley grabados. La voz y el render necesitan una ejecución real de Actions antes de considerarse verificados.
