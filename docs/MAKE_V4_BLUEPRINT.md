# Make.com V4 — configuración del escenario

Este documento es un blueprint exacto. No se ha creado ni activado ningún escenario en la cuenta Make: la cuenta no está conectada a esta sesión y los webhooks/credenciales deben crearse desde tu cuenta.

## Webhooks necesarios

Crea estos Custom webhooks en Make. Usa autenticación API Key en cada uno y guarda las claves en un gestor seguro. Make espera la clave en el encabezado x-make-apikey. No pegues las claves en GitHub público ni en este chat.

1. NEXUS_V4_GENERATION_REQUEST — recibe las órdenes.
2. NEXUS_V4_GENERATION_CALLBACK — recibe progreso y resultado desde GitHub Actions.
3. NEXUS_V4_PANEL_QUERY — interfaz de consulta para el futuro panel.

En cada webhook, configura una Data structure con los campos indicados en V4_ARCHITECTURE.md. Activa Advanced settings solo si necesitas inspeccionar otros encabezados; la autenticación API Key la valida Make antes de ejecutar el escenario.

## Data Store

Crea un Data Store llamado NEXUS_V4_JOBS. Usa request_id como Key y estos campos:
- request_id (text)
- status (text): pending, processing, completed, error
- stage (text)
- category (text)
- title (text)
- duration_seconds (number)
- voice (text)
- run_id (text)
- run_url (text)
- artifact_name (text)
- drive_root_url (text)
- drive_files_json (text)
- error_message (text)
- created_at (date)
- updated_at (date)
- source_run_id (text)

## Escenario 1 — NEXUS_V4_REQUEST_TO_GITHUB

Módulos en este orden:

1. Webhooks > Custom webhook: NEXUS_V4_GENERATION_REQUEST.
2. Filtro de validación:
   - schema_version = 1.0
   - event = generation.request
   - request_id tiene formato UUID
   - operation es render o upload_only
   - category pertenece a la lista del workflow
   - duration_seconds está entre 30 y 60
   - voice pertenece a los cuatro modelos permitidos
   - voice_rate está entre 0.75 y 1.25
   - pitch_semitones está entre -2 y 2
   - voice_volume está entre 0.5 y 1.5
   - pause_seconds está entre 0.2 y 1.5
   - narration_intensity es calm, mysterious o urgent
   - si operation=upload_only, request_id y source_run_id son obligatorios.
3. Usa un Router según operation:
   - Ruta render: Data Store > Add/Replace a Record con Key=request_id, status=pending, stage=queued y Overwrite desactivado. Si la clave ya existe, la operación falla; la ruta de error responde HTTP 409 duplicate_request y no despacha un nuevo render.
   - Ruta upload_only: Data Store > Get a Record con Key=request_id. Solo continúa si el registro existe, status=error, stage=drive_upload_failed y el campo source_run_id del registro coincide exactamente con source_run_id de la solicitud. Después usa Data Store > Update a Record para status=pending, stage=drive_retry. Si no coincide, responde HTTP 409 retry_not_allowed.
   Activa Process data in order en la configuración del escenario para serializar las solicitudes y reducir carreras entre comprobación y escritura.
4. HTTP > Make a request (HTTP v4):
   - Method: POST
   - URL: https://api.github.com/repos/Yei09/NEXUS_VIDEO_AI./actions/workflows/nexus-video-v4.yml/dispatches
   - Authentication: Bearer token guardado como Credential/Keychain de Make, nunca en el body.
   - Headers: Accept: application/vnd.github+json; X-GitHub-Api-Version: 2022-11-28; Content-Type: application/json.
   - Body type: Raw / JSON.
   - Body exacto:
   
       {
         "ref": "v4-make-drive",
         "inputs": {
           "operation": "{{operation}}",
           "request_id": "{{request_id}}",
           "category": "{{category}}",
           "duration_seconds": "{{duration_seconds}}",
           "voice": "{{voice}}",
           "voice_rate": "{{voice_rate}}",
           "pitch_semitones": "{{pitch_semitones}}",
           "voice_volume": "{{voice_volume}}",
           "pause_seconds": "{{pause_seconds}}",
           "narration_intensity": "{{narration_intensity}}",
           "voice_auditions": {{voice_auditions}},
           "source_run_id": "{{source_run_id}}"
         }
       }

   Sustituye cada marcador por el campo mapeado del webhook. voice_auditions debe mapearse como booleano JSON true/false, no como texto. Si operation=render, source_run_id puede enviarse como cadena vacía.
