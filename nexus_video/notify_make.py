import json, os
from pathlib import Path
from urllib.request import Request,urlopen

def main():
    url=os.getenv("MAKE_WEBHOOK_URL","").strip()
    if not url: print("MAKE_WEBHOOK_URL ausente; aviso omitido."); return
    p={"project":"NEXUS VIDEO AI","status":os.getenv("JOB_STATUS","unknown"),"metadata":json.loads(Path("output/metadata.json").read_text()) if Path("output/metadata.json").exists() else {},"social_publishing":False}
    req=Request(url,data=json.dumps(p,ensure_ascii=False).encode(),headers={"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=20) as r:
        if r.status not in (200,201,202,204): raise RuntimeError(f"Webhook HTTP {r.status}")
        print(f"Make aceptó metadatos: HTTP {r.status}")
if __name__=="__main__": main()
