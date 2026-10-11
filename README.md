# blender-shorts-toolkit

**Claude Code + Blender 5.x ile tamamen betikle dikey YouTube Shorts üretmek için sınanmış araçlar, şablonlar ve dersler.**
*Tested tools, templates and lessons for producing vertical YouTube Shorts entirely from Python scripts with Claude Code and Blender 5.x — free assets only (MakeHuman/MPFB, Mixamo, Poly Haven).*

İki tamamlanmış Shorts projesinden (35 sn'lik bir ilk yardım anlatımı ve 9 sn'lik bir döngü videosu) çıkarıldı;
zayıf bir dizüstünde (GTX 950M, 8 GB RAM), Türkçe Blender arayüzüyle, ücretli hiçbir şey kullanmadan.

👉 **Önce oku: [DERSLER.md](DERSLER.md)** — çalışma düzeni, Blender 5.x API tuzakları, retarget, kamera/ışık, ses ölçümü, lisans.

## İçerik

| Dosya | Ne yapar | Gerekir |
|---|---|---|
| [`blender_shorts/retarget_mixamo.py`](blender_shorts/retarget_mixamo.py) | Mixamo FBX → `mixamorig` iskeleti; eklentisiz, dünya uzayında delta aktarımı, parmak ucu yürüyüşü düzeltmesi, otomatik zemine oturtma, sürümlü kayıt | Blender |
| [`blender_shorts/motion_utils.py`](blender_shorts/motion_utils.py) | Ayak gömülme/kayma ölçümü, ARKit yüz anahtarları + göz kırpma, Blender 5.x `channelbag` | Blender |
| [`blender_shorts/fx_lib.py`](blender_shorts/fx_lib.py) | Kamera push-in / Gürültü / sarsıntı (±180° düzeltmeli), beyaz flaş, acı halkaları, kıvılcım, deri ışıması, Bloom (5.x birleştirici), işaretçi-kamera bağlama | Blender |
| [`blender_shorts/preview_grid.py`](blender_shorts/preview_grid.py) | Seçili karelerden hızlı kontrol ızgarası + kemik→hedef uzaklıkları | Blender |
| [`blender_shorts/render_resume.py`](blender_shorts/render_resume.py) | Kaldığı yerden devam eden PNG render, isteğe bağlı EDL ile kısaltılmış film | Blender |
| [`blender_shorts/encode_mp4.py`](blender_shorts/encode_mp4.py) | PNG → H.264 MP4 (+AAC), **ffmpeg gerekmez** | Blender |
| [`blender_shorts/edl.py`](blender_shorts/edl.py) | Kurgu listesi: film ↔ kaynak kare eşlemesi, tek kaynak | Python |
| [`blender_shorts/loudness.py`](blender_shorts/loudness.py) | ITU-R BS.1770-4 LUFS + gerçek tepe (dBTP), öz testli | numpy |
| [`examples/edl_buzdolabi.py`](examples/edl_buzdolabi.py) | Gerçek proje kurgusu: 357 kaynak kare → 268 film karesi | Python |
| [`templates/`](templates/) | `CLAUDE.md`, `shots.md`, `PROGRESS.md` ve 5 rol ajanı (`.claude/agents/`) | — |

## Hızlı başlangıç

```bash
# 1) Şablonları yeni proje klasörüne kopyala
cp templates/CLAUDE.md templates/shots.md templates/PROGRESS.md YeniProje/
mkdir -p YeniProje/.claude/agents && cp templates/agents/*.md YeniProje/.claude/agents/

# 2) Mixamo kliplerini aktar
blender -b scenes/proje_v003.blend --python blender_shorts/retarget_mixamo.py -- \
    --rig CHR_Genc --mocap assets/mocap --scenes scenes --prefix proje walking.fbx=MOC_Yurume

# 3) Kontrol ızgarası
blender -b scenes/proje_v004.blend --python blender_shorts/preview_grid.py -- --name S01_kontrol --frames 1 12 21 40

# 4) Son render (kaldığı yerden devam eder) → MP4
blender -b scenes/proje_v010.blend --python blender_shorts/render_resume.py -- --out renders/final/proje --samples 64
blender -b --factory-startup --python blender_shorts/encode_mp4.py -- --src renders/final/proje --out renders/final/proje_ --audio karisim.wav

# 5) Ses ölçümü (hedef -14 LUFS, ≤ -1 dBTP)
python -m blender_shorts.loudness karisim.wav
```

Windows'ta `blender` yerine tam yol: `"D:\blender.exe"`. Blender 5.2.2 LTS ile sınandı.

## Testler

```bash
python -m pytest tests      # edl + loudness (Blender gerekmez)
```

## Lisans

Kod MIT. Bu depo hiçbir 3D varlık, ses veya mocap dosyası içermez; kullandığınız varlıkların lisansını
(ör. CC-BY atıf) kendiniz takip edin — bkz. DERSLER.md §7.
