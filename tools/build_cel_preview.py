"""A separate art-direction preview. Does not modify or export the game's active kit.
Run with Blender --background --python tools/build_cel_preview.py
"""
import bpy, bmesh, math
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'cel-preview'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0

def linear(hex):
    values = [int(hex[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c < .04045 else ((c + .055) / 1.055)**2.4 for c in values)

COLORS = dict(ink='242841', coat='333C66', teal='4CE0CF', hair='319DAA', hairlight='82F4DE',
              white='F6F4EB', skin='FFE1CE', gold='F5C268', coral='ED7187', plum='6B4A76',
              iris='6773C8', violet='AD99DC', blush='F4A0AB', black='171E32')
materials = {}
def cel(name, color):
    rgb = linear(color)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    n = mat.node_tree.nodes; n.clear(); links = mat.node_tree.links
    out = n.new('ShaderNodeOutputMaterial')
    diffuse = n.new('ShaderNodeBsdfDiffuse'); diffuse.inputs['Color'].default_value = (1,1,1,1)
    convert = n.new('ShaderNodeShaderToRGB')
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    for i, (position, shade) in enumerate([(0,.38),(.36,.70),(.75,1.0)]):
        stop = ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(position)
        stop.position = position
        stop.color = (*[c * shade for c in rgb],1)
    emission = n.new('ShaderNodeEmission')
    links.new(diffuse.outputs[0],convert.inputs[0])
    links.new(convert.outputs[0],ramp.inputs[0])
    links.new(ramp.outputs[0],emission.inputs[0])
    links.new(emission.outputs[0],out.inputs['Surface'])
    return mat
for name, color in COLORS.items(): materials[name] = cel(name, color)

def flat(name, hex):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    n=mat.node_tree.nodes; n.clear()
    e=n.new('ShaderNodeEmission'); e.inputs[0].default_value=(*linear(hex),1)
    out=n.new('ShaderNodeOutputMaterial'); mat.node_tree.links.new(e.outputs[0],out.inputs[0])
    return mat
outline=flat('Ink outline','242841'); outline.use_backface_culling=True
outline.use_backface_culling_shadow=True
paper=flat('Warm paper','F0EDE5'); lettering=flat('Typography','333C66')
parts=[]
def finish(o,name,mat,smooth=True):
    o.name=name; o.data.materials.append(materials[mat])
    if smooth:
        for face in o.data.polygons: face.use_smooth=True
    parts.append(o)
    return o

def ball(name,loc,scale,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=loc)
    o=bpy.context.object; o.scale=scale
    return finish(o,name,mat)

def box(name,loc,scale,mat,r=.04):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=o.modifiers.new('Rounded edges','BEVEL'); bevel.width=r; bevel.segments=4
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=bevel.name)
    weighted=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL'); weighted.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    return finish(o,name,mat)

def tube(name,points,r,mat):
    curve=bpy.data.curves.new(name,'CURVE'); curve.dimensions='3D'; curve.resolution_u=16
    curve.bevel_depth=r; curve.bevel_resolution=4
    spline=curve.splines.new('BEZIER'); spline.bezier_points.add(len(points)-1)
    for bp,co in zip(spline.bezier_points,points):
        bp.co=co; bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,curve); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object,name,mat)

def lock(name,points,widths,depths,mat):
    """A swept, curved, tapered lock; subdivision gives a continuous silhouette."""
    verts=[]; faces=[]; count=12
    for p,w,d in zip(points,widths,depths):
        for k in range(count):
            a=k*math.tau/count
            verts.append((p[0]+w*math.cos(a),p[1]+d*math.sin(a),p[2]))
    for j in range(len(points)-1):
        for k in range(count):
            a=j*count+k; b=j*count+(k+1)%count
            faces.append((a,b,b+count,a+count))
    faces.append(tuple(reversed(range(count))))
    faces.append(tuple((len(points)-1)*count+k for k in range(count)))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    mod=o.modifiers.new('Sculpted curve','SUBSURF'); mod.levels=2
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat)

