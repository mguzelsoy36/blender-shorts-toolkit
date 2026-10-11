"""PNG dizisini Blender'ın video düzenleyicisiyle H.264 MP4'e çevirir — ffmpeg KURMAK GEREKMEZ.

Kullanım:
  blender -b --factory-startup --python blender_shorts/encode_mp4.py -- --src renders/final/proje --out film_
          [--fps 30 --w 1080 --h 1920] [--audio karisim.wav]
Ders: kareler render sırasında zaten AgX ile işlendi; kodlarken görünüm dönüşümünü "Standard"a almazsanız
renkler İKİ KEZ dönüştürülür ve soluk/gri çıkar.
Blender 5.x: sequence_editor.strips (eski adı sequences), image_settings.media_type = "VIDEO".
"""
import argparse
import os
import re
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="encode_mp4")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True, help="çıktı yolu öneki (Blender kare aralığını ekler)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--audio")
    a = ap.parse_args(argv)

    files = sorted(f for f in os.listdir(a.src) if re.match(r"kare_\d{4}\.png$", f))
    if not files:
        raise SystemExit("kare bulunamadı: " + a.src)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = a.w, a.h, 100
    scene.render.fps = a.fps
    se = scene.sequence_editor_create()
    coll = se.strips if hasattr(se, "strips") else se.sequences
    st = coll.new_image("kareler", os.path.join(a.src, files[0]), 1, 1)
    for f in files[1:]:
        st.elements.append(f)
    if a.audio:
        coll.new_sound("ses", os.path.abspath(a.audio), 2, 1)
    scene.frame_start, scene.frame_end = 1, len(files)
    ims = scene.render.image_settings
    if hasattr(ims, "media_type"):
        ims.media_type = "VIDEO"
    ims.file_format = "FFMPEG"
    ff = scene.render.ffmpeg
    ff.format, ff.codec = "MPEG4", "H264"
    ff.constant_rate_factor = "HIGH"
    ff.ffmpeg_preset = "GOOD"
    if a.audio:
        ff.audio_codec, ff.audio_bitrate = "AAC", 192
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.use_sequencer = True
    scene.render.filepath = os.path.abspath(a.out)
    bpy.ops.render.render(animation=True)
    print("VIDEO", scene.render.frame_path(), "kare", len(files))


if __name__ == "__main__":
    main()
