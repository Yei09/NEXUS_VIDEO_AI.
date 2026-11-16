# NEXUS VIDEO AI V4

Motor de producción audiovisual en español, desarrollado en una rama independiente para integrar GitHub Actions, Make.com y Google Drive.

## Estado de esta versión

Rama de trabajo: v4-make-drive (creada desde cinematic-v3).

Esta rama incorpora el motor V4, un workflow manual, un cargador de Google Drive con OAuth y verificación, callbacks de Make y contratos/documentación para los escenarios y el futuro panel.

**Todavía no se ha ejecutado una generación V4 ni se ha conectado una cuenta Make o Google Drive.** La integración requiere secretos y escenarios creados por el propietario. Además, GitHub exige que el workflow_dispatch exista en la rama predeterminada antes de aceptar despachos API; el workflow de V4 está en esta rama y no se fusionará a main sin autorización.

## Capacidades implementadas en código

- Historias en español compuestas localmente desde plantillas narrativas combinables; cada evento define escena, acción, cámara, efecto y transición.
- Seis escenas por historia con composiciones 2D procedurales diferenciadas.
- Animación por fotogramas: objetos/personajes, sombras, niebla, partículas, luces, cámara dolly/pan y vibración de impacto.
- Verificación de movimiento entre fotogramas y diversidad entre escenas, con hasta dos regeneraciones limitadas para diversidad.
- Piper TTS con cuatro modelos compatibles, velocidad configurable, ajuste de tono y nivel de intensidad.
- Narración WAV separada, música ambiental y efectos sintetizados libres de muestras de terceros.
- MP4 vertical 1080×1920, H.264/AAC, 30 FPS, 30–60 segundos, validación con ffprobe.
- Google Drive: carpetas por request_id, subida reanudable, verificación de tamaño/MD5 y operación upload_only para reintentar sin renderizar.
- Make: callbacks autenticados de estado y contrato exacto de workflow inputs.

**Límite visual:** el motor produce ilustraciones 2D animadas mediante Pillow/FFmpeg. No es metraje real, 3D ni generación de vídeo con un modelo generativo. La narrativa es local por plantillas, no un LLM.

## Ejecución manual

Workflow: .github/workflows/nexus-video-v4.yml

Inputs:
- operation: render
- request_id: UUID (puede quedar vacío en una ejecución manual)
- category: paranormal / casa_embrujada / leyenda_urbana / criaturas / psicologico
- duration_seconds: 30–60
- voice: es_MX-claude-high / es_MX-ald-medium / es_ES-davefx-medium / es_ES-sharvard-medium
- voice_rate: 0.75–1.25
- pitch_semitones: -2 a +2
- voice_volume: 0.5–1.5
- pause_seconds: 0.2–1.5
- narration_intensity: calm / mysterious / urgent
- voice_auditions: true para cuatro muestras WAV

Para reintentar solo la carga de Drive, operation=upload_only y se requiere el request_id y source_run_id originales.

## Configuración externa requerida

1. Google Drive OAuth: seguir docs/GOOGLE_DRIVE_V4_SETUP.md.
2. Make webhooks/Data Store: seguir docs/MAKE_V4_BLUEPRINT.md.
3. Contratos de inputs y estados: docs/V4_ARCHITECTURE.md.
4. Interfaces del futuro panel: docs/PANEL_API_V4.md.

Secrets de GitHub:
- GOOGLE_OAUTH_CLIENT_JSON
- GOOGLE_OAUTH_REFRESH_TOKEN
- MAKE_RESULT_WEBHOOK_URL
- MAKE_WEBHOOK_API_KEY

Token GitHub fine-grained se almacena como Credential en el módulo HTTP de Make; no se guarda en GitHub ni en el repositorio.

## Archivos

Cada generación crea output/<request_id>/ con videos, audios, historia, script, metadata, motion_report, render_report, thumbnail y errores. El workflow conserva el directorio como artefacto de GitHub antes de intentar Drive. La retención configurada es 14 días.

## Restricciones

- No cron ni generación diaria.
- No publicación en redes.
- No Make ni Google Drive se activan sin credenciales y autorización.
- No facturación habilitada por este repositorio.
- No se modifica main ni NEXUS_AI_ADVANCED.