def limb(name,a,b,r1,r2,mat):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=r1,radius2=r2,depth=d.length,location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object; o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    bevel=o.modifiers.new('Soft joint','BEVEL'); bevel.width=min(r1,r2)*.45; bevel.segments=3
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=bevel.name)
    return finish(o,name,mat)

def eye(x,z,mat='iris',ang=0):
    # Eyes sit on the forward cheek plane, with separate sclera, iris, pupil and lash.
    ball('Eye white',(x,-.350,z),(.116,.027,.131),'white')
    ball('Iris',(x,-.376,z-.007),(.075,.010,.102),mat)
    ball('Pupil',(x,-.387,z+.005),(.033,.006,.062),'black')
    ball('Eye glint',(x-.024,-.396,z+.045),(.026,.005,.031),'white')
    ball('Lower glint',(x+.032,-.393,z-.043),(.013,.004,.016),'white')
    tube('Upper lash',[(x-.109,-.362,z+.04),(x,-.388,z+.12),(x+.109,-.362,z+.055)],.013,'ink')

def ring(name,loc,rx,ry,thickness,mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=1,minor_radius=thickness,major_segments=64,minor_segments=12,location=loc)
    o=bpy.context.object; o.scale=(rx,ry,1)
    return finish(o,name,mat)

def cute_body():
    # One continuous tailored silhouette, with a high waist and softly flared hem.
    lock('Tailored tunic',[(0,.015,.87),(0,.015,.90),(0,0,1.03),(0,0,1.21),(0,0,1.40),(0,0,1.59),(0,0,1.70),(0,0,1.76)],
         [.39,.41,.35,.215,.225,.28,.23,.10],[.235,.245,.22,.15,.16,.185,.15,.09],'white')
    # A curved inset and flowing seam lines replace the old rectangular chest plate.
    ball('Bodice inset',(0,-.153,1.43),(.145,.033,.235),'coat')
    for side in [-1,1]:
        tube('Curved jacket edge',[(side*.19,-.12,1.69),(side*.155,-.182,1.53),(side*.145,-.17,1.36),(side*.12,-.155,1.23)],.016,'teal')
        tube('Skirt seam',[(side*.12,-.155,1.21),(side*.21,-.191,1.03),(side*.28,-.174,.90)],.008,'hair')
    ring('Soft navy hem',(0,.015,.889),.389,.233,.024,'coat')
    ring('Mint hem piping',(0,.015,.914),.395,.238,.010,'teal')
    ring('Waist ribbon',(0,0,1.22),.225,.159,.017,'teal')
    ball('Waist jewel',(0,-.174,1.22),(.032,.017,.042),'gold')
    limb('Neck',(0,0,1.68),(0,0,1.90),.085,.085,'skin')
    ring('Sailor collar',(0,0,1.74),.15,.12,.035,'coat')
    # Small neck bow and a teardrop clasp.
    for side in [-1,1]:
        bow=ball('Silk bow',(side*.064,-.165,1.66),(.072,.032,.035),'teal')
        bow.rotation_euler.y=side*-.3
    ball('Bow jewel',(0,-.20,1.66),(.028,.020,.034),'gold')
    for side in [-1,1]:
        x=side*.145
        limb('Slender leg',(x,0,.30),(x,.015,.97),.087,.102,'coat')
        # Smooth knee boots and compact oval toes; no box-shaped soles or cuffs.
        lock('Sculpted boot',[(x,-.035,.10),(x,-.025,.17),(x,0,.29),(x,0,.42),(x,0,.58),(x,0,.60)],
             [.105,.12,.10,.108,.12,.115],[.135,.16,.11,.11,.12,.115],'white')
        ball('Boot toe',(x,-.11,.125),(.12,.185,.09),'white')
        ball('Soft sole',(x,-.065,.062),(.123,.207,.032),'coat')
        ring('Boot rim',(x,0,.575),.12,.12,.014,'teal')
        tube('Boot seam',[(x,-.121,.51),(x,-.12,.35),(x,-.16,.20)],.008,'teal')
        ball('Boot charm',(x,-.125,.49),(.021,.008,.031),'gold')
        # One curved sleeve from the sloping shoulder to its tapered elbow.
        lock('Flowing sleeve',[(side*.245,0,1.68),(side*.29,0,1.62),(side*.33,-.015,1.46),(side*.345,-.04,1.29)],
             [.075,.105,.09,.075],[.09,.11,.09,.075],'white')
        limb('Slim forearm',(side*.35,-.08,1.11),(side*.345,-.04,1.32),.067,.073,'coat')
        ball('Sleeve cuff',(side*.348,-.047,1.28),(.078,.082,.044),'teal')
        hand=ball('Soft glove',(side*.35,-.10,1.06),(.077,.073,.106),'white')
        hand.rotation_euler.y=side*-.15
        ball('Thumb',(side*.30,-.14,1.06),(.038,.038,.06),'white')
    # A small rounded blaster stays clear of the body silhouette.
    ball('Blaster shell',(.35,-.23,1.08),(.09,.19,.082),'coat')
    ball('Blaster core',(.35,-.25,1.14),(.055,.115,.027),'teal')
    limb('Blaster muzzle',(.35,-.35,1.08),(.35,-.40,1.08),.045,.045,'gold')
    # Flowing ribbon tails sit behind the tunic.
    for side in [-1,1]:
        lock('Floating coat ribbon',[(side*.15,.16,1.28),(side*.26,.25,1.13),(side*.38,.28,.96),(side*.46,.22,1.00)],
             [.055,.065,.055,.001],[.025,.027,.022,.001],'teal')

