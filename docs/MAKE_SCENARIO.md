# Make.com: escenario de registro (sin activar programación)

1. En Make crea un escenario nuevo.
2. Añade Webhooks → Custom webhook y crea un webhook llamado NEXUS VIDEO AI result.
3. Copia la URL y guárdala en GitHub → Settings → Secrets and variables → Actions como MAKE_WEBHOOK_URL.
4. Añade un módulo Google Sheets opcional o un Data Store para registrar status, title, created_at, duration_seconds y drive.webViewLink.
5. Añade un filtro para distinguir rendered, uploaded_and_verified y failure.
6. Deja el escenario en modo manual o apagado hasta que la primera prueba esté aprobada.

El payload solo contiene metadatos y enlaces. El MP4 se carga directamente desde GitHub Actions a Drive; Make no recibe archivos grandes. No configures tres ejecuciones diarias todavía. No uses Make para publicar en redes.

Para activar el inicio del workflow desde Make en una fase posterior hará falta un token de GitHub con permisos mínimos para ejecutar Actions. No se almacena en el panel del navegador y no se activa en esta fase.
