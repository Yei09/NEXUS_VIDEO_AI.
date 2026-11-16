import json, os
from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES=["https://www.googleapis.com/auth/drive"]

def main():
    folder=os.getenv("GOOGLE_DRIVE_FOLDER_ID","").strip()
    if not folder:
        print("GOOGLE_DRIVE_FOLDER_ID no configurado; carga omitida."); return
    oauth_json=os.getenv("GOOGLE_OAUTH_CLIENT_JSON","")
    refresh=os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN","")
    service_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON","")
    if oauth_json and refresh:
        client=json.loads(oauth_json)
        data=client.get("installed") or client.get("web") or client
        creds=Credentials(token=None,refresh_token=refresh,token_uri="https://oauth2.googleapis.com/token",client_id=data["client_id"],client_secret=data["client_secret"],scopes=SCOPES)
    elif service_json:
        print("Aviso: la cuenta de servicio requiere una unidad compartida de Google Workspace; para Mi unidad usa OAuth de usuario.")
        info=json.loads(service_json)
        creds=service_account.Credentials.from_service_account_info(info,scopes=SCOPES)
    else:
        print("Credenciales de Google Drive no configuradas; carga omitida."); return
    drive=build("drive","v3",credentials=creds,cache_discovery=False)
    meta=json.loads(Path("output/metadata.json").read_text(encoding="utf-8")); mp4=Path(meta["file"])
    media=MediaFileUpload(str(mp4),mimetype="video/mp4",resumable=True,chunksize=8*1024*1024)
    req=drive.files().create(body={"name":mp4.name,"parents":[folder]},media_body=media,fields="id,name,mimeType,size,webViewLink,parents")
    result=None
    while result is None: _,result=req.next_chunk()
    check=drive.files().get(fileId=result["id"],fields="id,name,mimeType,size,webViewLink,parents").execute()
    if check.get("mimeType")!="video/mp4" or int(check.get("size",0))!=mp4.stat().st_size: raise RuntimeError("No coincide el tamaño o tipo MIME del archivo subido.")
    meta["drive"]=check; meta["status"]="uploaded_and_verified"
    Path("output/metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"drive_file":check},ensure_ascii=False))
if __name__=="__main__": main()