def base_body(kind):
    hero=kind=='crew'; boss=kind=='boss'
    accent='teal' if hero else 'gold' if boss else 'coral'
    for side in [-1,1]:
        x=side*.175
        limb('Leg',(x,0,.45),(x,0,1.08),.115,.13,'coat' if hero else 'ink')
        ball('Boot',(x,-.07,.22),(.145,.235,.23),'white' if hero else 'ink')
        box('Sole',(x,-.085,.075),(.285,.43,.09),'ink',.035)
        box('Boot accent',(x,-.263,.27),(.15,.025,.075),accent,.025)
        limb('Boot cuff',(x,0,.38),(x,0,.54),.143,.135,'coat' if hero else accent)
    ball('Hip',(0,.015,1.02),(.29,.20,.22),'ink')
    ball('Jacket',(0,0,1.40),(.30,.215,.43),'white' if hero else 'plum')
    box('Chest inset',(0,-.199,1.48),(.31,.06,.30),'coat',.06)
    tube('Jacket piping',[(-.18,-.19,1.72),(-.12,-.235,1.48),(-.13,-.207,1.22)],.019,accent)
    tube('Jacket piping',[(.18,-.19,1.72),(.12,-.235,1.48),(.13,-.207,1.22)],.019,accent)
    box('Belt',(0,-.005,1.12),(.56,.43,.085),'ink',.04)
    box('Buckle',(0,-.236,1.12),(.115,.035,.095),'gold',.025)
    limb('Neck',(0,0,1.70),(0,0,1.92),.105,.105,'skin' if hero else 'ink')
    tube('High collar',[(-.15,-.08,1.78),(0,-.16,1.75),(.15,-.08,1.78)],.07,'coat')
    for side in [-1,1]:
        a=(side*.32,0,1.64); b=(side*.40,-.04,1.34); c=(side*.40,-.17,1.13)
        ball('Shoulder',a,(.145,.165,.17),'white' if hero else accent)
        limb('Upper sleeve',b,a,.10,.13,'white' if hero else 'plum')
        limb('Forearm',c,b,.10,.11,'coat')
        ball('Glove',(side*.40,-.17,1.08),(.11,.11,.13),'white' if hero else 'ink')
        box('Wrist trim',(side*.40,-.04,1.26),(.21,.23,.075),accent,.025)
    if hero:
        # Flared curved coat panels instead of a box-shaped torso.
        for side in [-1,1]:
            lock('Coat tail',[(side*.16,.08,1.23),(side*.24,.11,1.02),(side*.30,.16,.84)], [.13,.17,.16],[.14,.15,.13],'white')
            tube('Tail hem',[(side*.16,-.02,.89),(side*.30,.02,.86),(side*.40,.12,.89)],.02,'teal')
        # A rounded sci-fi sidearm, carried in the right hand.
        box('Sidearm body',(.41,-.30,1.08),(.15,.42,.18),'ink',.055)
        box('Sidearm core',(.41,-.34,1.17),(.10,.22,.055),'teal',.02)
        limb('Sidearm muzzle',(.41,-.50,1.08),(.41,-.60,1.08),.065,.065,'gold')
    return accent

