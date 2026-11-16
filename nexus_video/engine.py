from __future__ import annotations
import json, os, shutil, subprocess, sys, textwrap, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"; WORK=ROOT/"work"; W,H=1080,1920
DEMO=("¿Sabías que tu cerebro sigue trabajando mientras duermes? Durante el sueño organiza recuerdos, procesa emociones y refuerza aprendizajes. Por eso descansar no es perder el tiempo: es una parte esencial de aprender. Una rutina sencilla ayuda: baja la luz, evita pantallas antes de acostarte y procura dormir a una hora parecida cada noche. Tu descanso también merece un lugar en tu lista de prioridades.")

def run(cmd, input_text=None):
    p=subprocess.run(cmd,input=input_text,text=True,capture_output=True)
    if p.returncode: raise RuntimeError(f"Fallo: {' '.join(cmd)}\n{p.stderr[-2500:]}")
    return p.stdout.strip()

def duration(p):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)]))

def main():
    for tool in ("ffmpeg","ffprobe","piper"):
        if not shutil.which(tool): raise RuntimeError("No se encontró "+tool)
    OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    title=os.getenv("VIDEO_TITLE","Lo que tu cerebro hace mientras duermes")
    script=os.getenv("VIDEO_SCRIPT",DEMO).strip()
    if len(script.split())<45: raise RuntimeError("El guion necesita al menos 45 palabras.")
    voice=os.getenv("PIPER_VOICE","es_MX-ald-medium")
    base=f"https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/{voice}.onnx"
    model=WORK/"voice.onnx"; config=WORK/"voice.onnx.json"
    for url,path in ((os.getenv("PIPER_MODEL_URL",base),model),(os.getenv("PIPER_CONFIG_URL",base+".json"),config)):
        if not path.exists(): print("Descargando "+path.name); urllib.request.urlretrieve(url,path)
    if model.stat().st_size<100000 or config.stat().st_size<100: raise RuntimeError("Modelo Piper incompleto.")
    wav=WORK/"narration.wav"
    run(["piper","--model",str(model),"--config",str(config),"--output_file",str(wav)],script)
    seconds=duration(wav)
    if not 25<=seconds<=75: raise RuntimeError(f"Duración de narración no válida: {seconds:.1f}s")
    im=Image.new("RGB",(W,H)); px=im.load()
    for y in range(H):
        t=y/H
        for x in range(W):
            glow=max(0,1-(((x-800)/900)**2+((y-350)/700)**2))*24
            px[x,y]=(int(10+15*t+glow),int(18+20*t+glow),int(38+35*t+glow))
    d=ImageDraw.Draw(im)
    try:
        big=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",76)
        small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",34)
    except OSError: big=small=ImageFont.load_default()
    d.rounded_rectangle((72,150,1008,1770),radius=48,outline=(65,100,160),width=3)
    d.text((112,260),"NEXUS VIDEO AI",font=small,fill=(130,190,255))
    y=690
    for line in textwrap.wrap(title,width=19):
        d.text((112,y),line,font=big,fill=(248,250,255)); y+=105
    d.text((112,1580),"CONOCIMIENTO EN 60 SEGUNDOS",font=small,fill=(170,190,220))
    bg=WORK/"background.png"; im.save(bg)
    words=script.split(); chunks=[" ".join(words[i:i+8]) for i in range(0,len(words),8)]
    def ts(v):
        ms=int(v*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    srt=WORK/"captions.srt"; step=seconds/len(chunks)
    with srt.open("w",encoding="utf-8") as f:
        for i,c in enumerate(chunks): f.write(f"{i+1}\n{ts(i*step)} --> {ts(min(seconds,(i+1)*step))}\n{c}\n\n")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); mp4=OUT/f"nexus-video-{stamp}.mp4"
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=work/captions.srt:force_style='FontName=DejaVu Sans,FontSize=19,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=170'"
    run(["ffmpeg","-y","-loop","1","-i",str(bg),"-i",str(wav),"-vf",vf,"-c:v","libx264","-preset","veryfast","-tune","stillimage","-pix_fmt","yuv420p","-r","30","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",str(mp4)])
    probe=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(mp4)]))
    vs=next((x for x in probe["streams"] if x.get("codec_type")=="video"),None)
    aus=next((x for x in probe["streams"] if x.get("codec_type")=="audio"),None)
    if not vs or not aus or vs.get("width")!=W or vs.get("height")!=H: raise RuntimeError("Validación de audio/vídeo o resolución fallida.")
    final=float(probe["format"]["duration"])
    if not 25<=final<=75: raise RuntimeError("Duración final fuera del rango esperado.")
    meta={"status":"rendered","created_at":datetime.now(timezone.utc).isoformat(),"title":title,"script":script,"file":str(mp4),"size_bytes":mp4.stat().st_size,"duration_seconds":round(final,2),"width":W,"height":H,"voice":voice,"social_publishing":False}
    (OUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"script.txt").write_text(script,encoding="utf-8")
    print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=="__main__":
    try: main()
    except Exception as e: print("NEXUS VIDEO AI ERROR:",e,file=sys.stderr); raise
