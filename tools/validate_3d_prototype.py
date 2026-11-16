"""Strict technical checks and image-motion checks on the rendered MP4."""
import json,subprocess,sys
from pathlib import Path
import cv2,numpy as np
p=Path(sys.argv[1]); video=p/"nexus_blender3d_10s.mp4"
def probe():
 d=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(video)]))
 v=next(x for x in d["streams"] if x["codec_type"]=="video"); a=next(x for x in d["streams"] if x["codec_type"]=="audio")
 assert v["codec_name"]=="h264" and (v["width"],v["height"])==(1080,1920)
 assert abs(float(v["r_frame_rate"].split("/")[0])/float(v["r_frame_rate"].split("/")[1])-30)<.001
 assert a["codec_name"]=="aac" and abs(float(d["format"]["duration"])-10)<.03
 assert int(v.get("nb_read_frames",v.get("nb_frames","0")))==300
 return d
def diff_at(ts):
 cap=cv2.VideoCapture(str(video)); imgs=[]
 for t in ts:
  cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,im=cap.read(); assert ok; im=cv2.resize(im,(180,320)); imgs.append(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY))
 cap.release()
 return [float(np.mean(cv2.absdiff(imgs[i],imgs[i+1]))) for i in range(len(imgs)-1)]
meta=json.loads((p/"scene_manifest.json").read_text()); cues=json.loads((p/"audio_cues.json").read_text())
assert meta["geometry_objects"]>40 and meta["rig_bones"]>=10
assert len(meta["camera_samples"])>=8 and len({tuple(x["location"]) for x in meta["camera_samples"]})>=4
assert len(cues)>=6 and len({x["start_seconds"] for x in cues})==len(cues)
assert all(x["start_seconds"]>=0 and x["start_seconds"]+x["duration_seconds"]<=10 for x in cues)
walk=diff_at([1.0,1.1,1.2,1.3,1.4,1.5]); door=diff_at([4.7,4.9,5.1,5.3,5.5,5.7]); shadow=diff_at([6.8,7,7.2,7.4,7.6,7.8])
# Every sequence must exhibit image change; multiple adjacent samples must change materially.
assert sum(x>0.7 for x in walk)>=4,("walk visual motion",walk)
assert sum(x>0.7 for x in door)>=3,("door visual motion",door)
assert sum(x>0.7 for x in shadow)>=3,("shadow visual motion",shadow)
d=probe()
report={"status":"PASS","video":str(video),"probe":d,"walk_adjacent_mean_absdiff":walk,"door_adjacent_mean_absdiff":door,"shadow_adjacent_mean_absdiff":shadow,"checks":{"3d_geometry":True,"armature_rig":True,"camera_motion":True,"walk_visual_change":True,"door_visual_change":True,"shadow_visual_change":True,"timed_audio_events":True,"h264_aac_1080x1920_30fps_10s":True}}
(p/"validation_report.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