def crew():
    cute_body()
    ball('Face',(0,-.018,2.17),(.42,.35,.435),'skin')
    for side in [-1,1]: ball('Ear',(side*.38,-.01,2.14),(.075,.07,.105),'skin')
    ball('Back hair',(0,.12,2.34),(.43,.32,.40),'hair')
    # Crown and long tapered locks meet behind the fringe, keeping the face open.
    ball('Crown',(0,.045,2.45),(.42,.32,.31),'hair')
    for i in range(7):
        x=(i-3)*.108
        endz=2.26 if i in [2,3,4] else 2.13
        lock('Swept fringe',[(x*.78,-.19,2.68),(x,-.30,2.51),(x+.04,-.365,2.34),(x+.055,-.37,endz)],
             [.065,.095,.072,.002],[.045,.065,.045,.002],'teal' if i%3 else 'hair')
    for side in [-1,1]:
        lock('Face framing lock',[(side*.35,-.12,2.53),(side*.41,-.19,2.28),(side*.39,-.20,2.02),(side*.31,-.19,1.91)],
             [.08,.09,.07,.002],[.065,.075,.065,.002],'hair')
        ball('Hair tie',(side*.39,.10,2.43),(.095,.075,.095),'gold')
        lock('Sweeping twin tail',[(side*.40,.14,2.47),(side*.54,.22,2.28),(side*.61,.30,1.92),(side*.60,.31,1.61),(side*.77,.22,1.44)],
             [.12,.16,.17,.11,.003],[.10,.13,.13,.08,.002],'hair')
        lock('Twin tail highlight',[(side*.45,.025,2.43),(side*.55,.095,2.24),(side*.63,.16,1.93),(side*.66,.18,1.63)],
             [.035,.058,.04,.002],[.015,.02,.015,.002],'teal')
        eye(side*.16,2.18)
        tube('Eyebrow',[(side*.07,-.354,2.37),(side*.16,-.37,2.39),(side*.24,-.33,2.37)],.012,'hair')
        ball('Blush',(side*.26,-.304,2.055),(.068,.008,.022),'blush')
    tube('Smile',[(-.037,-.339,2.012),(0,-.35,2.003),(.037,-.339,2.012)],.008,'coral')
    tube('Headband',[(-.37,.02,2.51),(0,-.05,2.70),(.37,.02,2.51)],.022,'ink')
    for side in [-1,1]:
        ball('Headset',(side*.40,.005,2.18),(.065,.11,.13),'white')
        ball('Headset core',(side*.447,-.005,2.18),(.025,.07,.08),'teal')

