"""Yeniden kullanılabilir efekt ve kamera fonksiyonları (tüm çekimler kullanır).

Hepsi idempotent: aynı adla tekrar çağrıldığında eski nesneyi/düğümü silip yeniden kurar.
Blender 5.2 notları: action.fcurves yok → motion_utils.channelbag(); Türkçe arayüzde düğüm
adları çevrilir → düğümler türle bulunur, kendi düğümlerimiz "FX_" önekiyle adlandırılır.
"""
import math
import bpy
from mathutils import Vector, Euler

try:
    from . import motion_utils as mu
except ImportError:          # betik olarak: sys.path'e bu klasörü ekleyin
    import motion_utils as mu


# ------------------------------------------------------------------ genel
def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def clear_coll(c):
    for o in list(c.objects):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and getattr(data, "users", 1) == 0:
            for block in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
                if data.name in block and block[data.name] is data:
                    block.remove(data)
                    break


def empty(name, loc, c, size=0.02):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = size
    o.location = loc
    c.objects.link(o)
    return o


def key_visibility(obj, visible_from, visible_to):
    """Nesne yalnızca [visible_from, visible_to] karelerinde render'da görünür."""
    for f, hidden in ((visible_from - 1, True), (visible_from, False), (visible_to + 1, True)):
        obj.hide_render = hidden
        obj.hide_viewport = hidden
        obj.keyframe_insert("hide_render", frame=f)
        obj.keyframe_insert("hide_viewport", frame=f)


def set_constant(obj):
    ad = obj.animation_data
    if ad and ad.action:
        for fc in mu.channelbag(ad.action).fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def emission_material(name, color, strength):
    """Saydam ↔ ışık yayan karışım; 'FX_Mix' düğümünün Fac'ı ile görünürlük anahtarlanır."""
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "FX_Emission"
    em.inputs["Color"].default_value = tuple(color[:3]) + (1.0,)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.name = "FX_Mix"
    mix.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    return m


def key_fac(mat, frame, value):
    s = mat.node_tree.nodes["FX_Mix"].inputs[0]
    s.default_value = value
    s.keyframe_insert("default_value", frame=frame)


def no_shadow(obj):
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False


# ------------------------------------------------------------------ efektler
def white_flash(cam, frame, c, dur=2, name="FX_Flas"):
    """Kameranın hemen önünde beyaz ışık yayan düzlem: [frame, frame+dur-1] boyunca ekran beyaz."""
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    p = bpy.context.active_object
    p.name = name
    for uc in list(p.users_collection):
        uc.objects.unlink(p)
    c.objects.link(p)
    p.parent = cam
    p.location = (0, 0, -max(cam.data.clip_start * 2.0, 0.02))
    p.scale = (2.0, 2.0, 1.0)
    p.data.materials.append(emission_material("MAT_" + name, (1, 1, 1), 25.0))
    no_shadow(p)
    key_visibility(p, frame, frame + dur - 1)
    return p


def pain_rings(center, cam, start, c, n=3, color=(1.0, 0.06, 0.02), r_max=0.16, life=16, stagger=4,
               name="FX_AciHalka", strength=3.5, thickness=0.035):
    """Temas noktasından büyüyüp sönen, kameraya bakan ışıklı halkalar.
    Not: AgX çok parlak ışımayı beyaza kaydırır → doygun kırmızı için güç düşük (3–5) tutulur."""
    rings = []
    for i in range(n):
        s = start + i * stagger
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=thickness, major_segments=64,
                                         minor_segments=8, location=center)
        t = bpy.context.active_object
        t.name = "%s_%d" % (name, i)
        for uc in list(t.users_collection):
            uc.objects.unlink(t)
        c.objects.link(t)
        con = t.constraints.new("TRACK_TO")
        con.target, con.track_axis, con.up_axis = cam, "TRACK_Z", "UP_Y"
        mat = emission_material("MAT_%s_%d" % (name, i), color, strength)
        t.data.materials.append(mat)
        no_shadow(t)
        for f, sc, fac in ((s, 0.01, 1.0), (s + life * 0.4, r_max * 0.7, 1.0), (s + life, r_max, 0.0)):
            t.scale = (sc, sc, sc)
            t.keyframe_insert("scale", frame=f)
            key_fac(mat, f, fac)
        key_visibility(t, s, s + life)
        rings.append(t)
    return rings


