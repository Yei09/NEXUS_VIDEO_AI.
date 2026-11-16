from __future__ import annotations
import json, os, random, shutil, subprocess, sys, urllib.request, wave
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"output"; WORK=ROOT/"work"
W,H,FPS=1080,1920,30; XFADE=0.65
STORIES=[
("La llamada del sótano","terror psicológico",["Si recibes una llamada desde un teléfono desconectado, no contestes.","Anoche, Clara escuchó sonar el viejo teléfono del sótano. Su abuela llevaba diez años muerta y aquel aparato no tenía cable.","Contestó. Al otro lado, su propia voz susurró: «No bajes. Estoy detrás de ti».","Clara soltó el auricular. Entonces oyó tres golpes bajo el suelo… y el teléfono volvió a sonar.","Esta vez, la llamada venía del móvil que llevaba en la mano."]),
("La casa que respira","casa embrujada",["La casa llevaba veinte años vacía, pero cada noche alguien encendía la luz del pasillo.","Cuando Mateo entró, encontró fotografías familiares con una persona más en cada imagen. Una figura alta, siempre detrás de quien tomaba la foto.","El suelo crujió. Las paredes se hincharon lentamente, como un pecho respirando.","Mateo corrió a la puerta, pero la casa había cambiado el pasillo. En la última fotografía, la figura ya estaba junto a él.","Y la puerta de salida apareció cerrada desde dentro."]),
("La última parada","leyenda urbana",["En esta ruta hay una parada que no aparece en ningún mapa.","A las 2:17, el autobús de Elena se detuvo frente a una estación abandonada. Subió una niña empapada y pidió bajar en el puente viejo.","El conductor palideció: aquel puente había desaparecido en una inundación hacía treinta años.","Elena miró por la ventana. Todos los pasajeros tenían el rostro de la niña.","Cuando el autobús arrancó, su asiento estaba mojado… y su boleto decía: solo ida."]),
("Algo bajo la cama","criaturas",["Lo peor de vivir solo es descubrir que alguien conoce tus horarios.","Cada madrugada, Julián oía uñas arañando la madera bajo su cama. Pensó que era una tubería hasta que escuchó su nombre.","Una noche dejó el teléfono grabando. En el audio, su voz dormida decía: «Todavía no. Espera a que apague la luz».","Julián no había hablado en sueños. Al amanecer revisó la grabación y oyó una segunda respiración.","Venía de debajo de la cama… y se alejaba hacia la puerta."]),
("El reflejo equivocado","paranormal",["Si tu reflejo tarda en imitarte, no intentes comprobarlo otra vez.","Lucía se lavaba los dientes cuando vio que su reflejo seguía sonriendo después de que ella dejó de hacerlo.","Apagó la luz. En la oscuridad, el espejo se iluminó solo. Su reflejo levantó una mano y escribió desde el otro lado: «Déjame salir».","Lucía retrocedió. El reflejo no la siguió; se quedó quieto, mirando la puerta del baño.","Al girarse, escuchó el pestillo cerrarse detrás de ella."])]

def run(cmd):
 p=subprocess.run(cmd,text=True,capture_output=True)
 if p.returncode: raise RuntimeError("Fallo: "+" ".join(cmd)+"\n"+p.stderr[-3500:])
 return p.stdout.strip()
def dur(p): return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)]))
def kind(text,genre):
 s=(text+" "+genre).lower()
 if any(k in s for k in ("teléfono","sótano","auricular","golpes")): return "basement"
 if any(k in s for k in ("autobús","parada","puente","pasajeros","boleto")): return "bus"
 if any(k in s for k in ("cama","dormida","uñas","respiración")): return "bed"
 if any(k in s for k in ("espejo","reflejo","baño","pestillo")): return "mirror"
 return "house"
