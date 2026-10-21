"""Run: /Applications/Blender.app/Contents/MacOS/Blender -b -t 4 --python tools/build_anime_assets.py"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'anime'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

PALETTE = dict(ink='202942', navy='343E65', teal='43DCD0', hair='258A9B', light='F0F5FF', skin='FFD3BE',
               gold='FFCA73', coral='F06B82', plum='633C71', dark='2C2445', eye='5654A7', glow='A4FFF0')
mats = {}
for name, value in PALETTE.items():
    rgb = [int(value[i:i+2], 16)/255 for i in (0,2,4)]
    # Store linear values so glTF and Three vertex colors agree in sRGB output.
    rgb = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*rgb, 1)
    bs.inputs['Roughness'].default_value = .82
    mats[name] = m

parts = []
def finish(o, name, mat):
    o.name = name
    o.data.materials.append(mats[mat])
    parts.append(o)
    return o

def ball(name, loc, scale, mat, seg=12, rings=6):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o = bpy.context.object; o.scale = scale
    return finish(o, name, mat)

def box(name, loc, scale, mat, bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod=o.modifiers.new('Soft silhouette', 'BEVEL'); mod.width=bevel; mod.segments=1
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat)

def cone(name, a, b, r1, r2, mat, vertices=6):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=d.length, location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object; o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return finish(o,name,mat)

def character(kind):
    hero=kind=='crew'; boss=kind=='boss'
    armor='navy' if hero else 'dark'; accent='teal' if hero else 'gold' if boss else 'coral'
    for side in [-1,1]:
        x=side*.105
        box('leg', (x,0,.235),(.125,.15,.33),armor)
        box('boot',(x,-.045,.075),(.16,.25,.15),'ink')
        box('boot trim',(x,-.17,.11),(.13,.015,.04),accent,.005)
    cone('tunic',(0,0,.39),(0,0,.74),.205,.15,armor,8)
    box('chest plate',(0,-.132,.64),(.24,.075,.16),'light' if hero else 'plum')
    box('collar',(0,-.04,.765),(.25,.2,.07),accent)
    box('belt',(0,0,.43),(.34,.27,.055),accent)
    box('buckle',(0,-.15,.43),(.065,.035,.065),'gold',.01)
    for side in [-1,1]:
        ball('shoulder',(side*.20,0,.69),(.105,.12,.115),accent,8,4)
        cone('sleeve',(side*.22,0,.67),(side*.23,-.10,.51),.075,.065,armor)
        ball('glove',(side*.23,-.125,.49),(.065,.065,.065),'light' if hero else 'ink',8,4)
    ball('face',(0,-.015,.97),(.235,.205,.245),'skin' if hero else 'light')
    if hero:
        ball('hair cap',(0,.025,1.075),(.248,.205,.185),'hair')
        for i in range(5):
            x=(i-2)*.085
            cone('fringe',(x,-.145,1.19),(x-.035,-.215,1.015-abs(i-2)*.016),.083,.006,'teal',5)
        for side in [-1,1]:
            ball('hair tie',(side*.22,.05,1.07),(.06,.07,.065),'gold',8,4)
            cone('twin tail',(side*.25,.08,1.10),(side*.32,.13,.76),.10,.025,'hair',7)
            cone('tail highlight',(side*.25,.01,1.10),(side*.32,.07,.85),.045,.008,'teal',5)
        box('headset',(0,.19,1.01),(.43,.065,.07),'ink')
        box('rifle',( .20,-.30,.55),(.09,.36,.10),'ink')
        box('rifle core',(.20,-.35,.59),(.075,.12,.055),'teal',.006)
        cone('muzzle',(.20,-.48,.55),(.20,-.55,.55),.04,.04,'gold',8)
        for side in [-1,1]:
            ball('eye white',(side*.085,-.203,1.00),(.055,.018,.065),'light',8,4)
            ball('iris',(side*.085,-.220,.997),(.028,.008,.047),'eye',8,4)
            ball('eye sparkle',(side*.080,-.230,1.018),(.010,.005,.015),'light',6,3)
            box('brow',(side*.085,-.215,1.065),(.10,.016,.018),'ink',.003)
            ball('blush',(side*.155,-.185,.94),(.035,.012,.016),'coral',8,4)
        box('mouth',(0,-.214,.915),(.035,.01,.01),'coral',.002)
    else:
        ball('helmet',(0,.045,1.08),(.25,.20,.18),accent)
        box('visor',(0,-.205,1.005),(.35,.045,.09),'ink')
        for side in [-1,1]:
            box('eye slit',(side*.085,-.235,1.005),(.075,.018,.025),'gold' if not boss else 'coral',.004)
            cone('horn',(side*.17,.01,1.18),(side*.29,-.02,1.40 if boss else 1.32),.075,.003,'gold',6)
            box('cheek armor',(side*.18,-.145,.91),(.10,.09,.15),accent)
        box('mask grille',(0,-.211,.91),(.14,.035,.045),'navy')
        if boss:
            for side in [-1,1]:
                for z in [.68,.61,.54]:
                    box('samurai shoulder',(side*.27,0,z),(.24,.30,.07),'plum')
                    box('armor edge',(side*.27,-.16,z),(.24,.025,.025),'gold',.004)
            cone('helmet crest',(0,-.1,1.17),(0,-.12,1.41),.09,0,'gold',4)
            box('back banner',(0,.23,.9),(.13,.035,.6),'coral')
    # Eight baked walk poses keep the crowd to one shared mesh/material per actor.

def capsule():
    cone('capsule',(0,0,.15),(0,0,2.35),2.10,2.10,'light',12)
    for z in [.18,1.25,2.32]:
        cone('rim',(0,0,z-.09),(0,0,z+.09),2.2,2.2,'navy',12)
    for a in range(0,360,60):
        t=math.radians(a)
        box('power strip',(2.09*math.sin(t),2.09*math.cos(t),1.25),(.20,.14,1.55),'teal').rotation_euler.z=-t
    ball('power crystal',(0,0,2.5),(.55,.55,.33),'teal',8,4)

def crate():
    box('supply case',(0,0,1.25),(4.1,4.1,2.5),'navy',.18)
    for x in [-1.6,1.6]: box('case strap',(x,0,1.25),(.25,4.19,2.6),'light',.045)
    box('lid seam',(0,0,1.93),(4.2,4.2,.07),'teal',.015)
    box('front badge',(0,-2.12,1.35),(1.1,.08,.65),'teal',.07)
    box('badge cross',(0,-2.18,1.35),(.18,.045,.45),'light')
    box('badge cross',(0,-2.18,1.35),(.55,.045,.18),'light')

def pylon():
    box('foot',(0,0,.12),(.5,.5,.24),'navy')
    box('tower',(0,0,2.15),(.22,.25,4.1),'light')
    box('light',(0,-.15,3.50),(.11,.06,1.1),'teal')
    box('lantern',(0,0,4.55),(.65,.48,.22),'navy')
    box('lantern core',(0,0,4.36),(.45,.35,.16),'glow')

def export_geometry(objects):
    positions=[]; normals=[]; colors=[]; indices=[]; seen={}
    for obj in objects:
        mesh=obj.data; mesh.calc_loop_triangles(); matrix=obj.matrix_world
        nm=matrix.to_3x3().inverted().transposed()
        for tri in mesh.loop_triangles:
            mat=obj.data.materials[tri.material_index].diffuse_color[:3]
            for vi in reversed(tri.vertices):
                p=matrix @ mesh.vertices[vi].co
                n=(nm @ tri.normal).normalized()
                key=tuple(round(v,5) for v in (*[p.x,p.z,p.y],*[n.x,n.z,n.y],*mat))
                if key not in seen:
                    seen[key]=len(seen); positions.extend(key[:3]); normals.extend(key[3:6]); colors.extend(key[6:])
                indices.append(seen[key])
    return dict(position=positions,normal=normals,color=colors,index=indices)

runtime={}; manifest={}; model_groups={}
for kind, builder in [('crew',lambda:character('crew')),('enemy',lambda:character('enemy')),('boss',lambda:character('boss')),('capsule',capsule),('crate',crate),('pylon',pylon)]:
    parts=[]; builder(); bpy.context.view_layer.update()
    model_groups[kind]=list(parts)
    data=export_geometry(parts)
    frames=[]
    if kind in ['crew','enemy','boss']:
        originals={o:o.location.copy() for o in parts}
        for frame in range(8):
            s=math.sin(frame*math.tau/8)
            for o in parts:
                o.location=originals[o].copy()
                if o.name.split('.')[0] in ['leg','boot','boot trim']:
                    o.location.y += s * .075 * (1 if o.location.x>0 else -1)
                    o.location.z += max(0,s*(1 if o.location.x>0 else -1))*.025
            bpy.context.view_layer.update()
            frames.append(export_geometry(parts)['position'])
        for o in parts: o.location=originals[o]
        bpy.context.view_layer.update()
        data['frames']=frames
    runtime[kind]=data
    manifest[kind]=dict(vertices=len(data['position'])//3,triangles=len(data['index'])//3,walk_frames=len(frames))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT/f'{kind}.glb'),use_selection=True,export_format='GLB')
    for o in parts: o.hide_render=True; o.hide_set(True)

(OUT/'models.js').write_text('// Generated by tools/build_anime_assets.py; Y-up, forward -Z.\nwindow.ANIME_MODELS='+json.dumps(runtime,separators=(',',':'))+';\n')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

# A lit contact sheet also remains in the native Blender source.
offsets={'crew':(-3.3,0,0),'enemy':(-1.9,0,0),'boss':(-.4,0,0),'capsule':(1.6,0,0),'crate':(3.5,0,0),'pylon':(4.8,0,0)}
for kind, objects in model_groups.items():
    size=.34 if kind in ['capsule','crate','pylon'] else 1.25
    offset=Vector(offsets[kind])
    for o in objects:
        o.hide_render=False; o.hide_set(False)
        o.location=o.location*size+offset; o.scale*=size
    bpy.ops.object.text_add(location=(offset.x,-.65,-.04))
    text=bpy.context.object; text.name=f'{kind} label'; text.data.body=kind.upper(); text.data.size=.16
    text.rotation_euler=(math.radians(72),0,0); text.data.align_x='CENTER'; text.data.materials.append(mats['navy'])
box('Display plinth',(0,0,-.16),(11,3,.2),'light',.12)
scene=bpy.context.scene
scene.world.color=(.32,.32,.32)
for loc,power,size in [((0,-4,7),1100,7),((1,3,5),850,5)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object; light.data.energy=power; light.data.shape='DISK'; light.data.size=size
    light.rotation_euler=(Vector((0,0,.5))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(4,-11,7))
cam=bpy.context.object; cam.rotation_euler=(Vector((.65,0,.6))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'; cam.data.ortho_scale=11.5; scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=1800; scene.render.resolution_y=850; scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(OUT/'lineup.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'anime-kit.blend'))
bpy.ops.render.render(write_still=True)
print('ASSET_MANIFEST',json.dumps(manifest))
