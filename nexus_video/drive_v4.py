from __future__ import annotations
import json, os, time, mimetypes, hashlib
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_MIME = "application/vnd.google-apps.folder"

def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta el secreto/variable {name}.")
    return value

def drive_client():
    client = json.loads(required_env("GOOGLE_OAUTH_CLIENT_JSON"))
    config = client.get("installed") or client.get("web") or client
    refresh = required_env("GOOGLE_OAUTH_REFRESH_TOKEN")
    creds = Credentials(
        token=None, refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config["client_id"], client_secret=config["client_secret"],
        scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def find_folder(drive, name, parent_id):
    safe = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name='{safe}' and mimeType='{FOLDER_MIME}' and '{parent_id}' in parents and trashed=false"
    result = drive.files().list(q=q, pageSize=100, fields="files(id,name,mimeType,parents,webViewLink)").execute()
    matches = result.get("files", [])
    return matches[0] if matches else None

def ensure_folder(drive, name, parent_id):
    found = find_folder(drive, name, parent_id)
    if found:
        return found
    created = drive.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        fields="id,name,mimeType,parents,webViewLink"
    ).execute()
    return created

def upload_one(drive, path, parent_id):
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    local_size = path.stat().st_size
    local_md5 = hashlib.md5(path.read_bytes()).hexdigest()
    safe = path.name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"name='{safe}' and '{parent_id}' in parents and trashed=false"
    existing = drive.files().list(q=q, pageSize=100, fields="files(id,name,mimeType,size,md5Checksum,webViewLink,parents)").execute().get("files", [])
    target = next((x for x in existing if x.get("name") == path.name), None)
    media = MediaFileUpload(str(path), mimetype=mime, resumable=True, chunksize=8*1024*1024)
    for attempt in range(3):
        try:
            if target and int(target.get("size", -1)) == local_size and target.get("md5Checksum") == local_md5:
                result = target
            elif target:
                result = drive.files().update(fileId=target["id"], media_body=media,
                    fields="id,name,mimeType,size,md5Checksum,webViewLink,parents").execute()
            else:
                result = drive.files().create(body={"name": path.name, "parents": [parent_id]},
                    media_body=media, fields="id,name,mimeType,size,md5Checksum,webViewLink,parents").execute()
            check = drive.files().get(fileId=result["id"],
                fields="id,name,mimeType,size,md5Checksum,webViewLink,parents").execute()
            if int(check.get("size", -1)) != local_size:
                raise RuntimeError(f"Tamaño incorrecto después de subir {path.name}.")
            if check.get("md5Checksum") and check["md5Checksum"] != local_md5:
                raise RuntimeError(f"MD5 incorrecto después de subir {path.name}.")
            return check
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
            # Recreate MediaFileUpload after a failed resumable attempt.
            media = MediaFileUpload(str(path), mimetype=mime, resumable=True, chunksize=8*1024*1024)
    raise RuntimeError(f"No se pudo subir {path.name}.")

def main():
    request_id = required_env("REQUEST_ID")
    root_name = os.getenv("GOOGLE_DRIVE_ROOT_NAME", "NEXUS VIDEO AI").strip() or "NEXUS VIDEO AI"
    out = Path("output") / request_id
    meta_path = out / "metadata.json"
    if not meta_path.exists():
        raise RuntimeError(f"No existe {meta_path}; no se puede subir una generación incompleta.")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    if metadata.get("request_id") != request_id:
        raise RuntimeError("El request_id de metadata.json no coincide con la solicitud.")
    drive = drive_client()
    # The app creates its own root folder; drive.file scope can then manage its descendants.
    root = find_folder(drive, root_name, "root")
    if not root:
        root = drive.files().create(body={"name": root_name, "mimeType": FOLDER_MIME},
            fields="id,name,mimeType,webViewLink").execute()
    videos = ensure_folder(drive, "VIDEOS", root["id"])
    year = metadata.get("created_at", "")[:4] or time.strftime("%Y")
    month = metadata.get("created_at", "")[5:7] or time.strftime("%m")
    video_year = ensure_folder(drive, year, videos["id"])
    video_month = ensure_folder(drive, month, video_year["id"])
    video_request = ensure_folder(drive, request_id, video_month["id"])
    audios = ensure_folder(drive, "AUDIOS", root["id"])
    audio_request = ensure_folder(drive, request_id, audios["id"])
    voice_samples = ensure_folder(drive, "muestras_de_voz", audio_request["id"])
    stories = ensure_folder(drive, "HISTORIAS", root["id"])
    story_request = ensure_folder(drive, request_id, stories["id"])
    reports = ensure_folder(drive, "INFORMES", root["id"])
    report_request = ensure_folder(drive, request_id, reports["id"])
    errors = ensure_folder(drive, "ERRORES", root["id"])
    error_request = ensure_folder(drive, request_id, errors["id"])

    uploaded = []
    for path in sorted((out/"videos").glob("*")) if (out/"videos").exists() else []:
        if path.is_file():
            uploaded.append(upload_one(drive, path, video_request["id"]))
    thumb = out/"thumbnail.jpg"
    if thumb.exists():
        uploaded.append(upload_one(drive, thumb, video_request["id"]))
    for name in ("narration.wav", "audio_mix.wav", "music.wav", "effects.wav"):
        path = out/"audios"/name
        if path.exists():
            uploaded.append(upload_one(drive, path, audio_request["id"]))
    samples = out/"audios"/"voice_samples"
    if samples.exists():
        for path in sorted(samples.glob("*.wav")):
            uploaded.append(upload_one(drive, path, voice_samples["id"]))
    for name in ("story.txt", "script.txt", "story_events.json"):
        path = out/name
        if path.exists():
            uploaded.append(upload_one(drive, path, story_request["id"]))
    for name in ("metadata.json", "motion_report.json", "render_report.json"):
        path = out/name
        if path.exists():
            # metadata.json is uploaded again after the manifest is embedded below.
            if name != "metadata.json":
                uploaded.append(upload_one(drive, path, report_request["id"]))
    error_dir = out/"errors"
    if error_dir.exists():
        for path in sorted(error_dir.rglob("*")):
            if path.is_file():
                uploaded.append(upload_one(drive, path, error_request["id"]))

    manifest = {
        "request_id": request_id, "root_folder": root, "folders": {
            "video": video_request, "audio": audio_request, "stories": story_request,
            "reports": report_request, "errors": error_request
        },
        "files": uploaded, "verified_file_count": len(uploaded),
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    (out/"drive_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata["drive"] = {
        "status": "uploaded_and_verified", "root_folder": root,
        "folders": manifest["folders"], "files": uploaded,
        "verified_file_count": len(uploaded), "manifest": "drive_manifest.json"
    }
    metadata["drive_status"] = "uploaded_and_verified"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    uploaded_meta = upload_one(drive, meta_path, report_request["id"])
    uploaded_manifest = upload_one(drive, out/"drive_manifest.json", report_request["id"])
    print(json.dumps({"status": "uploaded_and_verified", "request_id": request_id,
        "drive_root": root.get("webViewLink"), "verified_file_count": len(uploaded)+2,
        "metadata": uploaded_meta, "manifest": uploaded_manifest}, ensure_ascii=False))

if __name__ == "__main__":
    main()
