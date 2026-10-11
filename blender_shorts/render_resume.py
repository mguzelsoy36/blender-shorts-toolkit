"""Kaldığı yerden devam eden son render: PNG dizisi, var olan kareleri atlar (çökme/elektrik kesintisi güvenli).

Kullanım:
  blender -b sahne.blend --python blender_shorts/render_resume.py -- --out renders/final/proje [--start 1 --end 268]
          [--samples 64] [--edl edl_proje.py]
--edl verilirse: dosya EDL adlı bir edl.EDL nesnesi tanımlar; film karesi n için kaynak karesi render edilir
ve kare_n.png olarak yazılır (kurgu masasındaki kısaltma, render'da birebir uygulanır).
Kamera, kaynak karedeki zaman çizelgesi işaretçisinden AÇIKÇA seçilir ve her satırda yazdırılır
(frame_set'in kamera geçişine güvenmeyin; kesme karelerinde yanlış kamera görmek pahalı bir 4 saatlik hatadır).

Ders: her projenin kendi çıktı klasörü olsun. Eski projenin kare_0001…png dosyaları aynı klasördeyse
"var" sayılıp atlanır ve film yanlış karelerle birleşir.
"""
import argparse
import importlib.util
import os
import sys
import time

import bpy


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="render_resume")
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=int)
    ap.add_argument("--end", type=int)
    ap.add_argument("--samples", type=int)
    ap.add_argument("--edl", help="EDL nesnesi tanımlayan .py dosyası")
    return ap.parse_args(argv)


def load_edl(path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("proje_edl", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.EDL


def marker_camera(scene, f):
    ms = [m for m in scene.timeline_markers if m.camera and m.frame <= f]
    return max(ms, key=lambda m: m.frame).camera if ms else scene.camera


def main():
    a = parse()
    scene = bpy.context.scene
    edl = load_edl(a.edl) if a.edl else None
    f0 = a.start or (1 if edl else scene.frame_start)
    f1 = a.end or (edl.end if edl else scene.frame_end)
    if a.samples:
        scene.eevee.taa_render_samples = a.samples
    os.makedirs(a.out, exist_ok=True)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    print("ORNEK", scene.eevee.taa_render_samples, "KARE", f0, f1, flush=True)
    for n in range(f0, f1 + 1):
        path = os.path.join(a.out, "kare_%04d.png" % n)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        t = time.time()
        src = edl.src_of(n) if edl else n
        scene.frame_set(src)
        scene.camera = marker_camera(scene, src)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("KARE %d <- kaynak %d %.1f sn %s" % (n, src, time.time() - t, scene.camera.name), flush=True)
    print("BITTI", flush=True)


if __name__ == "__main__":
    main()
