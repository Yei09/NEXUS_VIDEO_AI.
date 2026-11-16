# Configuración y prueba manual

## Seguridad predeterminada
- Solo ejecución manual mediante workflow_dispatch. No hay schedule.
- No se publica en TikTok, Instagram, YouTube ni otras redes.
- El MP4 se guarda como artefacto de Actions. Drive se activa al configurar credenciales.
- Make recibe metadatos únicamente, nunca el MP4.
- No habilites facturación. Si Google exige tarjeta o facturación, detente.

## Google Drive
1. Crea en Drive una carpeta llamada NEXUS VIDEO AI.
2. En Google Cloud Console crea un proyecto sin vincular facturación.
3. Habilita Google Drive API.
4. Crea una cuenta de servicio y descarga su clave JSON.
5. Comparte la carpeta con el correo client_email de esa cuenta de servicio como Editor.
6. Copia el ID de la carpeta desde su URL.
7. En GitHub abre Settings → Secrets and variables → Actions:
   - Secret GOOGLE_SERVICE_ACCOUNT_JSON: pega el JSON completo.
   - Variable GOOGLE_DRIVE_FOLDER_ID: pega el ID de la carpeta.
8. Nunca guardes la clave en el repositorio, issues, commits o conversaciones.

El cargador usa la API oficial con carga reanudable y verifica el MIME type y el tamaño del archivo después de subirlo. La cuenta de servicio debe tener acceso a la carpeta.

## Piper TTS
El workflow instala Piper TTS y descarga la voz española es_MX-ald-medium. Motor y modelo tienen licencias distintas; comprueba el MODEL_CARD de la voz antes de uso comercial. Se puede sustituir con PIPER_VOICE, PIPER_MODEL_URL y PIPER_CONFIG_URL en el workflow, tras verificar origen y licencia.

## Ejecutar el vídeo de prueba
1. Abre Actions.
2. Selecciona NEXUS Video - Manual Test.
3. Pulsa Run workflow. Usa el guion predeterminado o uno de al menos 45 palabras.
4. Espera a que termine.
5. Revisa el paso Render narrated MP4 y el artefacto nexus-video-manual-test.
6. Si Drive está configurado, revisa el paso Upload and verify Google Drive y el estado uploaded_and_verified en output/metadata.json.

La validación comprueba vídeo H.264, audio AAC, resolución 1080×1920 y duración de 25–75 segundos.

## Make.com (opcional)
Crea un escenario con Webhooks → Custom webhook. Guarda su URL como secreto MAKE_WEBHOOK_URL en GitHub Actions. El sistema enviará estado y metadatos al finalizar. No programes escenarios ni automatices disparadores todavía. La integración futura para iniciar workflows desde Make requiere un token de GitHub con permisos mínimos y quedará apagada hasta que se apruebe.

## Panel
dashboard/ es un panel estático inicial. El botón abre el workflow manual en GitHub. Todavía no tiene backend, estado en vivo ni secretos conectados. No introduzcas tokens en el navegador. La futura API deberá usar un Worker y secretos privados.

## Costos
No se solicita ni habilita facturación. GitHub Actions en repositorios públicos ofrece runners estándar gratuitos según los términos y límites vigentes de GitHub. Drive utiliza el almacenamiento disponible de la cuenta. Si un proveedor solicita tarjeta o activar facturación, cancela.
