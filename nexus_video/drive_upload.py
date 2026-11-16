import json, os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    raw=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON","")
    if not raw: raise RuntimeError("Falta GOOGLE_SERVICE_ACCOUNT_JSON.")
    creds=service_account.Credentials.from_service_account_info(json.loads(raw),scopes=["https://www.googleapis.com/auth/drive"])
    drive=build("drive","v3",credentials=creds,cache_discovery=False)
    folder=os.getenv("GOOGLE_DRIVE_FOLDER_ID","").strip()
    if not folder: raise RuntimeError("Falta GOOGLE_DRIVE_FOLDER_ID.")
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
