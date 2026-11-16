from __future__ import annotations
import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

def send(status=None, extra=None):
    url = os.getenv("MAKE_RESULT_WEBHOOK_URL", "").strip()
    api_key = os.getenv("MAKE_WEBHOOK_API_KEY", "").strip()
    if not url or not api_key:
        print("Make callback no configurado; se conserva el resultado como artefacto de GitHub.")
        return False
    request_id = os.getenv("REQUEST_ID", "")
    out = Path("output") / request_id
    metadata = {}
    for name in ("metadata.json",):
        p = out / name
        if p.exists():
            metadata = json.loads(p.read_text(encoding="utf-8"))
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_url = ""
    if os.getenv("GITHUB_SERVER_URL") and os.getenv("GITHUB_REPOSITORY") and run_id:
        run_url = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}"
    error_logs = {}
    for log_name in ("render_error.log", "drive_upload.log"):
        error_log = out / "errors" / log_name
        if error_log.exists():
            error_logs[log_name] = error_log.read_text(encoding="utf-8", errors="replace")[-3000:]
    manifest_path = out / "drive_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    payload = {
        "schema_version": "1.0",
        "event": "generation.status",
        "project": "NEXUS VIDEO AI",
        "version": "V4",
        "request_id": request_id,
        "status": status or os.getenv("NEXUS_STATUS", "unknown"),
        "run_id": run_id,
        "run_url": run_url,
        "artifact_name": os.getenv("ARTIFACT_NAME", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "extra": extra or {"error_logs": error_logs, "drive_manifest": manifest},
        "social_publishing": False
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for attempt in range(3):
        try:
            req = Request(url, data=body, headers={
                "Content-Type": "application/json",
                "x-make-apikey": api_key,
                "User-Agent": "NEXUS-VIDEO-AI-V4"
            }, method="POST")
            with urlopen(req, timeout=25) as response:
                if response.status not in (200, 201, 202, 204):
                    raise RuntimeError(f"Make devolvió HTTP {response.status}")
                print(f"Make callback aceptado: status={payload['status']} HTTP={response.status}")
                return True
        except Exception as exc:
            print(f"Callback Make intento {attempt+1}/3 falló: {exc}", file=sys.stderr)
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError("No se pudo notificar el estado a Make tras 3 intentos.")

if __name__ == "__main__":
    send(os.getenv("NEXUS_STATUS", "unknown"))