def pain_sparks(center, cam, start, c, n=10, color=(1.0, 0.25, 0.04), length=0.07, reach=0.14, life=10,
                name="FX_Kivilcim", strength=4.0, width=0.0025):
    """Temas noktasından dışa fırlayan ince ışık çizgileri (kameraya bakan düzlemde)."""
    pivot = empty(name + "_Pivot", center, c)
    con = pivot.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = cam, "TRACK_Z", "UP_Y"
    mat = emission_material("MAT_" + name, color, strength)
    out = []
    for i in range(n):
        ang = 2 * math.pi * i / n + (0.25 if i % 2 else 0.0)
        bpy.ops.mesh.primitive_plane_add(size=1.0)
        p = bpy.context.active_object
        p.name = "%s_%d" % (name, i)
        for uc in list(p.users_collection):
            uc.objects.unlink(p)
        c.objects.link(p)
        p.data.materials.append(mat)
        no_shadow(p)
        p.parent = pivot
        p.rotation_euler = (0, 0, ang)
        d = Vector((math.cos(ang), math.sin(ang), 0))
        r0, r1 = reach * 0.25, reach * (0.9 + 0.2 * (i % 3) / 2)
        for f, r, sx in ((start, r0, 0.2), (start + life * 0.5, (r0 + r1) / 2, 1.0), (start + life, r1, 0.05)):
            p.location = d * r
            p.scale = (length * sx, width, 1)
            p.keyframe_insert("location", frame=f)
            p.keyframe_insert("scale", frame=f)
        key_visibility(p, start, start + life)
        out.append(p)
    key_fac(mat, start, 1.0)
    key_fac(mat, start + life, 0.0)
    return out


def skin_glow(objs, center_obj, keys, color=(1.0, 0.08, 0.03), radius=0.07, power=1.6):
    """Deri malzemesine, center_obj'ye uzaklıkla maskelenen kırmızı ışıma ekler.
    keys: [(kare, güç), ...] — 'FX_Glow_Guc' değer düğümü anahtarlanır."""
    mats = {m for o in objs for m in o.data.materials if m and m.use_nodes}
    for m in mats:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        old_add = nt.nodes.get("FX_Glow_Add")
        if old_add:
            src = old_add.inputs[0].links[0].from_socket if old_add.inputs[0].links else None
            for n in [n for n in nt.nodes if n.name.startswith("FX_Glow")]:
                nt.nodes.remove(n)
            if src:
                nt.links.new(src, out.inputs["Surface"])
        surf = out.inputs["Surface"].links[0].from_socket
        tc = nt.nodes.new("ShaderNodeTexCoord")
        tc.name, tc.object = "FX_Glow_TC", center_obj
        ln = nt.nodes.new("ShaderNodeVectorMath")
        ln.name, ln.operation = "FX_Glow_Len", "LENGTH"
        nt.links.new(tc.outputs["Object"], ln.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.name = "FX_Glow_Map"
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.0, radius
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
        mr.clamp = True
        nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
        sq = nt.nodes.new("ShaderNodeMath")
        sq.name, sq.operation = "FX_Glow_Sq", "POWER"
        sq.inputs[1].default_value = power
        nt.links.new(mr.outputs["Result"], sq.inputs[0])
        val = nt.nodes.new("ShaderNodeValue")
        val.name = "FX_Glow_Guc"
        mul = nt.nodes.new("ShaderNodeMath")
        mul.name, mul.operation = "FX_Glow_Mul", "MULTIPLY"
        nt.links.new(sq.outputs[0], mul.inputs[0])
        nt.links.new(val.outputs[0], mul.inputs[1])
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "FX_Glow_Em"
        em.inputs["Color"].default_value = tuple(color[:3]) + (1.0,)
        nt.links.new(mul.outputs[0], em.inputs["Strength"])
        add = nt.nodes.new("ShaderNodeAddShader")
        add.name = "FX_Glow_Add"
        nt.links.new(surf, add.inputs[0])
        nt.links.new(em.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs["Surface"])
        for f, v in keys:
            val.outputs[0].default_value = v
            val.outputs[0].keyframe_insert("default_value", frame=f)
    return mats


# ------------------------------------------------------------------ kamera
def look_rot(loc, target, compat=None):
    """compat: önceki anahtarın Euler'i. -Y'ye bakan kamerada Z dönüşü ±180° sınırında; uyumlu Euler
    verilmezse iki anahtar +180/-180 çıkabilir ve kamera arada 360° döner."""
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    return q.to_euler("XYZ", compat) if compat is not None else q.to_euler()


def camera(name, c, lens, fstop, focus_obj, clip_start=0.01):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cd)
    c.objects.link(cam)
    cd.lens, cd.clip_start = lens, clip_start
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.focus_object = focus_obj
    return cam