def draw_scene(path,text,genre,seed):
 rng=random.Random(seed); im=Image.new("RGB",(W,H)); px=im.load()
 for y in range(H):
  sh=y/H
  for x in range(W):
   glow=max(0,1-(((x-780)/650)**2+((y-350)/700)**2))
   n=rng.random()*1.3
   px[x,y]=(int(3+7*sh+glow*13+n),int(5+8*sh+glow*8+n),int(12+18*sh+glow*17+n))
 d=ImageDraw.Draw(im,"RGBA"); k=kind(text,genre)
 if k in ("house","basement"):
  d.polygon([(60,1100),(540,650),(1020,1100),(1020,1920),(60,1920)],fill=(7,9,16,255),outline=(65,67,78,220))
  d.polygon([(180,1100),(540,800),(900,1100)],fill=(5,7,13,255))
  d.rectangle((330,1040,750,1710),fill=(4,6,12,255),outline=(72,70,80,220),width=9)
  for x in (205,765): d.rectangle((x,1090,x+100,1320),fill=(20,26,34,255),outline=(90,83,78,190),width=5)
  if k=="basement":
   for y in (1450,1540,1630): d.line((80,y,1000,y+30),fill=(55,55,64,130),width=5)
   d.ellipse((470,900,620,1080),fill=(0,0,0,190))
 elif k=="bus":
  d.polygon([(100,740),(980,740),(880,1420),(200,1420)],fill=(10,14,22,255),outline=(80,85,95,220))
  for x in (245,465,685):
   d.rectangle((x,830,x+170,1130),fill=(5,12,20,255),outline=(70,80,90,210),width=5)
   d.ellipse((x+55,900,x+120,1020),fill=(0,0,0,190))
  d.polygon([(0,1420),(1080,1420),(1080,1920),(0,1920)],fill=(4,7,13,255))
 elif k=="bed":
  d.rectangle((90,1180,990,1710),fill=(13,15,24,255))
  d.polygon([(120,1230),(900,1230),(1020,1630),(30,1630)],fill=(22,23,33,255))
  d.rectangle((350,920,780,1230),fill=(4,5,10,255),outline=(70,70,80,180),width=5)
  d.ellipse((430,1530,670,1770),fill=(0,0,0,230))
 else:
  d.rectangle((180,560,900,1570),fill=(6,8,15,255),outline=(88,90,100,220),width=13)
  d.rectangle((215,595,865,1535),fill=(13,18,27,255))
  d.ellipse((430,800,680,1140),fill=(0,0,0,220))
  d.ellipse((480,880,520,925),fill=(170,175,180,100)); d.ellipse((590,880,630,925),fill=(170,175,180,100))
 # Atmospheric mist layers, grain and silhouette depth.
 fog=Image.new("RGBA",(W,H),(0,0,0,0)); fd=ImageDraw.Draw(fog,"RGBA")
 for j in range(10):
  y=1100+j*78+rng.randint(-20,20)
  fd.ellipse((-260+j*25,y,900+j*20,y+170),fill=(150,160,175,rng.randint(7,17)))
 im=Image.alpha_composite(im.convert("RGBA"),fog.filter(ImageFilter.GaussianBlur(45)))
 im.convert("RGB").save(path,quality=94)
def ass_time(v):
 cs=max(0,int(v*100)); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100)
 return f"{h}:{m:02}:{s:02}.{cs:02}"
def subtitles(parts,lengths,pauses,path):
 head="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,39,&H00F5F3F0,&H000000FF,&HCC000000,&H55000000,0,0,0,0,100,100,0,0,1,2.2,1.2,2,100,100,145,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
 lines=[head]; cursor=0.0
 for part,length,pause in zip(parts,lengths,pauses):
  words=part.split(); chunks=[" ".join(words[i:i+7]) for i in range(0,len(words),7)]
  step=length/max(1,len(chunks))
  for j,chunk in enumerate(chunks):
   w=chunk.split(); shown=" ".join(w[:4])+r"\N"+" ".join(w[4:]) if len(w)>4 else chunk
   start=cursor+j*step; end=min(cursor+length,start+step+0.06)
   lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{shown}\n")
  cursor+=length+pause
 path.write_text("".join(lines),encoding="utf-8")
