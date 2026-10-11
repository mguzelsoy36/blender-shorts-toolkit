"""Seçilen karelerden düşük örnekli EEVEE kontrol ızgarası (4 sütun). Sahneyi KAYDETMEZ.

Kullanım:
  blender -b sahne.blend --python blender_shorts/preview_grid.py -- --name S02_kontrol --frames 56 80 100 150
          [--camera CAM_S02] [--rig CHR_Genc --dist mixamorig:RightHand=KRK_Kasima_Hedef ...]
Çıktı: renders/previews/<ad>.png + her kare için kemik → hedef uzaklıkları (cm).

Ders: Claude'un "bitti" demeden önce kareleri KENDİSİ açıp bakması en çok hatayı yakalayan adımdı.
Tek tek tam kalite kare yerine 270x480 / 16 örnekli ızgara: hızlı, ucuz, tek bakışta 8–12 kare.
Uzaklık çıktısı, "el kulpta mı?" gibi soruları gözden bağımsız sayıyla doğrular (IK düzeltme katmanı için).
"""
import argparse
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="preview_grid")
ap.add_argument("--name", required=True)
ap.add_argument("--frames", type=int, nargs="+", required=True)
ap.add_argument("--camera")
ap.add_argument("--out", default=os.path.join("renders", "previews"))
ap.add_argument("--rig")
ap.add_argument("--dist", nargs="*", default=[], help="KEMIK=HEDEF_NESNE (kemik ucu → nesne)")
ap.add_argument("--w", type=int, default=270)
ap.add_argument("--h", type=int, default=480)
ap.add_argument("--samples", type=int, default=16)
a = ap.parse_args(argv)

os.makedirs(a.out, exist_ok=True)
tmp = os.path.join(a.out, "_tmp_grid.png")
sc = bpy.context.scene
W, H = a.w, a.h
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.eevee.taa_render_samples = a.samples
cam = bpy.data.objects[a.camera] if a.camera else None
if cam:
    for m in sc.timeline_markers:
        m.camera = None                 # işaretçiler sabit kamerayı geri almasın (sahne kaydedilmez)
rig = bpy.data.objects[a.rig] if a.rig else None

tiles = []
for f in a.frames:
    sc.frame_set(f)
    if cam:
        sc.camera = cam
    info = []
    for pair in a.dist:
        bone, tgt = pair.split("=", 1)
        if rig and tgt in bpy.data.objects:
            p = rig.matrix_world @ rig.pose.bones[bone].tail
            info.append("%s→%s %.1f cm" % (bone.split(":")[-1], tgt, (p - bpy.data.objects[tgt].matrix_world.translation).length * 100))
    print("KARE", f, sc.camera.name if sc.camera else "-", " ".join(info))
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp)
    tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4))
    bpy.data.images.remove(img)
while len(tiles) % 4:
    tiles.append(np.zeros((H, W, 4), dtype=np.float32))
rows = [np.concatenate(tiles[r * 4:(r + 1) * 4], axis=1) for r in range(len(tiles) // 4)]
grid = np.concatenate(rows[::-1], axis=0)          # Blender pikselleri alttan başlar
out = bpy.data.images.new("grid", grid.shape[1], grid.shape[0], alpha=True)
out.pixels = grid.ravel()
out.filepath_raw = os.path.abspath(os.path.join(a.out, a.name + ".png"))
out.file_format = "PNG"
out.save()
os.remove(tmp)
print("IZGARA", out.filepath_raw)
