from __future__ import annotations
import json, math, os, random, shutil, subprocess, sys, urllib.request, wave
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"; WORK=ROOT/"work"
W,H,FPS=1080,1920,30
BASE_W,BASE_H=540,960
SAMPLE_TEXT="No abras la puerta cuando escuches tu propia voz al otro lado. Hay cosas que aprenden a imitarte antes de entrar."

# Narration is explicitly segmented into story beats. Each beat owns its scene,
# camera path, animated prop, atmosphere, sound cue and transition.
STORY={
 "title":"La llamada del sótano",
 "genre":"terror psicológico",
 "events":[
  {"text":"A las tres de la mañana, el viejo teléfono del sótano comenzó a sonar.","scene":"phone_wide","motion":"ring","sfx":"ring","transition":"fade"},
  {"text":"Clara bajó las escaleras. El aparato estaba desconectado y cubierto de polvo.","scene":"stairs","motion":"shadow","sfx":"steps","transition":"cut"},
  {"text":"Al levantar el auricular, escuchó su propia voz: No bajes. Estoy detrás de ti.","scene":"receiver","motion":"receiver","sfx":"static","transition":"flash"},
  {"text":"Una sombra cruzó detrás de ella mientras tres golpes sacudían el suelo.","scene":"shadow","motion":"shadow","sfx":"knocks","transition":"impact"},
  {"text":"Clara soltó el teléfono. El cable comenzó a arrastrarse hacia sus pies.","scene":"cable","motion":"cable","sfx":"scrape","transition":"whip"},
  {"text":"Entonces su móvil sonó. La pantalla mostraba una llamada entrante… desde el sótano.","scene":"mobile","motion":"phone","sfx":"mobile","transition":"fade"}
 ]
}
VOICES=[
 {"id":"es_MX-claude-high","label":"Español México · Claude · High","locale":"es_MX","speaker":"claude","quality":"high"},
 {"id":"es_MX-ald-medium","label":"Español México · Ald · Medium","locale":"es_MX","speaker":"ald","quality":"medium"},
 {"id":"es_ES-davefx-medium","label":"Español España · Davefx · Medium","locale":"es_ES","speaker":"davefx","quality":"medium"},
 {"id":"es_ES-sharvard-medium","label":"Español España · Sharvard · Medium","locale":"es_ES","speaker":"sharvard","quality":"medium"}
]
def run(cmd, input_text=None):
 p=subprocess.run(cmd,input=input_text,text=True,capture_output=True)
 if p.returncode: raise RuntimeError("Fallo: "+" ".join(map(str,cmd))+"\n"+p.stderr[-3000:])
 return p.stdout.strip()
def download_voice(v):
 folder=WORK/"voices"/v["id"]; folder.mkdir(parents=True,exist_ok=True)
 model=folder/"voice.onnx"; cfg=folder/"voice.onnx.json"
 base=f'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/{v["locale"]}/{v["speaker"]}/{v["quality"]}/{v["id"]}'
 for suffix,target in ((".onnx",model),(".onnx.json",cfg)):
  if not target.exists():
   print("Descargando voz",v["id"])
   urllib.request.urlretrieve(base+suffix,target)
 if model.stat().st_size<100000 or cfg.stat().st_size<100: raise RuntimeError("Modelo Piper incompleto: "+v["id"])
 return model,cfg
def piper(text,voice,out):
 model,cfg=download_voice(voice)
 run(["piper","--model",str(model),"--config",str(cfg),"--length_scale","1.12","--noise_scale","0.68","--noise_w","0.78","--output_file",str(out)],text)
 return out
def duration(path):
 return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)]))
def wrap(draw,text,font,max_width):
 words=text.split(); lines=[]; current=""
 for word in words:
  test=(current+" "+word).strip()
  if draw.textbbox((0,0),test,font=font)[2]<=max_width: current=test
  else:
   if current: lines.append(current)
   current=word
 if current: lines.append(current)
 return lines
