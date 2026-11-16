# NEXUS VIDEO AI V4 — arquitectura y contratos

## Estado real de esta rama

V4 se desarrolla en la rama v4-make-drive, creada desde cinematic-v3. No modifica main, otros repositorios ni el proyecto Android.

La implementación añade:
- nexus_video/story_v4.py: generador local de historias estructuradas por acontecimientos.
- nexus_video/engine_v4.py: Piper, escenas 2D procedurales animadas, cámara, niebla, partículas, iluminación, subtítulos, audio sintetizado y validaciones.
- nexus_video/drive_v4.py: OAuth de usuario, estructura de carpetas, carga reanudable y verificación de archivos en Drive.
- nexus_video/notify_make_v4.py: callbacks autenticados a Make.
- .github/workflows/nexus-video-v4.yml: ejecución manual render y operación upload_only.

**Límite audiovisual explícito:** V4 genera ilustraciones 2D procedurales animadas con Pillow y FFmpeg. No genera metraje real, 3D, ni imágenes con un modelo generativo. Las historias se componen localmente a partir de plantillas narrativas combinables; no se llama a un LLM externo. Los sonidos y la música son sintetizados por el propio motor, no grabaciones Foley.

## Parámetros exactos del workflow

| Input de GitHub Actions | Tipo | Valores |
|---|---|---|
| operation | choice | render, upload_only |
| request_id | string | UUID |
| category | choice | paranormal, casa_embrujada, leyenda_urbana, criaturas, psicologico |
| duration_seconds | number | 30–60 |
| voice | choice | cuatro modelos Piper enumerados en el workflow |
| voice_rate | string | 0.75–1.25 |
| pitch_semitones | string | -2.0 a 2.0 |
| voice_volume | string | 0.5–1.5 |
| pause_seconds | string | 0.2–1.5 |
| narration_intensity | choice | calm, mysterious, urgent |
| voice_auditions | boolean | true / false |
| source_run_id | string | obligatorio solo para upload_only |

El workflow solo admite ejecución manual (workflow_dispatch). No tiene cron, publicación social ni programación diaria.

## JSON de solicitud de Make

Webhook: NEXUS_V4_GENERATION_REQUEST.

    {
      "schema_version": "1.0",
      "event": "generation.request",
      "request_id": "7d83b3ac-59fd-4b4b-a311-bb68c37ad02e",
      "operation": "render",
      "category": "paranormal",
      "duration_seconds": 45,
      "voice": "es_MX-claude-high",
      "voice_rate": 1.0,
      "pitch_semitones": -1.0,
      "voice_volume": 1.0,
      "pause_seconds": 0.78,
      "narration_intensity": "mysterious",
      "voice_auditions": false
    }

Para reintentar únicamente Drive, sin renderizar otra vez:

    {
      "schema_version": "1.0",
      "event": "generation.request",
      "request_id": "7d83b3ac-59fd-4b4b-a311-bb68c37ad02e",
      "operation": "upload_only",
      "source_run_id": "123456789",
      "category": "paranormal",
      "duration_seconds": 45,
      "voice": "es_MX-claude-high",
      "voice_rate": 1.0,
      "pitch_semitones": -1.0,
      "voice_volume": 1.0,
      "pause_seconds": 0.78,
      "narration_intensity": "mysterious",
      "voice_auditions": false
    }

El mismo request_id no puede renderizarse dos veces. upload_only es la única operación que reutiliza el artefacto de una ejecución anterior.

## Respuesta inmediata del webhook

Make responde HTTP 202 tras registrar y despachar la solicitud:

    {
      "schema_version": "1.0",
      "request_id": "7d83b3ac-59fd-4b4b-a311-bb68c37ad02e",
      "status": "pending",
      "message": "Solicitud aceptada; GitHub Actions notificará el progreso."
    }

GitHub Actions devuelve HTTP 204 a la llamada REST de workflow dispatch. No devuelve un run_id en esa respuesta. El run_id llega mediante el primer callback de GitHub a Make.

## Callback de GitHub a Make

Webhook: NEXUS_V4_GENERATION_CALLBACK.

Cada evento lleva schema_version, event=generation.status, request_id, status, run_id, run_url, artifact_name, updated_at y metadata. Los estados reportados incluyen processing, story_created, narrating, scenes_rendering, audio_mixing, rendered, uploading_drive, completed y drive_upload_failed. Los eventos intermedios mantienen status=processing y actualizan stage. Make normaliza drive_upload_failed como status=error y conserva stage=drive_upload_failed para permitir el reintento de carga.

El callback usa el encabezado x-make-apikey; la clave no está en el repositorio. Make valida la clave en el propio Custom webhook.

## Estados de negocio en Make

- pending: solicitud validada y guardada; despacho solicitado.
- processing: GitHub confirmó que el workflow comenzó.
- completed: vídeo y archivos subidos y verificados en Drive.
- error: render, descarga del artefacto, Drive o una etapa crítica falló.

Campos adicionales: stage, run_id, run_url, artifact_name, drive_links, error_message, created_at, updated_at.

## Límite de activación de GitHub

GitHub documenta que un workflow workflow_dispatch solo puede recibir eventos si el archivo del workflow ya existe en la rama predeterminada. Por tanto, mientras nexus-video-v4.yml exista solo en v4-make-drive, Make no puede despacharlo mediante la API. Para activar el circuito Make → GitHub será necesario aprobar y fusionar el workflow a main (o cambiar temporalmente la rama predeterminada, acción que no se hará sin autorización). Esta rama puede revisarse y prepararse sin modificar main.

## Archivos de salida por solicitud

output/<request_id>/:
- videos/*.mp4, thumbnail.jpg
- audios/narration.wav, audio_mix.wav, music.wav, effects.wav, muestras opcionales
- historia.txt, story.txt, script.txt, story_events.json
- metadata.json, motion_report.json, render_report.json
- errors/*, drive_manifest.json

## Seguridad y costes

- Token GitHub: se almacena en las credenciales del módulo HTTP de Make, no en Git.
- Make callback: URL y API key se guardan como GitHub Actions Secrets.
- Google: OAuth client JSON y refresh token se guardan como GitHub Actions Secrets.
- El alcance OAuth implementado es drive.file; la app crea y administra su propia carpeta raíz y sus descendientes.
- No se transporta el MP4 por Make.
- No se usan APIs de generación de pago ni publicación social.
- Make Free conserva sus límites de operaciones y webhooks; no se activa ningún plan de pago.
