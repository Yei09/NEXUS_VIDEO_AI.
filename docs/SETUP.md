# Configuración y prueba de NEXUS VIDEO AI

## Objetivo
El producto genera historias originales de terror en español para Shorts, Reels y TikTok: terror psicológico, paranormal, leyendas urbanas, casas embrujadas y criaturas. Cada ejecución manual produce una historia, no una publicación.

## Seguridad predeterminada
- Solo workflow_dispatch manual. No existe programación diaria.
- No se publica en redes sociales.
- No se solicita ni activa facturación.
- Google Drive y Make son opcionales y se omiten si no están configurados.
- No pegues claves, tokens ni contraseñas en el repositorio ni en el chat.

## Ejecutar una historia de prueba
1. Abre Actions en GitHub.
2. Selecciona NEXUS Video - Manual Horror Test.
3. Pulsa Run workflow y elige la categoría.
4. Espera a que finalice el proceso.
5. Descarga el artefacto nexus-horror-story-test.
6. Revisa output/metadata.json y output/script.txt incluidos en el ZIP.

El motor usa Piper TTS en español, crea ilustraciones de escenas con Python/Pillow y sintetiza un ambiente de terror original con FFmpeg. Valida H.264, AAC, 1080×1920 y duración de 30–60 segundos. La duración exacta depende de la velocidad de narración y el guion; si queda fuera del rango, la ejecución falla para no entregar un vídeo que incumpla.

## Google Drive (opcional)
Para subir a Mi unidad se usa OAuth de tu cuenta:
1. Crea una carpeta NEXUS VIDEO AI en Google Drive.
2. En Google Cloud Console crea un proyecto sin vincular facturación y comprueba que no te solicite habilitarla.
3. Habilita Google Drive API.
4. Configura consentimiento OAuth y crea un cliente OAuth web.
5. Para OAuth Playground, añade https://developers.google.com/oauthplayground como URI de redirección autorizada. En Google OAuth Playground activa Use your own OAuth credentials y añade el client ID y client secret. Solicita el scope https://www.googleapis.com/auth/drive, autoriza tu cuenta y genera un refresh token.
6. En GitHub → Settings → Secrets and variables → Actions configura:
   - Secret GOOGLE_OAUTH_CLIENT_JSON: JSON del cliente OAuth.
   - Secret GOOGLE_OAUTH_REFRESH_TOKEN: refresh token.
   - Variable GOOGLE_DRIVE_FOLDER_ID: ID de la carpeta Drive.
7. Ejecuta manualmente el workflow y comprueba el paso de carga y verificación.

Si Google exige tarjeta o activar facturación, cancela y deja Drive pendiente. Si el consentimiento OAuth queda en Testing para un usuario externo, el refresh token puede caducar a los siete días; no habilites la programación diaria hasta resolverlo. No compartas las credenciales conmigo.

## Make.com (opcional, solo registro)
Crea Webhooks → Custom webhook y guarda la URL como secreto MAKE_WEBHOOK_URL en GitHub Actions. Recibirá metadatos de estado, título y enlace, nunca el MP4. Deja el escenario apagado/manual. No configures horarios ni publicación.

## Panel
dashboard/ contiene el primer panel informativo con enlace a la prueba manual. Aún no es un panel operativo con historial vivo ni backend; no introduzcas tokens en el navegador.

## Calidad y licencias
Piper engine y el modelo de voz tienen licencias diferentes. Revisa el MODEL_CARD del modelo antes de uso comercial. El arte visual y los tonos ambientales de esta prueba se generan localmente; no dependen de bancos de stock ni pistas musicales con copyright. El sonido sintetizado es un ambiente básico, no una biblioteca Foley profesional.