def camera_path(cam, f0, f1, loc0, loc1, target):
    """Yavaş yaklaşma (push-in): konum ve bakış iki uçta anahtarlanır, arası yumuşak."""
    prev = None
    for f, loc in ((f0, loc0), (f1, loc1)):
        cam.location = loc
        cam.rotation_euler = prev = look_rot(loc, target, prev)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


def camera_shake(cam, frame, amp_deg=1.2, frames=10, freq=2.2):
    """Darbe sarsıntısı: dönüşe sönümlenen salınım anahtarları ekler."""
    scene = bpy.context.scene
    for i in range(frames + 1):
        f = frame + i
        scene.frame_set(f)
        base = cam.rotation_euler.copy()
        d = math.radians(amp_deg) * math.exp(-i / (frames * 0.35)) * math.sin(i * freq)
        cam.rotation_euler = Euler((base.x + d, base.y + d * 0.4, base.z - d * 0.7))
        cam.keyframe_insert("rotation_euler", frame=f)


def camera_noise(cam, f0, f1, loc_strength=0.004, rot_strength=0.004, scale=14.0):
    """El kamerası titreşimi: F-eğrilerine Gürültü [Noise] değiştiricisi, çekim aralığıyla sınırlı."""
    for fc in mu.channelbag(cam.animation_data.action).fcurves:
        if fc.data_path not in ("location", "rotation_euler"):
            continue
        for mod in [m for m in fc.modifiers if m.type == "NOISE"]:
            fc.modifiers.remove(mod)
        mod = fc.modifiers.new("NOISE")
        mod.strength = loc_strength if fc.data_path == "location" else rot_strength
        mod.scale = scale
        mod.phase = 7.3 * (fc.array_index + 1) + (0 if fc.data_path == "location" else 3.1)
        mod.use_restricted_range = True
        mod.frame_start, mod.frame_end = f0, f1
        mod.blend_in = mod.blend_out = 2


def hero_foot_enable(f0, f1, hero_name="HERO_Ayak_R", mask_name="HERO_AyakGizle"):
    """[f0, f1] karelerinde kahraman ayağı görünür yapar, gövdedeki MakeHuman ayağını maskeyle gizler.
    Birden çok çekim için tekrar çağrılabilir (anahtarlar birikir, sabit enterpolasyon)."""
    hero = bpy.data.objects.get(hero_name)
    if hero is None:
        return False
    key_visibility(hero, f0, f1)
    body = next(o for o in hero.parent.children if o.name.endswith(".body"))
    mod = body.modifiers[mask_name]
    for f, on in ((f0 - 1, False), (f0, True), (f1 + 1, False)):
        mod.show_render = mod.show_viewport = on
        mod.keyframe_insert("show_render", frame=f)
        mod.keyframe_insert("show_viewport", frame=f)
    return True


def setup_glare(threshold=1.2, strength=0.55, size=0.6, name="CMP_Parlama"):
    """Sahne geneli parlama (Bloom): yalnızca eşiği aşan ışık yayan efektler ve yanık vurgular parlar.
    Blender 5.x: birleştirici, scene.compositing_node_group'a atanan bir düğüm grubudur."""
    scene = bpy.context.scene
    ng = bpy.data.node_groups.get(name)
    if ng:
        bpy.data.node_groups.remove(ng)
    ng = bpy.data.node_groups.new(name, "CompositorNodeTree")
    ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    gl = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    for ident in ("Bloom", "BLOOM", "Fog Glow", "FOG_GLOW"):
        try:
            gl.inputs["Type"].default_value = ident
            break
        except (TypeError, ValueError):
            continue
    gl.inputs["Threshold"].default_value = threshold
    gl.inputs["Strength"].default_value = strength
    gl.inputs["Size"].default_value = size
    ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
    ng.links.new(gl.outputs[0], out.inputs[0])
    scene.compositing_node_group = ng
    print("PARLAMA tip", gl.inputs["Type"].default_value, "esik", threshold, "guc", strength)
    return ng


def bind_marker(name, frame, cam):
    scene = bpy.context.scene
    for m in [m for m in scene.timeline_markers if m.name == name]:
        scene.timeline_markers.remove(m)
    m = scene.timeline_markers.new(name, frame=frame)
    m.camera = cam
    return m