def main():
 for b in ("ffmpeg","ffprobe","piper"):
  if not shutil.which(b): raise RuntimeError("No se encontró "+b)
 OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
 for p in WORK.iterdir():
  if p.is_file(): p.unlink()
 rng=random.Random(os.getenv("STORY_SEED") or datetime.now(timezone.utc).isoformat())
 story=next((s for s in STORIES if s[1]==os.getenv("HORROR_CATEGORY")),None) or rng.choice(STORIES)
 title,genre,parts=story; script=" ".join(parts)
 voice=os.getenv("PIPER_VOICE","es_MX-claude-high")
 try: lang,region,speaker,quality=voice.split("-")
 except ValueError: raise RuntimeError("PIPER_VOICE debe tener formato es_MX-nombre-calidad.")
 base=f"https://huggingface.co/rhasspy/piper-voices/resolve/main/es/{lang}/{region}/{speaker}/{quality}/{voice}"
 model=WORK/"voice.onnx"; cfg=WORK/"voice.onnx.json"
 for url,target in ((base+".onnx",model),(base+".onnx.json",cfg)):
  if not target.exists(): print("Descargando Piper:",voice); urllib.request.urlretrieve(url,target)
 if model.stat().st_size<100000 or cfg.stat().st_size<100: raise RuntimeError("Modelo Piper incompleto.")
 wavs=[]; lengths=[]; pauses=[]
 for i,part in enumerate(parts):
  wav=WORK/f"voice-{i}.wav"
  p=subprocess.run(["piper","--model",str(model),"--config",str(cfg),"--length_scale","1.16","--noise_scale","0.68","--noise_w","0.78","--output_file",str(wav)],input=part,text=True,capture_output=True)
  if p.returncode: raise RuntimeError("Piper falló: "+p.stderr[-2500:])
  wavs.append(wav); lengths.append(dur(wav))
  pauses.append(0.95 if ("…" in part or "..." in part) else 0.68)
 audio_items=[]
 for i,wav in enumerate(wavs):
  audio_items.append(wav)
  if i<len(pauses):
   silence=WORK/f"pause-{i}.wav"
   with wave.open(str(wav),"rb") as wf: rate,ch,width=wf.getframerate(),wf.getnchannels(),wf.getsampwidth()
   with wave.open(str(silence),"wb") as sf:
    sf.setnchannels(ch); sf.setsampwidth(width); sf.setframerate(rate)
    sf.writeframes(b"\0"*int(rate*pauses[i])*ch*width)
   audio_items.append(silence)
 listing=WORK/"audio.txt"
 listing.write_text("".join("file '"+str(p.resolve())+"'\n" for p in audio_items),encoding="utf-8")
 narration=WORK/"narration.wav"
 run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),"-c:a","pcm_s16le",str(narration)])
 seconds=dur(narration)
 if not 30<=seconds<=60: raise RuntimeError(f"Voz {seconds:.1f}s fuera de 30–60s; se detiene para no entregar una prueba inválida.")
 images=[]; seed=rng.randrange(1,2**31)
 for i,part in enumerate(parts):
  p=WORK/f"scene-{i}.jpg"; draw_scene(p,part,genre,seed+i*991); images.append(p)
 subtitles(parts,lengths,pauses,WORK/"captions.ass")
 seg=seconds/len(images); cmd=["ffmpeg","-y"]
 for p in images: cmd += ["-loop","1","-framerate",str(FPS),"-t",f"{seg:.4f}","-i",str(p)]
 narr=len(images); cmd += ["-i",str(narration),"-f","lavfi","-i",f"anoisesrc=color=pink:amplitude=0.035:sample_rate=44100:duration={seconds:.3f}","-f","lavfi","-i",f"sine=frequency=49:sample_rate=44100:duration={seconds:.3f}","-f","lavfi","-i",f"sine=frequency=67:sample_rate=44100:duration={seconds:.3f}"]
 wind=narr+1; drone=narr+2; impacts=narr+3
 filters=[]
 for i in range(len(images)):
  x="iw/2-(iw/zoom/2)" if i%2==0 else "iw/2-(iw/zoom/2)+18*sin(on/75)"
  y="ih/2-(ih/zoom/2)+12*sin(on/110)"
  filters.append(f"[{i}:v]scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='min(zoom+0.00055,1.075)':x='{x}':y='{y}':d=1:s=1080x1920:fps={FPS},eq=brightness='0.012*sin(2*PI*t/3.7)':contrast=1.10:saturation=0.78,noise=alls=2:allf=t,format=yuv420p,setsar=1,settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
 current="v0"; accumulated=seg
 for i in range(1,len(images)):
  label=f"xf{i}"; filters.append(f"[{current}][v{i}]xfade=transition=fade:duration={XFADE}:offset={accumulated-XFADE:.4f}[{label}]")
  current=label; accumulated+=seg-XFADE
 filters.append(f"[{narr}:a]asetrate=22050*0.96,aresample=22050,atempo=1.0416667,highpass=f=75,lowpass=f=10500,equalizer=f=180:t=q:w=1.1:g=1.5,acompressor=threshold=0.12:ratio=2.2:attack=18:release=180,volume=1.0[voice]")
 filters.append(f"[{wind}:a]lowpass=f=520,highpass=f=70,volume=0.13,afade=t=out:st={max(0,seconds-3):.2f}:d=3[wind]")
 filters.append(f"[{drone}:a]lowpass=f=125,volume=0.075,afade=t=in:st=0:d=2,afade=t=out:st={max(0,seconds-4):.2f}:d=4[drone]")
 pulse=[round(sum(lengths[:i])+sum(pauses[:i])+lengths[i]*.72,2) for i in range(len(parts))]
 expr="+".join(f"0.20*between(t,{t:.2f},{t+.42:.2f})" for t in pulse)
 filters.append(f"[{impacts}:a]volume='{expr}',lowpass=f=180,afade=t=out:st={max(0,seconds-2):.2f}:d=2[impacts]")
 filters.append("[voice][wind][drone][impacts]amix=inputs=4:duration=first:weights='1 0.18 0.16 0.22',loudnorm=I=-16:TP=-1.5:LRA=10[a]")
 filters.append(f"[{current}]subtitles=work/captions.ass:fontsdir=/usr/share/fonts/truetype/dejavu,format=yuv420p[vout]")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); mp4=OUT/f"nexus-terror-cinematic-{stamp}.mp4"
 run(cmd+["-filter_complex",";".join(filters),"-map","[vout]","-map","[a]","-t",f"{seconds:.3f}","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-r",str(FPS),"-c:a","aac","-b:a","192k","-ar","44100","-movflags","+faststart",str(mp4)])
 probe=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(mp4)]))
 v=next((x for x in probe["streams"] if x.get("codec_type")=="video"),None); a=next((x for x in probe["streams"] if x.get("codec_type")=="audio"),None)
 if not v or not a or v.get("width")!=W or v.get("height")!=H or v.get("codec_name")!="h264" or a.get("codec_name")!="aac": raise RuntimeError("Validación H.264/AAC/1080x1920 fallida.")
 final=float(probe["format"]["duration"])
 if not 30<=final<=60: raise RuntimeError("Duración final fuera de 30–60 segundos.")
 meta={"status":"rendered","created_at":datetime.now(timezone.utc).isoformat(),"genre":genre,"title":title,"script":script,"file":str(mp4),"size_bytes":mp4.stat().st_size,"duration_seconds":round(final,2),"width":W,"height":H,"fps":FPS,"video_codec":"h264","audio_codec":"aac","voice":voice,"voice_processing":"pitch_down_0.7_semitone_with_duration_restored","visual_style":"story_specific_art_slow_camera_motion_flicker_grain_crossfade","sound_design":"synthesized_wind_low_drone_and_story_beat_impacts","social_publishing":False}
 (OUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8"); (OUT/"script.txt").write_text(script,encoding="utf-8")
 print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=="__main__":
 try: main()
 except Exception as e: print("NEXUS VIDEO AI ERROR:",e,file=sys.stderr); raise
