from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageStat

def video(root):
    items=sorted(Path(root).rglob("*.mp4"))
    if not items: raise FileNotFoundError(f"No MP4 en {root}")
    return items[0]

def metadata(root):
    items=list(Path(root).rglob("metadata.json"))
    if not items: raise FileNotFoundError(f"No metadata.json en {root}")
    return json.loads(items[0].read_text(encoding="utf-8"))

def sample(mp4, event, out):
    t=float(event.get("start_seconds",0))+float(event.get("duration_seconds",0))*.55
    subprocess.run(["ffmpeg","-y","-ss",f"{t:.3f}","-i",str(mp4),"-frames:v","1","-q:v","2",str(out)],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return t

def main():
    if len(sys.argv)!=4: raise SystemExit("Uso: compare_v42_v421.py V42_DIR V421_DIR OUTPUT_DIR")
    old_root,new_root,out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=True)
    old_mp4,new_mp4=video(old_root),video(new_root)
    old_meta,new_meta=metadata(old_root),metadata(new_root)
    a,b=old_meta["events"],new_meta["events"]
    if len(a)!=6 or len(b)!=6: raise RuntimeError("Se requieren seis eventos por versión.")
    cw,ch=270,480
    sheet=Image.new("RGB",(cw*2,(ch+34)*6),(7,9,14))
    draw=ImageDraw.Draw(sheet); rows=[]
    for i,(ea,eb) in enumerate(zip(a,b),1):
        pa=out/f"v4.2-scene-{i:02d}.jpg"; pb=out/f"v4.2.1-scene-{i:02d}.jpg"
        ta=sample(old_mp4,ea,pa); tb=sample(new_mp4,eb,pb)
        ia=Image.open(pa).convert("RGB").resize((cw,ch)); ib=Image.open(pb).convert("RGB").resize((cw,ch))
        score=round(sum(ImageStat.Stat(ImageChops.difference(ia,ib)).mean)/3,3)
        y=(i-1)*(ch+34); sheet.paste(ia,(0,y+34)); sheet.paste(ib,(cw,y+34))
        draw.text((8,y+10),f"V4.2 · {ea.get('scene','scene')}",fill=(245,245,245))
        draw.text((cw+8,y+10),f"V4.2.1 · {eb.get('scene','scene')}",fill=(245,245,245))
        rows.append({"index":i,"scene_v42":ea.get("scene"),"scene_v421":eb.get("scene"),
                     "v42_timestamp_seconds":round(ta,3),"v421_timestamp_seconds":round(tb,3),
                     "mean_absolute_rgb_difference":score,"v42_frame":pa.name,"v421_frame":pb.name})
    sheet_path=out/"v4.2-vs-v4.2.1-contact-sheet.jpg"; sheet.save(sheet_path,quality=92)
    report={"baseline_run_id":43821467642,"baseline_commit":"1c94b9d5b60fa9c9446893383e9eea1466f168a4",
            "scene_count":6,"comparison_method":"paired MP4 event-midpoint frames; RGB difference is descriptive, not a quality score",
            "scenes":rows,"contact_sheet":sheet_path.name}
    (out/"comparison_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
