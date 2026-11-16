from __future__ import annotations
import json, os, random, shutil, subprocess, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"output"; WORK=ROOT/"work"; W,H=1080,1920
STORIES=[
("La llamada del sótano","terror psicológico",["Si recibes una llamada desde un teléfono desconectado, no contestes.","Anoche, Clara escuchó sonar el viejo teléfono del sótano. Su abuela llevaba diez años muerta y aquel aparato no tenía cable.","Contestó. Al otro lado, su propia voz susurró: «No bajes. Estoy detrás de ti».","Clara soltó el auricular. Entonces oyó tres golpes bajo el suelo… y el teléfono volvió a sonar.","Esta vez, la llamada venía del móvil que llevaba en la mano."]),
("La casa que respira","casa embrujada",["La casa llevaba veinte años vacía, pero cada noche alguien encendía la luz del pasillo.","Cuando Mateo entró, encontró fotografías familiares con una persona más en cada imagen. Una figura alta, siempre detrás de quien tomaba la foto.","El suelo crujió. Las paredes se hincharon lentamente, como un pecho respirando.","Mateo corrió a la puerta, pero la casa había cambiado el pasillo. En la última fotografía, la figura ya estaba junto a él.","Y la puerta de salida apareció cerrada desde dentro."]),
("La última parada","leyenda urbana",["En esta ruta hay una parada que no aparece en ningún mapa.","A las 2:17, el autobús de Elena se detuvo frente a una estación abandonada. Subió una niña empapada y pidió bajar en el puente viejo.","El conductor palideció: aquel puente había desaparecido en una inundación hacía treinta años.","Elena miró por la ventana. Todos los pasajeros tenían el rostro de la niña.","Cuando el autobús arrancó, su asiento estaba mojado… y su boleto decía: solo ida."]),
("Algo bajo la cama","criaturas",["Lo peor de vivir solo es descubrir que alguien conoce tus horarios.","Cada madrugada, Julián oía uñas arañando la madera bajo su cama. Pensó que era una tubería hasta que escuchó su nombre.","Una noche dejó el teléfono grabando. En el audio, su voz dormida decía: «Todavía no. Espera a que apague la luz».","Julián no había hablado en sueños. Al amanecer revisó la grabación y oyó una segunda respiración.","Venía de debajo de la cama… y se alejaba hacia la puerta."]),
("El reflejo equivocado","paranormal",["Si tu reflejo tarda en imitarte, no intentes comprobarlo otra vez.","Lucía se lavaba los dientes cuando vio que su reflejo seguía sonriendo después de que ella dejó de hacerlo.","Apagó la luz. En la oscuridad, el espejo se iluminó solo. Su reflejo levantó una mano y escribió desde el otro lado: «Déjame salir».","Lucía retrocedió. El reflejo no la siguió; se quedó quieto, mirando la puerta del baño.","Al girarse, escuchó el pestillo cerrarse detrás de ella."])]
def run(cmd):
 p=subprocess.run(cmd,text=True,capture_output=True)
 if p.returncode: raise RuntimeError(f"Fallo: {' '.join(cmd)}\n{p.stderr[-2500:]}")
 return p.stdout.strip()
def dur(p): return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)]))
def draw_scene(path,title,caption,i,n):
 im=Image.new("RGB",(W,H)); pix=im.load()
 for y in range(H):
  for x in range(W):
   glow=max(0,1-(((x-820)/700)**2+((y-300)/650)**2))*12
   pix[x,y]=(int(5+7*y/H+glow),int(7+8*y/H+glow*.3),int(16+18*y/H+glow))
 d=ImageDraw.Draw(im); d.ellipse((700,220,980,500),fill=(150,145,140),outline=(80,80,95),width=6)
 d.polygon([(0,1180),(150,850),(280,1180),(430,940),(600,1180),(790,860),(930,1180),(1080,900),(1080,1920),(0,1920)],fill=(8,10,18))
 d.polygon([(160,1160),(520,860),(880,1160)],fill=(12,14,24)); d.rectangle((240,1150,820,1580),fill=(10,12,20),outline=(65,63,78),width=8)
 for xx in (340,650): d.rectangle((xx,1240,xx+90,1390),fill=(145,95,60) if i==2 else (48,58,67),outline=(110,90,85),width=5)
 for yy in (1500,1600): d.ellipse((-160,yy-65,1250,yy+80),fill=(20,25,36))
 try: f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",58); sm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",28)
 except OSError: f=sm=ImageFont.load_default()
 d.text((75,155),"NEXUS · RELATOS DE TERROR",font=sm,fill=(200,70,80)); d.text((75,610),title,font=f,fill=(245,235,230))
 d.text((75,1740),caption[:58],font=sm,fill=(220,215,215)); d.text((950,1820),f"{i}/{n}",font=sm,fill=(200,80,90)); im.save(path)
