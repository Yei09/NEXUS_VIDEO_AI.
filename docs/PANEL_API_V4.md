# NEXUS VIDEO AI V4 — interfaz del futuro panel

El panel no se marca como implementado ni conectado en esta versión. El contrato de integración está definido para que el panel utilice Make como backend y nunca tenga acceso directo a secretos de GitHub o Google.

## Solicitar una generación

POST al webhook NEXUS_V4_GENERATION_REQUEST.

Payload: ver V4_ARCHITECTURE.md. El panel genera un UUID por solicitud, lo conserva y muestra el estado pending. No reenvía el mismo UUID para crear otro render.

## Consultar un trabajo

POST al webhook NEXUS_V4_PANEL_QUERY:

    {
      "action": "get",
      "request_id": "7d83b3ac-59fd-4b4b-a311-bb68c37ad02e"
    }

Respuesta esperada desde Make Data Store:

    {
      "request_id": "7d83b3ac-59fd-4b4b-a311-bb68c37ad02e",
      "status": "completed",
      "stage": "done",
      "run_id": "123456789",
      "run_url": "https://github.com/Yei09/NEXUS_VIDEO_AI./actions/runs/123456789",
      "artifact_name": "nexus-v4-7d83b3ac-59fd-4b4b-a311-bb68c37ad02e",
      "drive_root_url": "https://drive.google.com/drive/folders/...",
      "drive_files": [],
      "error_message": null,
      "updated_at": "2026-11-16T12:00:00Z"
    }

Los enlaces de Drive se toman del objeto metadata.drive devuelto por el callback. El panel puede mostrar vídeo, narración, historia, informes y miniatura con los webViewLink de cada archivo.

## Consultar historial

POST al webhook NEXUS_V4_PANEL_QUERY:

    {
      "action": "list",
      "limit": 20,
      "status": "completed"
    }

Make ejecuta Data Store > Search Records con un límite máximo de 50 y orden descendente por created_at. Si status se omite, devuelve los últimos trabajos de cualquier estado.

## Configuración del generador

El panel debe ofrecer controles para:
- Categoría: paranormal, casa_embrujada, leyenda_urbana, criaturas, psicologico.
- Duración objetivo: 30–60 segundos.
- Voz: cuatro IDs Piper aceptados por el workflow.
- Velocidad: 0.75–1.25.
- Tono: -2.0 a +2.0 semitonos.
- Intensidad: calm, mysterious, urgent.
- Audiciones de voz: true/false.

Los valores se envían en el mismo JSON de generación; Make valida antes de despachar.

## Seguridad del panel

- El navegador no debe contener MAKE webhook URL, API key de Make, token GitHub ni credenciales Google.
- Un backend/proxy privado debe llamar los webhooks de Make con la API key correspondiente.
- Las consultas de estado deben validar que el usuario tiene permiso para consultar el request_id.
- Los enlaces de Drive deben ser privados y sujetos a los permisos de tu cuenta. El motor no cambia el acceso a "cualquiera con el enlace".
- No se incluye una interfaz HTML estática que simule estas funciones. El panel real requiere implementar el backend de sesión/autorización y conectar los tres webhooks de Make una vez creados.
