"""Mixamo FBX hareketlerini Mixamo adlı (mixamorig:*) iskelete aktarır — ücretsiz, eklentisiz, Blender 5.x.

Kullanım:
  blender -b sahne_v003.blend --python blender_shorts/retarget_mixamo.py -- \
      --rig CHR_Genc --mocap assets/mocap --scenes scenes --prefix sahne \
      walking.fbx=MOC_Yurume opening_door.fbx=MOC_Kapi_Ac
Çıktı: her klip için sahte kullanıcılı "MOC_*" aksiyonu + scenes/<prefix>_v(NNN+1).blend (üzerine yazmaz).
Idempotent: aynı adlı aksiyon varsa silinip yeniden üretilir.

Yöntem (dünya uzayında delta aktarımı):
  1) Kaynak T-pozunda, hedef A-pozunda. Hedefin her kemiği kaynağın dinlenme yönüne en kısa dönüşle
     hizalanarak sanal bir "T-pozu" hesaplanır (bükülme korunur).
     İSTİSNA: Foot/ToeBase/Toe_End HİZALANMAZ. Hizalanınca ayak aşağı bükülür → karakter parmak ucunda
     yürür ve "sabit ~5 cm gömülme" gibi görünür (gerçek projede bu hatayı yaşadık; --align-feet eski davranış).
  2) Her karede: hedef_dünya = kaynak_dünya(kare) · kaynak_dinlenme⁻¹ · hedef_T
  3) Kalça konumu kalça yüksekliği oranıyla ölçeklenir (ayak kaymasını azaltır).
  4) Zemine oturtma: her karedeki en alçak tabanın ORTANCASI hedefe çekilir (zıplama kareleri etkilemez).
"""
import argparse
import os
import re
import statistics
import sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion_utils as mu  # noqa: E402

HIPS = "mixamorig:Hips"
NO_ALIGN = ("Foot", "ToeBase", "Toe_End")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="retarget_mixamo")
    ap.add_argument("--rig", required=True, help="hedef iskelet nesnesinin adı")
    ap.add_argument("--mocap", default="assets/mocap", help="FBX klasörü")
    ap.add_argument("--scenes", default="scenes", help="sürümlü .blend klasörü")
    ap.add_argument("--prefix", default="sahne", help="kaydedilecek dosya öneki: <prefix>_vNNN.blend")
    ap.add_argument("--sole", type=float, default=0.006, help="taban yüksekliği hedefi (m)")
    ap.add_argument("--body-suffix", default=".body", help="gövde meshinin ad soneki (MPFB: .body)")
    ap.add_argument("--align-feet", action="store_true", help="eski davranış: ayakları da hizala (önerilmez)")
    ap.add_argument("clips", nargs="+", help="dosya.fbx=AKSIYON_ADI")
    return ap.parse_args(argv)


ARGS = None
FOOT_FIX = True
SOLE_TARGET = 0.006


def rot_q(m):
    return m.to_3x3().normalized().to_quaternion()


def bone_dir(obj, bone):
    return (obj.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)).normalized()


def ordered(bones):
    return sorted(bones, key=lambda b: len(b.parent_recursive))


def import_source(path):
    before = set(bpy.data.objects)
    acts_before = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == "ARMATURE")
    new_acts = [a for a in bpy.data.actions if a not in acts_before]
    return src, new, new_acts


