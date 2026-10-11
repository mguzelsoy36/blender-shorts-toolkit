"""Hareket ölçüm ve düzeltme yardımcıları (Blender 5.x).

- sole_track / contact_report: ayak tabanı gömülme ve kayma (foot sliding) ölçümü — gözle değil sayıyla kontrol.
- face_keys / blink: ARKit adlı yüz şekil anahtarlarını karakterin TÜM meshlerine (kaş, kirpik, diş...) birlikte yazar.
- channelbag: Blender 5.x'te action.fcurves YOK; F-eğrilerine katmanlı/slot'lu aksiyon üzerinden erişim.
- offset_hips_*: kalça anahtarlarını dünya uzayında kaydırma (zemine oturtma, temas noktasına taşıma).
Kemik adları varsayılan olarak Mixamo (mixamorig:*); PREFIX ile değiştirilebilir.
"""
import bpy
import numpy as np
from mathutils import Vector

SIDES = ("Left", "Right")
PREFIX = "mixamorig:"


def assign_action(rig, act):
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = act
    if hasattr(rig.animation_data, "action_slot") and getattr(act, "slots", None):
        rig.animation_data.action_slot = act.slots[0]


def _seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def sole_track(rig, body, f0, f1, step=1, radius=0.09):
    """Her karede sol/sağ ayak tabanının en alçak noktası (dünya). Maske modifikatörü köşe
    sırasını değiştirdiği için köşeler ayak kemiği segmentine uzaklıkla (9 cm) seçilir.
    Döner: {"Left": [(kare, z, Vector(xy)), ...], "Right": [...]}"""
    scene = bpy.context.scene
    track = {s: [] for s in SIDES}
    for f in range(f0, f1 + 1, step):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        mw = np.array(ev.matrix_world)
        P = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        for s in SIDES:
            a = np.array(rig.matrix_world @ rig.pose.bones["%s%sFoot" % (PREFIX, s)].head)
            b = np.array(rig.matrix_world @ rig.pose.bones["%s%sToeBase" % (PREFIX, s)].tail)
            sel = P[_seg_dist(P, a, b) < radius]
            low = sel[np.argmin(sel[:, 2])]
            track[s].append((f, float(low[2]), Vector((float(low[0]), float(low[1])))))
        ev.to_mesh_clear()
    return track


def contact_report(track, tol=0.015):
    """Basma: taban, klipteki en alçak değerine 'tol' kadar yakınsa. Kayma: her basma
    diliminde tabanın yatay yer değiştirmesi (en büyüğü)."""
    out = {}
    for s, data in track.items():
        zs = [d[1] for d in data]
        ground = min(zs)
        slide, seg, planted = 0.0, [], 0
        for d in data + [(None, 1e9, None)]:
            if d[1] < ground + tol:
                seg.append(d)
                planted += 1 if d[0] is not None else 0
            else:
                if len(seg) > 2:
                    slide = max(slide, max((p[2] - seg[0][2]).length for p in seg))
                seg = []
        out[s] = {"min_z": ground, "max_z": max(zs), "planted": planted, "frames": len(data), "slide": slide}
    return out


def face_keys(rig, frame, values):
    """Yüz şekil anahtarlarını (ARKit adları) karakterin TÜM meshlerinde (gövde, kaş, kirpik, göz,
    diş...) aynı değerle anahtarlar. values: {"eyeBlinkLeft": 1.0, ...}"""
    n = 0
    for o in rig.children:
        if o.type != "MESH" or not o.data.shape_keys:
            continue
        kbs = o.data.shape_keys.key_blocks
        for name, v in values.items():
            kb = kbs.get(name)
            if kb is not None:
                kb.value = v
                kb.keyframe_insert("value", frame=frame)
                n += 1
    return n


def blink(rig, frame, extra=None):
    """Doğal göz kırpma: 1 kare kapanış, 3 kare açılış."""
    base = dict(extra or {})
    for f, v in ((frame - 1, 0.0), (frame + 1, 1.0), (frame + 4, 0.0)):
        vals = dict(base)
        vals.update({"eyeBlinkLeft": v, "eyeBlinkRight": v})
        face_keys(rig, f, vals)


def channelbag(act):
    from bpy_extras import anim_utils
    return anim_utils.action_get_channelbag_for_slot(act, act.slots[0])


def offset_hips_vec(rig, act, vec_world, hips="mixamorig:Hips"):
    """Kalça konum anahtarlarını dünya vektörü kadar kaydırır (rig dönüşümü hesaba katılır)."""
    rest = rig.data.bones[hips].matrix_local.to_3x3()
    v = rest.inverted() @ (rig.matrix_world.to_3x3().inverted() @ Vector(vec_world))
    path = 'pose.bones["%s"].location' % hips
    for fc in channelbag(act).fcurves:
        if fc.data_path == path:
            d = v[fc.array_index]
            for kp in fc.keyframe_points:
                kp.co.y += d
                kp.handle_left.y += d
                kp.handle_right.y += d
            fc.update()


def offset_hips_world(rig, act, dz, hips="mixamorig:Hips"):
    """Kalça konum anahtarlarını dünya Z'sinde dz kadar kaydırır (zemine oturtma)."""
    offset_hips_vec(rig, act, (0, 0, dz), hips)
