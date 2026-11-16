"""Procedural 3D horror corridor, armature-driven actor, animated door/shadow and camera."""
import bpy, math, json, os, time
BUILD_STARTED=time.perf_counter()
from mathutils import Vector
OUT=os.environ.get("NEXUS_RENDER_OUT","artifacts/blender3d/frames")
SAMPLES=int(os.environ.get("NEXUS_SAMPLES","8"))
def material(name,c,metal=0,rough=.7,emission=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True; p=m.node_tree.nodes.get("Principled BSDF"); p.inputs["Base Color"].default_value=(*c,1); p.inputs["Metallic"].default_value=metal; p.inputs["Roughness"].default_value=rough
 if emission: p.inputs["Emission Color"].default_value=(*c,1); p.inputs["Emission Strength"].default_value=emission
 return m
def box(name,loc,dim,ma,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=dim; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma)
 if bevel: mod=o.modifiers.new("worn edges","BEVEL"); mod.width=bevel; mod.segments=2
 return o
def key(obj,path,values,index=None):
 for f,v in values:
  if index is None: setattr(obj,path,v)
  else: getattr(obj,path)[index]=v
  obj.keyframe_insert(data_path=path,index=index,frame=f)
def build():
 bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
 s=bpy.context.scene; s.render.engine="CYCLES"; s.cycles.device="CPU"; s.cycles.samples=SAMPLES; s.cycles.use_denoising=True
 s.render.resolution_x=1080; s.render.resolution_y=1920; s.render.resolution_percentage=100; s.render.fps=30; s.frame_start=1; s.frame_end=300
 s.render.image_settings.file_format="PNG"; s.render.image_settings.color_mode="RGB"; s.view_settings.view_transform="AgX"
 s.world.color=(.008,.01,.018)
 wall=material("damp concrete",(.045,.055,.07)); floor=material("wet slate",(.018,.027,.04),.25,.24); trim=material("aged brass",(.12,.075,.035),.5); wood=material("dark door wood",(.055,.018,.012)); cloth=material("charcoal coat",(.009,.014,.022)); skin=material("pale face",(.27,.16,.13)); steel=material("steel",(.2,.24,.27),.8,.2); glow=material("failing fluorescent",(.55,.7,.48),0,.2,2)
 # Hall geometry: solid independent meshes, not a flat plate.
 box("corridor_floor",(0,2,-.13),(5.4,19,.26),floor); box("corridor_ceiling",(0,2,3.9),(5.4,19,.22),wall)
 for x in (-2.65,2.65):
  box("left_right_wall",(x,2,1.9),(.22,19,4),wall)
  for y in (-4,1,6): box("wall_pillar",(x*.94,y,1.9),(.28,.35,4.05),trim)
 for y in (-5,0,5,9):
  for x in (-2.3,2.3):
   box("lamp_housing",(x,y,3.72),(.55,.85,.08),steel); box("lamp_tube",(x,y,3.66),(.38,.62,.035),glow)
 # Door is parented to a hinge at its actual edge and opens across frames 150-210.
 hinge=bpy.data.objects.new("DOOR_HINGE_ANIMATED",None); s.collection.objects.link(hinge); hinge.location=(2.48,3.2,0)
 door=box("door_leaf",(2.48,3.2,1.45),(.12,1.55,2.9),wood,.025); door.parent=hinge; door.location=(0,-.775,1.45)
 knob=box("door_handle",(2.38,2.68,1.35),(.08,.12,.12),steel,.025); knob.parent=hinge; knob.location=(-.1,-.52,1.35)
 key(hinge,"rotation_euler",[(1,(0,0,0)),(145,(0,0,0)),(220,(0,0,-math.radians(82))),(300,(0,0,-math.radians(82)))],2)
 box("side_table",(-1.85,1,.48),(.65,.65,.9),wood,.04); box("tabletop",(-1.85,1,.96),(.8,.8,.1),trim,.03)
 for y in (-2,4,7): box("wall_pipe",(-2.48,y,1.1),(.07,.07,2.1),steel)
 # Rig with hierarchical bones. Body parts are separate meshes bound to the armature bones.
 arm=bpy.data.armatures.new("NEXUS_HUMANOID_ARMATURE"); rig=bpy.data.objects.new("CHARACTER_RIG",arm); s.collection.objects.link(rig); bpy.context.view_layer.objects.active=rig; rig.select_set(True); bpy.ops.object.mode_set(mode="EDIT")
 def bone(n,h,t,p=None):
  b=arm.edit_bones.new(n); b.head=h; b.tail=t
  if p: b.parent=arm.edit_bones[p]
 bone("root",(0,0,0),(0,0,.8)); bone("spine",(0,0,.8),(0,0,1.5),"root"); bone("head",(0,0,1.5),(0,0,1.9),"spine")
 for side,sgn in (("L",-1),("R",1)):
  bone("upper_arm_"+side,(0,0,1.38),(sgn*.35,0,1.1),"spine"); bone("forearm_"+side,(sgn*.35,0,1.1),(sgn*.4,0,.88),"upper_arm_"+side)
  bone("thigh_"+side,(sgn*.13,0,.8),(sgn*.13,0,.42),"root"); bone("shin_"+side,(sgn*.13,0,.42),(sgn*.13,0,.07),"thigh_"+side)
 bpy.ops.object.mode_set(mode="OBJECT"); rig.show_in_front=True
 def actor_part(n,loc,dim,ma,bn,sphere=False):
  if sphere: bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=loc)
  else: bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
  o=bpy.context.object; o.name=n; o.dimensions=dim; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(ma); o.parent=rig; o.parent_type="BONE"; o.parent_bone=bn; return o
 actor_part("torso",(0,0,1.15),(.62,.34,.76),cloth,"spine"); actor_part("head_mesh",(0,0,1.72),(.34,.32,.38),skin,"head",True)
 for side,sgn in (("L",-1),("R",1)):
  actor_part("upper_arm_"+side,(sgn*.2,0,1.25),(.2,.22,.46),cloth,"upper_arm_"+side); actor_part("forearm_"+side,(sgn*.4,0,1),(.17,.19,.36),cloth,"forearm_"+side)
  actor_part("thigh_"+side,(sgn*.13,0,.62),(.23,.26,.45),cloth,"thigh_"+side); actor_part("shin_"+side,(sgn*.13,0,.24),(.18,.22,.38),cloth,"shin_"+side)
 rig.location=(0,-3.5,0)
 # A continuous gait cycle over the ten-second shot.
 for f in range(1,301,15):
  phase=(f-1)/60*math.tau
  for side,sgn in (("L",1),("R",-1)):
   for bn,angle in (("thigh_"+side,math.sin(phase)*.42*sgn),("shin_"+side,max(0,-math.sin(phase)*.55)),("upper_arm_"+side,-math.sin(phase)*.22*sgn)):
    pb=rig.pose.bones[bn]; pb.rotation_mode="XYZ"; pb.rotation_euler[0]=angle; pb.keyframe_insert(data_path="rotation_euler",frame=f)
 for f,y in ((1,-3.5),(300,2.9)): rig.location.y=y; rig.keyframe_insert(data_path="location",frame=f)
 # Independent shadow actor material/object animates into view behind protagonist.
 dark=material("shadow silhouette",(.001,.001,.003),0,1)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=(0,-5.5,1.05)); shadow=bpy.context.object; shadow.name="INDEPENDENT_SHADOW_ENTITY"; shadow.data.materials.append(dark); shadow.rotation_euler[0]=math.radians(90)
 for f,loc,sc in ((1,(0,-5.5,1),(.001,.001,.001)),(165,(0,-5.5,1),(.001,.001,.001)),(215,(.2,-4.6,1.1),(.42,.1,1)),(300,(.55,-3.8,1.2),(.62,.1,1.15))):
  shadow.location=loc; shadow.scale=sc; shadow.keyframe_insert(data_path="location",frame=f); shadow.keyframe_insert(data_path="scale",frame=f)
 # Camera tracks actor smoothly and deliberately cuts framing to the opening door then shadow.
 bpy.ops.object.camera_add(location=(0,-7.5,2)); cam=bpy.context.object; cam.name="CINEMATIC_FOLLOW_CAMERA"; s.camera=cam; cam.data.lens=38; cam.data.dof.use_dof=True; cam.data.dof.focus_object=rig; cam.data.dof.aperture_fstop=6.3
 def aim(target): cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
 for f,loc,target in ((1,(0,-7.5,2),(0,-2.2,1)),(140,(0,-4.7,1.9),(0,1,1)),(220,(-.8,-4.2,1.8),(1.9,3.2,1.3)),(260,(0,-4.2,1.8),(.3,-4.1,1.1)),(300,(0,-4,1.8),(.4,-3.8,1.1))):
  cam.location=loc; aim(target); cam.keyframe_insert(data_path="location",frame=f); cam.keyframe_insert(data_path="rotation_euler",frame=f)
 # Real area lights and flicker; actual Cycles shadows.
 for i,y in enumerate((-3,1,5,8)):
  bpy.ops.object.light_add(type="AREA",location=(0,y,3.45)); l=bpy.context.object; l.name="ceiling_area_"+str(i); l.data.energy=230; l.data.shape="RECTANGLE"; l.data.size=2; l.data.size_y=.5
  if i==2:
   for f,e in ((1,230),(145,230),(152,55),(158,260),(165,90),(175,230),(300,230)): l.data.energy=e; l.data.keyframe_insert(data_path="energy",frame=f)
 bpy.ops.object.light_add(type="AREA",location=(0,4.5,2.3)); back=bpy.context.object; back.name="shadow_backlight"; back.data.energy=350; back.data.color=(.3,.45,.65); back.data.size=1.2; back.rotation_euler=(math.radians(20),0,math.radians(180))
 dust=material("dust motes",(.2,.25,.3),0,.3,.25)
 for i in range(18):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.018,location=((i%5-2)*.7,-3+(i%7)*1.4,1+(i%4)*.5)); p=bpy.context.object; p.name="dust_particle"; p.data.materials.append(dust); p.keyframe_insert(data_path="location",frame=1); p.location.z+=.5; p.keyframe_insert(data_path="location",frame=300)
 os.makedirs(OUT,exist_ok=True); s.render.filepath=os.path.join(OUT,"frame_"); s.render.image_settings.file_format="PNG"
 # Explicit linear interpolation for smooth deterministic movement.
 for obj in s.objects:
  if obj.animation_data and obj.animation_data.action:
   for fc in obj.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation="BEZIER"
 s.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(OUT),"scene.blend"))
 camera_samples=[]
 for f in (1,30,60,90,120,150,180,210,240,270,300):
  s.frame_set(f); camera_samples.append({"frame":f,"seconds":(f-1)/30,"location":[round(v,4) for v in cam.matrix_world.translation],"rotation":[round(v,4) for v in cam.rotation_euler]})
 report={"engine":"Cycles CPU","resolution":[1080,1920],"fps":30,"frames":300,"samples":SAMPLES,"geometry_objects":len(s.objects),"rig_bones":len(arm.bones),"door":"DOOR_HINGE_ANIMATED","character":"CHARACTER_RIG","shadow":"INDEPENDENT_SHADOW_ENTITY","camera":"CINEMATIC_FOLLOW_CAMERA","camera_samples":camera_samples}
 with open(os.path.join(os.path.dirname(OUT),"scene_manifest.json"),"w") as f: json.dump(report,f,indent=2)
 prep_seconds=time.perf_counter()-BUILD_STARTED
 timing_path=os.path.join(os.path.dirname(OUT),"blender_timing.json")
 with open(timing_path,"w") as f: json.dump({"preparation_seconds":round(prep_seconds,3)},f)
 render_started=time.perf_counter(); bpy.ops.render.render(animation=True)
 with open(timing_path,"w") as f: json.dump({"preparation_seconds":round(prep_seconds,3),"render_seconds":round(time.perf_counter()-render_started,3)},f)
build()