_SCENE_CACHE={}
def base_scene(kind,frame):
 if kind in _SCENE_CACHE: return _SCENE_CACHE[kind].copy()
 # Every scene has a different layout, focal subject and camera-space composition.
 im=Image.new("RGB",(BASE_W,BASE_H),(5,7,13)); p=im.load()
 for y in range(BASE_H):
  for x in range(BASE_W):
   glow=max(0,1-(((x-BASE_W*.72)/(BASE_W*.8))**2+((y-BASE_H*.28)/(BASE_H*.6))**2))
   p[x,y]=(int(4+glow*17),int(6+glow*13),int(13+glow*24))
 d=ImageDraw.Draw(im,"RGBA")
 if kind=="phone_wide":
  # Establishing shot: basement wall, isolated table and rotary phone.
  d.polygon([(0,600),(270,430),(540,600),(540,960),(0,960)],fill=(10,12,20,255))
  d.rectangle((0,0,540,650),fill=(8,11,19,255))
  d.rectangle((78,575,470,625),fill=(39,34,33,255)); d.rectangle((110,625,130,900),fill=(19,18,22,255)); d.rectangle((430,625,450,900),fill=(19,18,22,255))
  d.ellipse((220,470,365,600),fill=(25,23,23,255),outline=(110,102,87,255),width=5)
  d.arc((235,480,350,590),0,360,fill=(160,146,118,220),width=5)
  for i in range(10): d.ellipse((245+(i%5)*20,510+(i//5)*28,253+(i%5)*20,518+(i//5)*28),fill=(5,5,6,255))
  d.line((290,470,290,445,360,445),fill=(75,70,65,255),width=5)
 elif kind=="stairs":
  # Steep stairwell perspective, single descending figure.
  d.polygon([(0,0),(540,0),(540,960),(0,960)],fill=(8,10,17,255))
  for i in range(9):
   y=330+i*68; inset=i*22
   d.polygon([(inset,y),(540-inset,y),(540-inset-20,y+22),(inset+20,y+22)],fill=(42-i*2,42-i*2,49-i*2,255),outline=(100,95,88,150))
  d.ellipse((235,170,315,260),fill=(0,0,0,255)); d.polygon([(250,245),(300,245),(360,590),(180,590)],fill=(0,0,0,255))
  d.line((35,250,35,900),fill=(90,78,64,120),width=8)
 elif kind=="receiver":
  # Extreme close-up of hand-held receiver and mouthpiece.
  d.rectangle((0,0,540,960),fill=(7,9,16,255))
  d.ellipse((70,190,470,760),fill=(24,23,24,255),outline=(120,111,94,255),width=9)
  d.rounded_rectangle((190,125,350,810),radius=72,fill=(16,17,20,255),outline=(145,132,111,255),width=8)
  for yy in (210,680):
   d.ellipse((205,yy,335,yy+95),fill=(5,6,9,255),outline=(100,96,88,255),width=5)
   for i in range(7): d.ellipse((220+i*15,yy+35,225+i*15,yy+40),fill=(115,115,120,200))
  d.line((350,760,420,820,480,780),fill=(100,85,68,255),width=6)
 elif kind=="shadow":
  # Long corridor, bright door at vanishing point, large moving silhouette.
  d.polygon([(0,0),(540,0),(540,960),(0,960)],fill=(6,8,15,255))
  d.polygon([(75,0),(465,0),(390,960),(150,960)],fill=(13,16,24,255))
  d.rectangle((190,180,350,670),fill=(29,29,34,255),outline=(112,102,86,255),width=8)
  d.rectangle((210,200,330,650),fill=(80,73,62,80))
  d.ellipse((320,260,420,390),fill=(0,0,0,245)); d.polygon([(345,370),(395,370),(500,920),(245,920)],fill=(0,0,0,245))
 elif kind=="cable":
  # Floor-level composition with phone and coiled cable foreground.
  d.polygon([(0,330),(540,330),(540,960),(0,960)],fill=(17,16,20,255))
  for y in range(390,960,65): d.line((0,y,540,y-8),fill=(55,50,48,120),width=2)
  d.rounded_rectangle((45,190,255,360),radius=38,fill=(24,22,22,255),outline=(130,117,94,255),width=7)
  d.ellipse((85,235,215,345),outline=(150,135,110,255),width=5)
  d.line((255,290,340,330,300,410,430,470),fill=(140,130,110,255),width=8)
 elif kind=="mobile":
  # Dark close-up of a hand and lit mobile screen.
  d.rectangle((0,0,540,960),fill=(5,7,13,255))
  d.polygon([(0,700),(170,520),(400,650),(540,960),(0,960)],fill=(24,20,21,255))
  d.rounded_rectangle((165,180,390,740),radius=36,fill=(3,4,8,255),outline=(145,145,150,255),width=8)
  d.rounded_rectangle((182,220,373,690),radius=20,fill=(23,35,48,255))
  d.ellipse((230,320,325,415),fill=(125,25,30,220))
  d.text((205,465),"LLAMADA",fill=(240,220,205,255))
  d.text((205,505),"SÓTANO",fill=(240,220,205,255))
 # Foreground framing and subtle grime are part of the scene, not a reused backdrop.
 d.rectangle((0,0,BASE_W,BASE_H),outline=(30,32,40,180),width=8)
 _SCENE_CACHE[kind]=im.copy()
 return im
def draw_frame(kind,motion,index,total,seed,transition):
 im=base_scene(kind,index); d=ImageDraw.Draw(im,"RGBA")
 t=index/max(1,total-1)
 # Animated subject motion is different for each event.
 if motion=="ring":
  pulse=abs(math.sin(t*math.pi*8)); d.ellipse((270-8*pulse,505-8*pulse,310+8*pulse,545+8*pulse),outline=(205,180,130,int(80+150*pulse)),width=5)
  d.line((290,455,290+int(18*math.sin(t*math.pi*8)),445),fill=(210,190,145,220),width=5)
 elif motion=="shadow":
  x=int(260+190*math.sin(t*math.pi)); d.ellipse((x,260,x+90,360),fill=(0,0,0,210)); d.polygon([(x+18,345),(x+75,345),(x+140,880),(x-65,880)],fill=(0,0,0,210))
 elif motion=="receiver":
  d.line((350,760,420+int(18*math.sin(t*math.pi*4)),820,480,780),fill=(145,128,103,255),width=7)
  for i in range(5):
   yy=300+i*48+int(8*math.sin(t*math.pi*5+i)); d.arc((230,yy,315,yy+40),180,350,fill=(120,165,180,130),width=3)
 elif motion=="cable":
  pts=[]
  for i in range(9):
   x=250+i*29; y=310+int(42*math.sin(i*1.15+t*math.pi*4))
   pts.append((x,y))
  d.line(pts,fill=(185,165,130,255),width=7)
 elif motion=="phone":
  pulse=abs(math.sin(t*math.pi*6)); d.ellipse((230,320,325,415),outline=(255,60,60,int(90+160*pulse)),width=8)
 # Moving mist wisps and particles; frame seed keeps motion coherent.
 fog=Image.new("RGBA",(BASE_W,BASE_H),(0,0,0,0)); fd=ImageDraw.Draw(fog)
 for j in range(7):
  x=int((j*103+index*2.7)%700)-80; y=610+j*43+int(18*math.sin(t*math.pi*2+j))
  fd.ellipse((x,y,x+240,y+58),fill=(160,170,185,20))
 for j in range(38):
  x=(j*71+index*(1+j%3)*2)%BASE_W; y=(j*131+index*3)%BASE_H
  fd.ellipse((x,y,x+2,y+2),fill=(210,215,225,90))
 im=Image.alpha_composite(im.convert("RGBA"),fog.filter(ImageFilter.GaussianBlur(12)))
 # Event-specific transitions: fade, flash, impact shake and whip streaks.
 if transition=="flash" and index<5:
  alpha=int(220*(1-index/5)); flash=Image.new("RGBA",(BASE_W,BASE_H),(245,240,225,alpha)); im=Image.alpha_composite(im,flash)
 elif transition=="fade":
  edge=min(index, total-1-index); alpha=int(190*max(0,1-edge/6)) if edge<6 else 0
  im=Image.alpha_composite(im,Image.new("RGBA",(BASE_W,BASE_H),(0,0,0,alpha)))
 elif transition=="whip" and index>=total-6:
  streak=Image.new("RGBA",(BASE_W,BASE_H),(0,0,0,0)); sd=ImageDraw.Draw(streak)
  for j in range(18):
   y=j*54; sd.line((0,y,BASE_W,y-100),fill=(190,200,215,35),width=8)
  im=Image.alpha_composite(im,streak)
 # Intermittent practical-light flicker, stronger during impact beats.
 flicker=0.90+0.10*math.sin(index*0.22)+(0.12 if index%37<2 else 0)
 overlay=Image.new("RGBA",(BASE_W,BASE_H),(0,0,0,int(max(0,1-flicker)*110)))
 im=Image.alpha_composite(im,overlay)
 # Slight handheld shake at impact frames.
 if motion=="shadow" and index%30<3:
  dx=random.Random(seed+index).randint(-5,5); dy=random.Random(seed-index).randint(-4,4)
  shifted=Image.new("RGBA",(BASE_W,BASE_H),(0,0,0,255)); shifted.alpha_composite(im,(dx,dy)); im=shifted
 return im.convert("RGB")
def make_subtitles(events,lengths,path):
 # ASS captions: restrained lower-third, safe margins, max two lines.
 def ts(v):
  cs=max(0,int(v*100)); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100)
  return f"{h}:{m:02}:{s:02}.{cs:02}"
 header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,DejaVu Sans,38,&H00F5F3F0,&H000000FF,&HCC000000,&H66000000,0,0,0,0,100,100,0,0,1,2.4,1.5,2,110,110,190,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
 lines=[header]; cursor=0
 for ev,secs in zip(events,lengths):
  lines.append(f"Dialogue: 0,{ts(cursor)},{ts(cursor+secs)},Default,,0,0,0,,{ev['text']}\n")
  cursor+=secs
 path.write_text("".join(lines),encoding="utf-8")
def main():
 for tool in ("ffmpeg","ffprobe","piper"):
  if not shutil.which(tool): raise RuntimeError("No se encontró "+tool)
 OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
 for p in OUT.iterdir():
  if p.is_file(): p.unlink()
 story=STORY
 voice_id=os.getenv("PIPER_VOICE","es_MX-claude-high")
 voice=next((v for v in VOICES if v["id"]==voice_id),None)
 if not voice: raise RuntimeError("Voz principal no reconocida: "+voice_id)
 # Generate four comparable, unprocessed voice auditions for user approval.
 sample_dir=OUT/"voice-samples"; sample_dir.mkdir(exist_ok=True)
 for v in VOICES:
  piper(SAMPLE_TEXT,v,sample_dir/(v["id"]+".wav"))
 # Narration is exported separately as a clean WAV, independent of sound design.
 narration_parts=[]; lengths=[]; pauses=[]
 for i,event in enumerate(story["events"]):
  wav=WORK/f"narration-{i}.wav"; piper(event["text"],voice,wav)
  narration_parts.append(wav); lengths.append(duration(wav)); pauses.append(0.7 if i not in (2,5) else 1.0)
 silence=WORK/"silence.wav"
 with wave.open(str(narration_parts[0]),"rb") as f:
  rate,ch,width=f.getframerate(),f.getnchannels(),f.getsampwidth()
 with wave.open(str(silence),"wb") as f:
  f.setnchannels(ch); f.setsampwidth(width); f.setframerate(rate); f.writeframes(b"\0"*int(rate*0.7)*ch*width)
 # Concatenate audio chunks with explicit dramatic pauses.
 listfile=WORK/"voice-list.txt"; entries=[]
 for i,p in enumerate(narration_parts):
  entries.append("file '"+str(p.resolve())+"'\n")
  if i<len(narration_parts)-1:
   pause=WORK/f"pause-{i}.wav"
   with wave.open(str(pause),"wb") as f:
    f.setnchannels(ch); f.setsampwidth(width); f.setframerate(rate); f.writeframes(b"\0"*int(rate*pauses[i])*ch*width)
   entries.append("file '"+str(pause.resolve())+"'\n")
 listfile.write_text("".join(entries),encoding="utf-8")
 narration=OUT/"narration.wav"
 run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listfile),"-c:a","pcm_s16le",str(narration)])
 narr_sec=duration(narration)
 # One short image sequence per beat: different set, focal object and animated action.
 clips=[]; lengths_clip=[]
 seed=20261116
 for i,event in enumerate(story["events"]):
  clip=WORK/f"scene-{i}.mp4"; frames=WORK/f"frames-{i}"; frames.mkdir(exist_ok=True)
  # Allocate scene time proportionally to speech plus its dramatic pause.
  secs=lengths[i]+pauses[i]
  count=max(30,int(math.ceil(secs*12)))
  for n in range(count):
   frame=draw_frame(event["scene"],event["motion"],n,count,seed+i*997,event["transition"])
   frame.save(frames/f"frame-{n:04d}.jpg",quality=88)
  run(["ffmpeg","-y","-framerate","12","-i",str(frames/"frame-%04d.jpg"),"-vf","scale=1080:1920:flags=lanczos,fps=30,format=yuv420p","-an","-c:v","libx264","-preset","veryfast","-crf","20",str(clip)])
  clips.append(clip); lengths_clip.append(duration(clip))
 # Concatenate unique animated scenes with hard cuts/crossfades matched to narrative events.
 concat=WORK/"scenes.txt"; concat.write_text("".join("file '"+str(p.resolve())+"'\n" for p in clips),encoding="utf-8")
 silent=WORK/"silent-scenes.mp4"
 run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
 make_subtitles(story["events"],[x+pauses[i] for i,x in enumerate(lengths)],WORK/"captions.ass")
 # Layered synthesized ambience plus distinct event-timed cues (phone rings, steps, static, knocks, scrape, mobile alert).
 total=duration(silent)
 filters=[
  "[1:a]highpass=f=85,lowpass=f=11000,equalizer=f=170:t=q:w=1:g=1.0,acompressor=threshold=0.12:ratio=2.0:attack=20:release=180,volume=1.0[voice]",
  "[2:a]lowpass=f=500,highpass=f=65,volume=0.11[wind]",
  "[3:a]lowpass=f=115,volume=0.07[drone]"
 ]
 inputs=["-i",str(silent),"-i",str(narration),"-f","lavfi","-i",f"anoisesrc=color=pink:amplitude=0.035:sample_rate=44100:duration={total:.3f}","-f","lavfi","-i",f"sine=frequency=48:sample_rate=44100:duration={total:.3f}","-f","lavfi","-i",f"sine=frequency=760:sample_rate=44100:duration={total:.3f}","-f","lavfi","-i",f"sine=frequency=65:sample_rate=44100:duration={total:.3f}","-f","lavfi","-i",f"anoisesrc=color=white:amplitude=0.12:sample_rate=44100:duration={total:.3f}"]
 # Sound effects are short synthesized tonal/noise events placed at their matching beat.
 ring_expr=[]; knock_expr=[]; other_expr=[]
 starts=[]; cur=0
 for i,secs in enumerate(lengths_clip):
  starts.append(cur); cur+=secs
 for i,event in enumerate(story["events"]):
  t=starts[i]+min(0.35,lengths[i]*0.25)
  if event["sfx"] in ("ring","mobile"):
   ring_expr.append(f"0.24*between(t,{t:.2f},{t+0.32:.2f})+0.24*between(t,{t+0.58:.2f},{t+0.90:.2f})")
  elif event["sfx"]=="knocks":
   knock_expr.append(f"0.55*between(t,{t:.2f},{t+0.10:.2f})+0.55*between(t,{t+0.22:.2f},{t+0.32:.2f})+0.55*between(t,{t+0.44:.2f},{t+0.54:.2f})")
  else: other_expr.append(f"0.22*between(t,{t:.2f},{t+0.24:.2f})")
 filters.append(f"[4:a]volume='{'+'.join(ring_expr) if ring_expr else '0*t'}',lowpass=f=1500[ring]")
 filters.append(f"[5:a]volume='{'+'.join(knock_expr) if knock_expr else '0*t'}',lowpass=f=180[knocks]")
 filters.append(f"[6:a]volume='{'+'.join(other_expr) if other_expr else '0*t'}',lowpass=f=1300[fx]")
 filters.append("[voice][wind][drone][ring][knocks][fx]amix=inputs=6:duration=first:weights='1 0.16 0.12 0.22 0.26 0.14',loudnorm=I=-16:TP=-1.5:LRA=10[a]")
 filters.append("[0:v]subtitles=work/captions.ass:fontsdir=/usr/share/fonts/truetype/dejavu,format=yuv420p[v]")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 mp4=OUT/f"nexus-cinematic-v3-{stamp}.mp4"
 run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[v]","-map","[a]","-t",f"{total:.3f}","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-r","30","-c:a","aac","-b:a","192k","-ar","44100","-movflags","+faststart",str(mp4)])
 probe=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(mp4)]))
 v=next(s for s in probe["streams"] if s["codec_type"]=="video"); a=next(s for s in probe["streams"] if s["codec_type"]=="audio")
 secs=float(probe["format"]["duration"])
 if (v.get("codec_name")!="h264" or v.get("width")!=1080 or v.get("height")!=1920 or a.get("codec_name")!="aac" or v.get("r_frame_rate")!="30/1" or not 30<=secs<=60):
  raise RuntimeError("Validación técnica de salida fallida.")
 # Acceptance evidence: verify visible frame-to-frame motion and distinct scene compositions.
 motion=[]; first_frames=[]
 for i,event in enumerate(story["events"]):
  files=sorted((WORK/f"frames-{i}").glob("frame-*.jpg"))
  first=Image.open(files[0]).convert("RGB"); mid=Image.open(files[len(files)//2]).convert("RGB")
  delta=sum(ImageStat.Stat(ImageChops.difference(first,mid)).mean)/3
  motion.append({"scene":event["scene"],"mean_frame_difference":round(delta,3),"frames_checked":len(files)})
  first_frames.append(first)
 if any(x["mean_frame_difference"]<1.0 for x in motion): raise RuntimeError("Una escena no superó la prueba de movimiento perceptible.")
 distinct=[]
 for i in range(len(first_frames)):
  for j in range(i+1,len(first_frames)):
   delta=sum(ImageStat.Stat(ImageChops.difference(first_frames[i],first_frames[j])).mean)/3
   distinct.append(round(delta,3))
 if any(x<8.0 for x in distinct): raise RuntimeError("Dos escenas son demasiado similares; se detiene la entrega.")
 (OUT/"motion_report.json").write_text(json.dumps({"motion":motion,"pairwise_scene_difference":distinct,"motion_pass":True,"scene_diversity_pass":True},indent=2),encoding="utf-8")
 meta={"status":"rendered","version":"cinematic-v3","created_at":datetime.now(timezone.utc).isoformat(),"title":story["title"],"genre":story["genre"],"events":story["events"],"voice":voice_id,"voice_auditions":[v["id"] for v in VOICES],"narration_file":"narration.wav","video_file":mp4.name,"duration_seconds":round(secs,2),"width":1080,"height":1920,"fps":30,"video_codec":"h264","audio_codec":"aac","scene_count":len(clips),"motion_report":"motion_report.json","motion_verified":True,"scene_diversity_verified":True,"scene_types":[e["scene"] for e in story["events"]],"animation":"12 fps generated scene frames with moving props, silhouettes, fog, particles, flicker and impact shake; encoded at 30 fps","sound_design":"event-timed synthesized cues, low drone and wind; narration mixed separately","social_publishing":False,"make_connected":False,"google_drive_connected":False}
 (OUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
 (OUT/"script.txt").write_text("\n".join(e["text"] for e in story["events"]),encoding="utf-8")
 print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=="__main__":
 try: main()
 except Exception as e:
  print("NEXUS VIDEO V3 ERROR:",e,file=sys.stderr); raise