5. Webhooks > Webhook Response: HTTP 202, Content-Type application/json, body:

       {
         "schema_version": "1.0",
         "request_id": "{{request_id}}",
         "status": "pending",
         "message": "Solicitud aceptada; GitHub Actions notificará el progreso."
       }

GitHub devuelve HTTP 204 al despachar workflow_dispatch; ese 204 solo confirma que GitHub aceptó el evento, no que el render haya terminado. El run_id se obtiene del callback inicial de GitHub. No añadas un Update a Record después del HTTP 204: el callback puede llegar antes y no debe sobrescribirse con pending. Si el despacho falla, la ruta de error actualiza status=error y stage=dispatch_failed.

### Credencial GitHub en Make

Crea un Fine-grained personal access token limitado al repositorio Yei09/NEXUS_VIDEO_AI. Permiso mínimo: Actions = Read and write; Metadata = Read (automático). No marques permisos de Contents write ni Administration. Guarda el token como Credential/Keychain en el módulo HTTP v4 de Make. No lo almacenes en el Data Store ni en el JSON.

## Escenario 2 — NEXUS_V4_CALLBACK_TO_STORE

1. Webhooks > Custom webhook: NEXUS_V4_GENERATION_CALLBACK.
2. Data Store > Get a Record usando request_id.
3. Actualiza status, stage, run_id (run actual), run_url, artifact_name, metadata, drive links, error y updated_at. Para source_run_id: en operation=render, inicialízalo con el primer run_id; en operation=upload_only, conserva el source_run_id original recibido y no lo sustituyas por el run_id de reintento.
4. Normaliza:
   - processing → status=processing, stage=rendering
   - story_created → status=processing, stage=story_created
   - narrating → status=processing, stage=narrating
   - scenes_rendering → status=processing, stage=scenes_rendering
   - audio_mixing → status=processing, stage=audio_mixing
   - rendered o uploading_drive → status=processing, stage=drive_upload
   - completed → status=completed, stage=done
   - drive_upload_failed o error → status=error, stage=drive_upload_failed o render_failed.
5. Webhook Response HTTP 200 con JSON { "accepted": true, "request_id": "{{request_id}}" }.

La API key de este webhook debe ser la misma que guardes en GitHub Secrets como MAKE_WEBHOOK_API_KEY. La URL se guarda en MAKE_RESULT_WEBHOOK_URL. El código envía la clave en x-make-apikey y no escribe el secreto en logs.

## Escenario 3 — NEXUS_V4_PANEL_QUERY

1. Custom webhook NEXUS_V4_PANEL_QUERY, protegido con API Key.
2. Recibe { "request_id": "UUID" }.
3. Data Store > Get a Record por request_id.
4. Webhook Response devuelve status, stage, run_url, artifact_name, drive_root_url, drive_files_json, error_message y updated_at.
5. Para historial, añade un modo list con Search Records ordenado por created_at descendente y un límite explícito.

El panel debe llamar a estos webhooks desde un backend/proxy propio; no expongas la URL ni la API key de Make en JavaScript público.

## Reintentos y anti-duplicados

- Activa Process data in order en el escenario de solicitudes.
- La clave del Data Store es request_id; no permitas sobrescritura al crear.
- No reintentes un render con el mismo request_id. Si falla Drive, la ruta upload_only solo se permite cuando el registro está en error/drive_upload_failed; conserva el mismo request_id y source_run_id original.
- Para fallos HTTP 429/5xx del endpoint de GitHub, usa un error handler con máximo 3 intentos y espera progresiva (por ejemplo 2, 5 y 10 segundos). No reintentes 401/403/422: son errores de credenciales o payload.
- Si GitHub devuelve 204 pero no llega callback, conserva el estado processing y consulta el run en GitHub manualmente; no lances otro render a ciegas.
- Make Free tiene límites propios de operaciones, webhooks y Data Store; mantén la primera prueba manual y no habilites un horario.

## Bloqueo actual de workflow_dispatch

La documentación oficial de GitHub establece que workflow_dispatch solo recibe eventos si el archivo workflow está en la rama predeterminada. El workflow V4 está en v4-make-drive. El PR #2 (v4-workflow-bootstrap) propone agregar únicamente ese archivo a main; no está fusionado. Make no podrá lanzar la rama hasta que el propietario apruebe y fusione ese PR. El workflow tiene una guarda para ejecutar solo el ref v4-make-drive. No hagas el despacho de prueba antes de resolver este punto.