def main():
 for t in ("ffmpeg","ffprobe","piper"):
  if not shutil.which(t): raise RuntimeError("No se encontró "+t)
 OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
 rng=random.Random(os.getenv("STORY_SEED") or datetime.now(timezone.utc).isoformat())
 s=next((x for x in STORIES if x[1]==os.getenv("HORROR_CATEGORY")),None) or rng.choice(STORIES)
 title,genre,parts=s; script=" ".join(parts)
 voice=os.getenv("PIPER_VOICE","es_MX-ald-medium"); base=f"https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/{voice}.onnx"
 model=WORK/"voice.onnx"; cfg=WORK/"voice.onnx.json"
 for url,p in ((os.getenv("PIPER_MODEL_URL",base),model),(os.getenv("PIPER_CONFIG_URL",base+".json"),cfg)):
  if not p.exists(): print("Descargando "+p.name); urllib.request.urlretrieve(url,p)
 if model.stat().st_size<100000 or cfg.stat().st_size<100: raise RuntimeError("Modelo Piper incompleto.")
 wav=WORK/"narration.wav"
 p=subprocess.run(["piper","--model",str(model),"--config",str(cfg),"--length_scale","1.12","--noise_scale","0.72","--noise_w","0.82","--output_file",str(wav)],input=script,text=True,capture_output=True)
 if p.returncode: raise RuntimeError("Piper TTS falló: "+p.stderr[-2000:])
 seconds=dur(wav)
 if not 30<=seconds<=60: raise RuntimeError(f"Duración de voz {seconds:.1f}s fuera de 30–60s.")
 imgs=[]
 for i,part in enumerate(parts):
  pth=WORK/f"scene-{i+1}.png"; draw_scene(pth,title,part,i+1,len(parts)); imgs.append(pth)
 concat=WORK/"scenes.txt"; each=seconds/len(imgs)
 with concat.open("w",encoding="utf-8") as f:
  for pth in imgs: f.write(f"file '{pth.resolve()}'\nduration {each:.4f}\n")
  f.write(f"file '{imgs[-1].resolve()}'\n")
 words=script.split(); chunks=[" ".join(words[i:i+6]) for i in range(0,len(words),6)]
 def ts(v):
  ms=int(v*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); sec,ms=divmod(ms,1000); return f"{h:02}:{m:02}:{sec:02},{ms:03}"
 with (WORK/"captions.srt").open("w",encoding="utf-8") as f:
  step=seconds/len(chunks)
  for i,c in enumerate(chunks): f.write(f"{i+1}\n{ts(i*step)} --> {ts(min(seconds,(i+1)*step))}\n{c}\n\n")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); mp4=OUT/f"nexus-terror-{stamp}.mp4"
 vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=work/captions.srt:force_style='FontName=DejaVu Sans,FontSize=34,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=190'"
 fc=f"[0:v]{vf}[v];[2:a]volume=0.18,lowpass=f=180[a1];[3:a]volume=0.07,lowpass=f=650,afade=t=out:st={max(0,seconds-3):.2f}:d=3[a2];[4:a]volume=0.035,tremolo=f=0.16:d=0.75[a3];[5:a]volume=0.025,tremolo=f=0.11:d=0.7[a4];[a1][a2][a3][a4]amix=inputs=4:duration=longest,volume=0.55[m];[1:a][m]amix=inputs=2:duration=first:weights='1 0.32'[a]"
 run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-i",str(wav),"-f","lavfi","-i",f"sine=frequency=48:sample_rate=44100:duration={seconds}","-f","lavfi","-i",f"anoisesrc=color=pink:amplitude=0.035:sample_rate=44100:duration={seconds}","-f","lavfi","-i",f"sine=frequency=130.81:sample_rate=44100:duration={seconds}","-f","lavfi","-i",f"sine=frequency=164.81:sample_rate=44100:duration={seconds}","-filter_complex",fc,"-map","[v]","-map","[a]","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-r","30","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",str(mp4)])
 probe=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(mp4)]))
 v=next((x for x in probe["streams"] if x.get("codec_type")=="video"),None); a=next((x for x in probe["streams"] if x.get("codec_type")=="audio"),None)
 if not v or not a or v.get("width")!=W or v.get("height")!=H or v.get("codec_name")!="h264": raise RuntimeError("Validación de vídeo/audio fallida.")
 final=float(probe["format"]["duration"])
 if not 30<=final<=60: raise RuntimeError("Duración final fuera de 30–60s.")
 meta={"status":"rendered","created_at":datetime.now(timezone.utc).isoformat(),"genre":genre,"title":title,"script":script,"file":str(mp4),"size_bytes":mp4.stat().st_size,"duration_seconds":round(final,2),"width":W,"height":H,"video_codec":"h264","audio_codec":"aac","voice":voice,"ambience":"original_synthesized_horror_drone","social_publishing":False}
 (OUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8"); (OUT/"script.txt").write_text(script,encoding="utf-8")
 print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=="__main__":
 try: main()
 except Exception as e: print("NEXUS VIDEO AI ERROR:",e,file=sys.stderr); raise