def retarget(src, tgt, action_name):
    scene = bpy.context.scene
    act = src.animation_data.action
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])

    tbones = ordered(list(tgt.data.bones))
    shared = {b.name for b in tbones if b.name in src.data.bones}

    # Dinlenme yönelimleri (dünya)
    src_rest = {n: rot_q(src.matrix_world @ src.data.bones[n].matrix_local) for n in shared}
    tgt_T = {}
    for b in tbones:
        if b.name not in shared:
            continue
        q_rest = rot_q(tgt.matrix_world @ b.matrix_local)
        if FOOT_FIX and b.name.split(":")[-1].replace("Left", "").replace("Right", "") in NO_ALIGN:
            tgt_T[b.name] = q_rest      # ayak dinlenme yönü korunur (aşağı bükülme olmaz)
            continue
        align = bone_dir(tgt, b).rotation_difference(bone_dir(src, src.data.bones[b.name]))
        tgt_T[b.name] = align @ q_rest

    src_hips_rest = src.matrix_world @ src.data.bones[HIPS].head_local
    tgt_hips_rest = tgt.matrix_world @ tgt.data.bones[HIPS].head_local
    scale = (tgt_hips_rest.z - tgt.matrix_world.translation.z) / (src_hips_rest.z - src.matrix_world.translation.z)

    # Temiz başlangıç
    if tgt.animation_data is None:
        tgt.animation_data_create()
    tgt.animation_data.action = None
    for pb in tgt.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.matrix_basis = Matrix.Identity(4)

    tgt_inv = tgt.matrix_world.inverted()
    tgt_inv_q = rot_q(tgt.matrix_world).inverted()
    rest = {b.name: b.matrix_local for b in tbones}

    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        pose = {}
        for b in tbones:
            n = b.name
            p = b.parent
            # Ebeveyne bağlı dinlenme dönüşümü (bu kemiğin "temel" pozu)
            base = (pose[p.name] @ rest[p.name].inverted() @ rest[n]) if p else rest[n].copy()
            if n in shared:
                q_src = rot_q(src.matrix_world @ src.pose.bones[n].matrix)
                q_world = q_src @ src_rest[n].inverted() @ tgt_T[n]
                q_arm = tgt_inv_q @ q_world
                if n == HIPS:
                    src_hips = src.matrix_world @ src.pose.bones[n].head
                    head = tgt_inv @ (tgt_hips_rest + (src_hips - src_hips_rest) * scale)
                else:
                    head = base.translation
                m = Matrix.Translation(head) @ q_arm.to_matrix().to_4x4()
            else:
                m = base
            pose[n] = m
            basis = base.inverted() @ m
            pb = tgt.pose.bones[n]
            pb.rotation_quaternion = basis.to_quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=f - f0 + 1)
            if n == HIPS:
                pb.location = basis.translation
                pb.keyframe_insert("location", frame=f - f0 + 1)

    new_act = tgt.animation_data.action
    new_act.name = action_name
    new_act.use_fake_user = True

    # Zemine oturtma: iskelet oranı farkından gelen sabit gömülmeyi kalça Z'si ile düzelt.
    # Her karedeki en alçak tabanın ORTANCASI kullanılır (zıplama gibi havada kareler etkilemez).
    body = next(o for o in tgt.children if o.name.endswith(ARGS.body_suffix))
    tr = mu.sole_track(tgt, body, 1, f1 - f0 + 1, step=2)
    per_frame = [min(l[1], r[1]) for l, r in zip(tr["Left"], tr["Right"])]
    dz = SOLE_TARGET - statistics.median(per_frame)
    mu.offset_hips_world(tgt, new_act, dz)
    print("ZEMIN", action_name, "kalca_dz_cm", round(dz * 100, 1))

    tgt.animation_data.action = None
    for pb in tgt.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    print("AKTARILDI", action_name, "kare", f1 - f0 + 1, "kalca_olcek", round(scale, 3))


def next_version_path(scenes, prefix):
    pat = re.compile(re.escape(prefix) + r"_v(\d{3})\.blend$")
    os.makedirs(scenes, exist_ok=True)
    nums = [int(m.group(1)) for f in os.listdir(scenes) if (m := pat.match(f))]
    return os.path.join(scenes, "%s_v%03d.blend" % (prefix, max(nums, default=0) + 1))


def main():
    global ARGS, FOOT_FIX, SOLE_TARGET
    ARGS = parse_args()
    FOOT_FIX, SOLE_TARGET = not ARGS.align_feet, ARGS.sole
    clips = [tuple(a.split("=", 1)) for a in ARGS.clips]
    print("BLENDER", bpy.app.version_string)
    tgt = bpy.data.objects[ARGS.rig]
    saved_loc, saved_rot = tgt.location.copy(), tgt.rotation_euler.copy()
    tgt.location, tgt.rotation_euler = (0, 0, 0), (0, 0, 0)   # ölçüm için başlangıç noktası
    for fname, aname in clips:
        old = bpy.data.actions.get(aname)
        if old:
            bpy.data.actions.remove(old)
        src, new_objs, new_acts = import_source(os.path.join(ARGS.mocap, fname))
        retarget(src, tgt, aname)
        for o in new_objs:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in new_acts:
            if a.users == 0 or a.name != aname:
                bpy.data.actions.remove(a)
    tgt.location, tgt.rotation_euler = saved_loc, saved_rot
    bpy.context.scene.frame_set(1)
    path = next_version_path(ARGS.scenes, ARGS.prefix)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("KAYDEDILDI", path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