def oni(kind):
    boss=kind=='boss'; accent=base_body(kind)
    ball('Oni mask',(0,-.02,2.18),(.395,.33,.43),'white')
    ball('Helmet crown',(0,.06,2.46),(.43,.33,.29),'ink' if boss else 'coral')
    for side in [-1,1]:
        # The angled, almond-shaped dark sockets and red markings read as an oni mask.
        socket=ball('Eye socket',(side*.16,-.343,2.20),(.145,.04,.085),'ink')
        socket.rotation_euler.y=side*-.16
        slit=ball('Glowing eye',(side*.16,-.38,2.20),(.095,.015,.031),'coral' if boss else 'gold')
        slit.rotation_euler.y=side*-.16
        tube('Mask marking',[(side*.25,-.28,2.08),(side*.20,-.333,1.99),(side*.23,-.27,1.94)],.022,'coral')
        lock('Curved ivory horn',[(side*.28,0,2.59),(side*.39,.02,2.74),(side*.42,-.04,2.94 if boss else 2.84),(side*.37,-.10,3.03 if boss else 2.91)],
             [.10,.085,.04,.001],[.09,.07,.035,.001],'gold')
        ball('Temple plate',(side*.37,.0,2.12),(.10,.22,.25),accent)
        limb('Tusk',(side*.12,-.31,1.98),(side*.13,-.36,2.07),.033,.002,'white')
    ball('Mask nose',(0,-.355,2.11),(.055,.045,.065),'white')
    tube('Mask mouth',[(-.12,-.294,2.00),(0,-.352,1.975),(.12,-.294,2.00)],.015,'ink')
    if boss:
        # Curved kabuto brim and overlapping lamellar shoulder plates.
        tube('Kabuto brim',[(-.44,-.02,2.43),(-.30,-.27,2.48),(0,-.35,2.53),(.30,-.27,2.48),(.44,-.02,2.43)],.055,'gold')
        lock('Helmet crest',[(0,-.18,2.61),(0,-.24,2.81),(0,-.23,3.01)], [.12,.095,.001],[.035,.035,.001],'gold')
        for side in [-1,1]:
            for j in range(3):
                z=1.66-j*.115
                plate=box('Lamellar shoulder',(side*(.38+j*.02),.015,z),(.35,.39,.13),'plum',.06)
                plate.rotation_euler.y=side*-.22
                tube('Gold shoulder edge',[(side*.22,-.16,z-.02),(side*.40,-.195,z-.045),(side*.56,-.14,z-.01)],.016,'gold')
            for j in range(3):
                z=1.10-j*.11
                box('Waist armor',(side*.22,-.05,z),(.26,.34,.125),'plum',.045)
                tube('Waist lacing',[(side*.15,-.23,z+.015),(side*.26,-.23,z+.015)],.012,'gold')
        # Swept helmet neck guard and a sheathed blade on the back.
        for z in [2.12,2.24,2.36]:
            ball('Neck guard',(0,.22,z),(.40,.20,.14),'ink')
        blade=box('Sheathed katana',(.31,.28,1.23),(.085,.12,1.66),'ink',.035)
        blade.rotation_euler.y=-.35
        box('Katana guard',(.08,.28,1.97),(.30,.20,.06),'gold',.025)
        for z in [1.99,2.06,2.13]: ball('Sword grip',(.05,.28,z),(.055,.07,.025),'coral')
    else:
        tube('Scarf',[(-.29,-.11,1.82),(0,-.21,1.78),(.29,-.10,1.82)],.075,'coral')
        lock('Scarf ribbon',[(.17,.16,1.80),(.33,.24,1.71),(.48,.31,1.54),(.65,.30,1.58)], [.10,.10,.07,.001],[.04,.04,.035,.001],'coral')

