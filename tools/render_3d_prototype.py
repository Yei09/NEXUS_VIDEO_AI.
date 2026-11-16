"""Build the 10-second Blender CPU prototype and create measurable evidence."""
import argparse,json,os,shutil,subprocess,time,resource,wave,math,struct
from pathlib import Path
def run(cmd,**kw): return subprocess.run(cmd,check=True,text=True,**kw)
def synth_audio(out):
 out.mkdir(parents=True,exist_ok=True); rate=48000; n=rate*10; mix=[0.0]*n
 def sound(t0,dur,freq,amp,noise=False):
  a=int(t0*rate); b=min(n,int((t0+dur)*rate))
  for i in range(a,b):
   t=(i-a)/rate; env=min(1,t*20)*min(1,max(0,(b-i)/(rate*.12)))
   z=(2*((i*1664525+1013904223)&0xffffffff)/0xffffffff-1) if noise else math.sin(2*math.pi*freq*t)
   mix[i]+=z*amp*env
 cues=[]
 for name,t,d,f in [("footstep_1",.55,.2,90),("footstep_2",1.35,.2,90),("footstep_3",2.15,.2,90),("door_open",5.0,.85,62),("shadow_reveal",7.15,.7,42),("final_impact",9.12,.55,48)]:
  sound(t,d,f,.24,name.startswith("foot")); cues.append({"event":name,"start_seconds":t,"duration_seconds":d,"linked_to":"story_event"})
 sound(0,10,38,.025,True)
 fx=out/"effects.wav"
 with wave.open(str(fx),"wb") as w:
  w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b"".join(struct.pack("<h",max(-32767,min(32767,int(x*32767)))) for x in mix))
 speech=out/"narration.wav"
 if shutil.which("espeak-ng"):
  run(["espeak-ng","-v","es","-s","138","-w",str(speech),"Tomás avanzó por el pasillo. La puerta se abrió sola. Detrás de él, algo comenzó a caminar."])
  run(["ffmpeg","-y","-loglevel","error","-i",str(speech),"-af","apad,atrim=0:10","-ar",str(rate),str(out/"voice_10s.wav")])
  run(["ffmpeg","-y","-loglevel","error","-i",str(out/"voice_10s.wav"),"-i",str(fx),"-filter_complex","[0:a]volume=1[v];[1:a]volume=.6[e];[v][e]amix=inputs=2:duration=longest,alimiter=limit=.9[a]","-map","[a]","-t","10","-ar",str(rate),str(out/"audio_master.wav")])
 else: shutil.copy(fx,out/"audio_master.wav")
 (out/"audio_cues.json").write_text(json.dumps(cues,indent=2))
def main():
 p=argparse.ArgumentParser(); p.add_argument("--out",default="artifacts/blender3d"); p.add_argument("--samples",type=int,default=8); a=p.parse_args()
 out=Path(a.out).resolve(); frames=out/"frames"; frames.mkdir(parents=True,exist_ok=True)
 blender=shutil.which("blender"); ffmpeg=shutil.which("ffmpeg")
 if not blender or not ffmpeg: raise SystemExit("Missing Blender or FFmpeg")
 prep_started=time.perf_counter(); synth_audio(out)
 script=Path(__file__).resolve().parents[1]/"nexus_video3d"/"scene_factory.py"
 env=os.environ.copy(); env.update(NEXUS_RENDER_OUT=str(frames),NEXUS_SAMPLES=str(a.samples))
 run([blender,"-b","-t","2","--python",str(script)],env=env); timing=json.loads((out/"blender_timing.json").read_text()); render=float(timing["render_seconds"]); preparation=float(timing["preparation_seconds"]) + (time.perf_counter()-prep_started-render-float(timing["preparation_seconds"]))
 mp4=out/"nexus_blender3d_10s.mp4"
 run([ffmpeg,"-y","-loglevel","error","-framerate","30","-i",str(frames/"frame_%04d.png"),"-i",str(out/"audio_master.wav"),"-frames:v","300","-vf","format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","22","-r","30","-c:a","aac","-b:a","160k","-t","10","-movflags","+faststart",str(mp4)])
 # Six keyframes plus consecutive proof sequences around walking, door, and shadow.
 for label,times in {"six":[.5,2.2,4.2,5.5,7.4,9.5],"walk":[1.0,1.1,1.2,1.3,1.4,1.5],"door":[4.7,4.9,5.1,5.3,5.5,5.7],"shadow":[6.8,7.0,7.2,7.4,7.6,7.8]}.items():
  dest=out/"evidence"/label; dest.mkdir(parents=True,exist_ok=True)
  for i,t in enumerate(times):
   run([ffmpeg,"-y","-loglevel","error","-ss",str(t),"-i",str(mp4),"-frames:v","1",str(dest/f"{i+1:02d}.jpg")])
 usage=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
 report={"engine":"Blender Cycles CPU","render_seconds":round(render,2),"peak_child_rss_kb":usage,"video_bytes":mp4.stat().st_size,"frames":300,"target_duration_seconds":10,"install_seconds":float(os.getenv("NEXUS_INSTALL_SECONDS","0")),"preparation_seconds":round(preparation,2),"fps_production":round(300/render,3),"samples":a.samples}
 (out/"performance_report.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__": main()
