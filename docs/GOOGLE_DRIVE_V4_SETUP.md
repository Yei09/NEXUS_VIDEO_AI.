# Google Drive V4 — OAuth y subida verificada

## Método elegido

V4 usa Google Drive API v3 con OAuth 2.0 de usuario y refresh token. No usa una cuenta de servicio: para guardar en tu Mi unidad, el usuario debe autorizar el acceso. El código solicita únicamente el scope drive.file. Con ese alcance, NEXUS crea su propia carpeta raíz y administra los archivos que crea dentro de ella; no necesita leer ni modificar todo tu Drive. Si ya existe una carpeta homónima creada manualmente, el scope drive.file podría no verla y se crearía una raíz adicional de NEXUS VIDEO AI; el motor no intenta acceder a carpetas ajenas a la app.

La subida usa carga reanudable (resumable) y después consulta cada archivo para comprobar tamaño y, cuando Drive devuelve el campo, MD5. Los reintentos de carga no vuelven a renderizar el vídeo.

## Preparación en Google Cloud

1. Abre https://console.cloud.google.com/ y crea un proyecto dedicado, por ejemplo NEXUS VIDEO AI.
2. En APIs & Services → Library, busca Google Drive API y pulsa Enable.
3. No habilites Billing ni vincules una tarjeta. Si la consola te exige activar facturación para continuar, detente y avísame; no aceptes ni crees una cuenta de facturación.
4. Abre Google Auth Platform → Branding y configura el nombre de la aplicación y el correo de soporte.
5. En Audience, usa External si tu cuenta es Gmail personal y añade tu propia cuenta en Test users para realizar la autorización.
6. En Data Access, solicita únicamente:
   https://www.googleapis.com/auth/drive.file
7. En Google Auth Platform → Clients, crea un OAuth Client ID de tipo Web application.
8. En Authorized redirect URIs añade exactamente:
   https://developers.google.com/oauthplayground
9. Descarga el JSON de credenciales OAuth y guárdalo de forma privada. No lo subas al repositorio ni lo pegues en este chat.

## Obtener el refresh token sin instalar programas

1. Abre https://developers.google.com/oauthplayground.
2. Pulsa el icono de configuración y marca Use your own OAuth credentials.
3. Introduce el Client ID y Client Secret de tu aplicación web.
4. Comprueba que OAuth flow sea Server-side, Access type sea Offline y Force prompt sea Consent Screen.
5. En Step 1, introduce el scope https://www.googleapis.com/auth/drive.file y autoriza con la cuenta de Google donde guardarás los vídeos.
6. En Step 2, pulsa Exchange authorization code for tokens.
7. Copia el refresh_token. No lo compartas en el chat.

**Importante sobre Testing:** Google indica que los refresh tokens de proyectos External con estado de publicación Testing caducan a los 7 días. Para uso continuado, revisa la opción Publishing status → In production. El scope drive.file es el alcance reducido que se usa en este motor. No solicites scopes amplios ni actives facturación para intentar evitar la expiración.

## Guardar secretos en GitHub

En el repositorio, abre Settings → Secrets and variables → Actions → New repository secret y crea:

- GOOGLE_OAUTH_CLIENT_JSON: contenido completo del JSON descargado de OAuth Client.
- GOOGLE_OAUTH_REFRESH_TOKEN: refresh_token obtenido en OAuth Playground.
- MAKE_RESULT_WEBHOOK_URL: URL privada del webhook NEXUS_V4_GENERATION_CALLBACK.
- MAKE_WEBHOOK_API_KEY: API key de autenticación de ese webhook.

No crees variables públicas para esos valores. No incluyas credenciales en commits, README, logs ni artefactos. Los secretos solo se inyectan al paso de Drive o al callback de Make.

## Carpetas creadas automáticamente

La primera ejecución crea una carpeta raíz propia llamada NEXUS VIDEO AI y su estructura:

- VIDEOS/YYYY/MM/<request_id>/
- AUDIOS/<request_id>/muestras_de_voz/
- HISTORIAS/<request_id>/
- INFORMES/<request_id>/
- ERRORES/<request_id>/

Cada request_id tiene su propio destino. Si se repite la misma solicitud de subida, el cargador busca el nombre dentro de su carpeta y compara el contenido; no crea copias redundantes si el archivo ya coincide. Los archivos ocupan espacio de tu cuota de Google Drive, según el almacenamiento disponible en tu cuenta.

## Verificación y recuperación

- La subida es reanudable y tiene hasta tres intentos por archivo.
- Tras subir, se consulta el archivo en Drive y se comprueba tamaño y MD5 cuando está disponible.
- Si falla la carga, el workflow conserva el directorio local como artefacto de GitHub Actions y registra el error.
- Para reintentar sin renderizar, ejecuta el workflow V4 con operation=upload_only, el mismo request_id y el source_run_id de la ejecución original. El artefacto debe seguir dentro de su periodo de retención.
- El código no transporta el MP4 a través de Make.

## Costes y límites

La documentación de Google describe el uso estándar de Drive API como disponible sin coste adicional dentro de sus límites. Google también documenta cuotas y cambios de límites para 2026, con posibles cargos por uso que supere umbrales diarios cuando la facturación esté habilitada. Por eso esta configuración no vincula facturación ni solicita aumentos de cuota. Si se alcanza un límite, la carga debe fallar de forma visible y reintentarse después; no se debe habilitar facturación automáticamente.

Fuentes oficiales:
- https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- https://developers.google.com/workspace/drive/api/guides/manage-uploads
- https://developers.google.com/identity/protocols/oauth2/
- https://developers.google.com/oauthplayground
- https://developers.google.com/workspace/drive/api/guides/limits