def ink_hull(obj):
    # Front-facing polygons are culled, leaving a narrow ink silhouette.
    bpy.ops.object.select_all(action='DESELECT')
    dup=obj.copy(); dup.data=obj.data.copy(); bpy.context.collection.objects.link(dup)
    dup.name=obj.name+' / ink'
    bpy.context.view_layer.objects.active=dup; dup.select_set(True)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mesh=dup.data
    for v in mesh.vertices: v.co+=v.normal*.009
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.reverse_faces(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    mesh.materials.clear(); mesh.materials.append(outline)
    return dup

groups={}
for kind,fn in [('crew',crew),('enemy',lambda:oni('enemy')),('boss',lambda:oni('boss'))]:
    parts=[]; fn(); bpy.context.view_layer.update()
    originals=list(parts)
    outlines=[ink_hull(o) for o in originals if not any(k in o.name for k in ['glint','Lash','lash','Pupil','Iris','Eye white','Eye socket','Glowing eye','Smile','Blush','Eyebrow','marking','mouth','Nose','nose'])]
    groups[kind]=originals+outlines
    collection=bpy.data.collections.new(kind.upper()); bpy.context.scene.collection.children.link(collection)
    for o in groups[kind]:
        for old in list(o.users_collection): old.objects.unlink(o)
        collection.objects.link(o)

scene=bpy.context.scene
# Shader-to-RGB is an Eevee cel shader, not a physically-based approximation.
for engine in ['BLENDER_EEVEE_NEXT','BLENDER_EEVEE']:
    try: scene.render.engine=engine; break
    except TypeError: pass
assert scene.render.engine!='CYCLES','Eevee is required for cel preview'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(*linear('F0EDE5'),1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
bpy.ops.object.light_add(type='SUN',location=(-3,-4,7))
key=bpy.context.object; key.name='Cel key'; key.data.energy=2.0; key.rotation_euler=(math.radians(25),math.radians(-35),math.radians(-25)); key.data.angle=.02
key.data.use_shadow=False
bpy.ops.object.light_add(type='AREA',location=(3,-4,4))
fill=bpy.context.object; fill.data.energy=80; fill.data.size=5
fill.data.use_shadow=False
fill.rotation_euler=(Vector((0,0,1.4))-fill.location).to_track_quat('-Z','Y').to_euler()

scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard'; scene.view_settings.look='None'
scene.render.film_transparent=False
scene.render.resolution_percentage=100
scene.render.image_settings.color_mode='RGBA'

bpy.ops.object.camera_add(location=(5,-13,6))
cam=bpy.context.object; scene.camera=cam; cam.data.type='ORTHO'; cam.data.lens=55
def point_camera(target,ortho):
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=ortho

for kind,x in [('crew',-2.2),('enemy',0),('boss',2.2)]:
    for o in groups[kind]: o.location.x+=x

# A quiet ground with contact shadows, no busy environment obscuring the models.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.01))
floor=bpy.context.object; floor.name='Preview ground'; floor.data.materials.append(cel('Ground','E1DDD7'))

def label(text,loc,size=.18):
    bpy.ops.object.text_add(location=loc)
    o=bpy.context.object; o.data.body=text; o.data.size=size; o.data.align_x='CENTER'
    o.rotation_euler=cam.rotation_euler; o.data.materials.append(lettering)
    return o

cam.location=(4,-15,6.3); point_camera((0,0,1.45),8.0)
labels=[]
for name,x in [('CREW  /  MINT',-2.2),('ONI  /  CORAL',0),('BOSS  /  GOLD',2.2)]:
    labels.append(label(name,(x,-.65,-.18),.16))
scene.render.resolution_x=1800; scene.render.resolution_y=1050
scene.render.filepath=str(OUT/'cel-lineup.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'cel-preview.blend'))
bpy.ops.render.render(write_still=True)

for text in labels: text.hide_render=True
for kind in ['enemy','boss']:
    for o in groups[kind]: o.hide_render=True
cam.location=(-.25,-8.5,3.5); point_camera((-2.2,0,1.55),3.65)
scene.render.resolution_x=1100; scene.render.resolution_y=1300
scene.render.filepath=str(OUT/'crew-closeup.png'); bpy.ops.render.render(write_still=True)

cam.location=(-2.2,-10,2.1); point_camera((-2.2,0,1.55),3.5)
scene.render.filepath=str(OUT/'crew-front.png'); bpy.ops.render.render(write_still=True)
print('CEL_PREVIEW_DONE',OUT)
