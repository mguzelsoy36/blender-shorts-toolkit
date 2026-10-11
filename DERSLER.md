# Dersler: Claude Code + Blender 5.2 ile iki Shorts filminden öğrenilenler

Bu belge, tamamen betikle (Python) ve Claude Code ile üretilen iki dikey YouTube Shorts projesinin
günlüklerinden (PROGRESS.md), betiklerinden ve hatalarından çıkarıldı:

| Proje | Süre | Çekim | Son render | Sonuç |
|---|---|---|---|---|
| **Sehpaya Çarpan Ayak** (ilk yardım anlatımı) | 35 sn, 1050 kare | 7 çekim + X-ray | ~10 saat, 64 örnek | TR + EN sürüm, gömülü altyazı |
| **Buzdolabı Döngüsü** ("Why do we ALL do this?") | 8.93 sn, 268 kare | 5 çekim, döngü | ~4 saat, 30–74 sn/kare | -14.02 LUFS, -1.46 dBTP, 4.3 MB |

Donanım: GTX 950M, 8 GB RAM, Windows, Blender 5.2.2 LTS (Türkçe arayüz), EEVEE. Her şey ücretsiz:
MPFB/MakeHuman (CC0), Mixamo, Poly Haven (CC0), edge-tts, numpy.

Blender adları Türkçe yazıldı, İngilizce orijinali köşeli parantezde.

---

## 1. Claude Code ile çalışma düzeni

**1.1 CLAUDE.md bir sözleşmedir, "rica" değil.** En çok işe yarayan kurallar yasak biçiminde yazılanlardı:
karakteri asla küp/küreden kurma; hareket mocap'ten gelsin, elle anahtar kare yalnız *düzeltme katmanı*;
yüzün göründüğü çekimde şekil anahtarı [Shape Keys] ifadesi şart; yer tutucu ile teslim yok —
kalite çizgisine ulaşılamıyorsa **dur, tek paragrafta açıkla, eksik varlığı listele.** Bu son kural sayesinde
Claude "şimdilik böyle olsun" çözümleri yerine somut istekler üretti (ör. "Mixamo'da kafa kaşıma klibi yok;
düşünme klibi + el IK düzeltmesi önerisi"). Şablon: [`templates/CLAUDE.md`](templates/CLAUDE.md).

**1.2 PROGRESS.md oturumlar arası hafızadır.** Her oturum başında CLAUDE.md + shots.md + PROGRESS.md okunur,
her adımdan sonra güncellenir. En değerli satırlar: **kalın yazılmış güncel sahne sürümü**, "DİKKAT" notları
(ör. "v010–v013 BOZUK, kullanma") ve "Sıradaki adım". Yeni bilgi en üste yazılınca dosya ters kronolojik
okunur; bu, uzun projede bağlamı hızlı toparlar.

**1.3 Bir seferde tek çekim, kullanıcı onayıyla.** Yönetmen kullanıcıdır; Claude teknik yönetmendir.
Seçenekleri (ör. S01 için A/B kamera açısı) önizleme kareleriyle sunup karar beklemek, geri dönüşü pahalı
işleri (4–10 saatlik render) korudu.

**1.4 .blend'in üzerine asla yazma; artan sürüm kaydet** (`sahne_v001.blend`, `v002` …). Bir betik hatası
(`place_rig`) bir aksiyonu sessizce bozup dört sürümü kullanılmaz yaptığında, temiz sürüme dönmek dakikalar
sürdü. *Ama*: sürümler diski doldurur → proje sonunda **çekim başına tek onaylı sürüm** kuralı kondu,
ara denemeler geçici klasöre.

**1.5 Betikler idempotent olmalı.** Nesneler adıyla bulunur/silinip yeniden kurulur, her çekim kendi
koleksiyonunda (`S03_Tepki`), kendi kamerasıyla (`CAM_S03`). Böylece "betiği tekrar çalıştır" her zaman
güvenli bir düzeltme yoludur.

**1.6 Tek kaynak dosyaları.** Kurgu (`frg_kurgu.py` → bu depoda [`edl.py`](blender_shorts/edl.py)) ve ses
planı (satırlar, efektler, düzeyler) tek dosyada; render, karışım, altyazı ve montaj betikleri oradan okur.
Kare numaraları elle kopyalanınca kayıyordu; tek kaynaktan sonra kaymadı.

**1.7 Rol ajanları + bağımsız kalite ajanı.** `.claude/agents/` altında yönetmen, set-karakter, animatör,
görüntü-efekt ve kalite-render. En değerlisi **sahneyi değiştirmeyen, yalnız raporlayan** kalite ajanı:
"başkasının işini iyi saymaya meyilli olma; şüphede kusur olarak raporla" talimatıyla, çekim sınırındaki
hareket bulanıklığı bozulmasını (kare 60) yakaladı. Şablonlar: [`templates/agents/`](templates/agents/).

**1.8 Görsel kontrol zorunlu ve sayısal.** "Bitti" demeden önce ilk kare / temas karesi / en yoğun an /
son kare render edilip **Claude tarafından açılıp incelenir**; en fazla 3 düzeltme turu, sonra dürüst rapor.
Göze ek olarak sayı: temas aralığı (kare 21'de 0.08 cm), taban gömülmesi, el-kulp uzaklığı (3–6 cm).
Hızlı ızgara: [`preview_grid.py`](blender_shorts/preview_grid.py).

**1.9 Blender'ı arka planda çalıştır:** `blender.exe -b sahne.blend --python betik.py -- argümanlar`.
Eklenti tercihleri gereken işlerde (MPFB) `--factory-startup` **kullanma**; kodlama/ses gibi saf işlerde kullan.

**1.10 Hesaplar.** Claude şifre girmez, hesap açmaz. Mixamo/Sketchfab için kullanıcı Claude'un tarayıcı
panelinde **bir kez** giriş yapar; arama ve indirmeyi Claude yapar. Not: panelde kaydetme penceresi açılmaz,
dosya `Downloads` klasörüne `.tmp` uzantısıyla düşer → Claude `assets/mocap/`'a taşır.
Mixamo ayarı: FBX Binary, Without Skin, 30 fps, Keyframe Reduction none.

**1.11 Zayıf donanım bütçesi.** Dokular ≤ 2K; önizleme 16 örnek, son render 64. 1M yüzlü 8K dokulu bir
fotogrametri taraması bilgisayarı dondurdu → 60k yüze indirilen başka model kullanıldı. Ağır işlemleri tek
tek çalıştır.

---

## 2. Blender 5.x API tuzakları (tahmin etme, doğrula)

| Belirti | Neden | Çözüm |
|---|---|---|
| `action.fcurves` AttributeError | 5.x katmanlı/slot'lu aksiyonlar | `bpy_extras.anim_utils.action_get_channelbag_for_slot(act, act.slots[0]).fcurves` → [`motion_utils.channelbag`](blender_shorts/motion_utils.py) |
| Aksiyon atanıyor ama oynamıyor | Slot atanmamış | `animation_data.action_slot = act.slots[0]` |
| Birleştirici [Compositor] düğümleri bulunamıyor | 5.x'te birleştirici bir düğüm grubu | `scene.compositing_node_group = ng` → [`fx_lib.setup_glare`](blender_shorts/fx_lib.py) |
| Parlama [Glare] tipi hata veriyor | enum adı sürüme göre değişiyor | `"Bloom"`, `"BLOOM"`, `"Fog Glow"` sırayla dene |
| Video düzenleyici kodu çalışmıyor | `sequences` → `strips`; `image_settings.media_type = "VIDEO"` | `hasattr` ile iki yolu da destekle → [`encode_mp4.py`](blender_shorts/encode_mp4.py) |
| Düğüm adıyla bulunamıyor | **Türkçe arayüz** yeni düğümlere Türkçe ad verir | Düğümü `type` ile bul; kendi düğümlerine `FX_` önekli ad ver |
| Kapı açısına bağlı ışık arka plan render'ında hep 0 | Sürücüler [Drivers] (SCRIPTED da AVERAGE da) `-b` kipinde 0 döndü | Sürücü kullanma; ışığı kapıyla **aynı karelerde** anahtarla |
| Motor adı | 5.x: `BLENDER_EEVEE` | `bpy.app.version` yazdır, `hasattr/dir` ile doğrula, sürüm farkını `try/except` ile koru |

---

## 3. Karakter ve hareket

**3.1 Karakter hattı (ücretsiz):** MPFB 2 + MakeHuman CC0 paketleri; `faceunits01` ile **52 ARKit yüz şekil
anahtarı**; iskelet seçeneği Mixamo (`mixamorig:*`, 52 kemik) → Mixamo klipleri ek eşleme olmadan aktarılır.
Yüz anahtarlarını yalnız gövdeye değil **kaş, kirpik, göz, diş, dil, saç** meshlerine de yaz
([`face_keys`](blender_shorts/motion_utils.py)); yoksa kaşlar yüzden ayrılır.

**3.2 Notlara değil ölçüme güven.** Notlarda karakter boyu 1.67 m yazıyordu; gerçek 1.46 m çıktı. Buzdolabı,
raf ve kamera yükseklikleri ölçülen değere göre yeniden kuruldu.

**3.3 Retarget dersi: sabit düzeltme bir belirtidir.** Tüm kliplerde "sabit ~5.5 cm gömülme" vardı ve kalça
indirilerek "düzeltildi". Asıl neden: ayak/parmak kemikleri Mixamo dinlenme yönüne hizalanınca ayak aşağı
bükülüyor, karakter **parmak ucunda** yürüyordu (topuk ön ayaktan ~5 cm yukarıda). Çözüm: `Foot/ToeBase`
hizalamasını kapat → zemin payı 5.5 cm'den 1.2–1.6 cm'ye indi. [`retarget_mixamo.py`](blender_shorts/retarget_mixamo.py)
bunu varsayılan yapar.

**3.4 Zemine oturtma:** her karedeki en alçak tabanın **ortancası** hedefe çekilir; zıplama gibi havada
kareler sonucu bozmaz. Gömülme ve kayma (foot sliding) [`sole_track` / `contact_report`](blender_shorts/motion_utils.py)
ile ölçülür.

**3.5 Mixamo'da olmayan hareket:** "sehpaya çarpma tepkisi", "kafa kaşıma" yoktu. Elle sıfırdan yazmak yerine:
en yakın klip (düşünme: el çeneye) + **düzeltme katmanı** (IK hedefi kafa yüzeyinde, Gürültü [Noise] ile
parmak titreşimi). El yanlış taraftaysa klibin **aynalı** sürümünü indir (sol el kulpta).
Hedef konumu önemli: kaşıma hedefi kafa merkezine konunca el alnın *içine* girdi → hedef kafa yüzeyine
(merkezden 7.4–9.5 cm) taşındı.

**3.6 Baş yönü:** klip başı 26° döndürüyordu; Kilitli İz [Locked Track] kısıtı (etki 0.75) ile ~13°'ye
indirildi, bakış hedefi rafları tarar.

**3.7 Ağır çekim:** yalnız o çekimin NLA şerit ölçeğiyle (4 kaynak kare → 20 kare, temas sonrası donma).
Genel Zaman Yeniden Eşleme [Time Remapping] kullanma — kamerayı ve diğer çekimleri de bozar.

**3.8 Yakın çekim için ayrı "kahraman" varlık:** MakeHuman ayağı 85 mm yakın çekimde yetersiz kaldı →
ayrı yüksek detaylı ayak modeli, gövdedeki ayak Maske [Mask] değiştiricisiyle yalnız o karelerde gizlenir
([`fx_lib.hero_foot_enable`](blender_shorts/fx_lib.py)). Otomatik eksen tahmini bu modelde **iki kez yanlış**
çıktı → eksenler elle zorlanıp gözle doğrulandı.

**3.9 Kıyafet "yamuk yumuk":** kapüşonlu ağ vücut kaslarını yansıtıyordu (doku veya gölge değil).
Çözüm: İskelet [Armature]'den **sonra** Laplace Yumuşatma [Laplacian Smooth] (λ 0.9, 12 tekrar, hacim
koruma); tişörte -1.2 cm Yer Değiştirme [Displace]; eşofmanı yumuşatma (bel kapüşonludan taşdı).

---

## 4. Kamera, ışık, efekt

**4.1 Hiçbir kamera sabit durmaz:** yavaş push-in + F-eğrisi Gürültü [Noise] değiştiricisi (kısıtlı aralık,
düşük güç) + darbede sönümlenen sarsıntı → [`camera_path / camera_noise / camera_shake`](blender_shorts/fx_lib.py).

**4.2 Euler ±180° tuzağı:** -Y'ye bakan kamerada iki anahtar +180° / -180° çıkınca kamera arada **360° döndü**.
`to_euler("XYZ", önceki_euler)` (uyumlu Euler) ile çözüldü — [`look_rot`](blender_shorts/fx_lib.py).

**4.3 Yüz ışığı:** yakın çekimde kamera ana ışığın **karşı** tarafında olmalı; aynı taraftan yüz düz ve soluk.
Kamera kolun kaldırıldığı taraftaysa kol yüzü kapatır → yüzün diğer yanına al.

**4.4 Gölge Bağlama [Shadow Linking]:** kalkık kol yüze keskin, kumlu bir gölge bandı düşürüyordu → iç ışıklar
gövde/kapüşonludan gölge almaz (koleksiyon EXCLUDE). Sahne geneli, tek seferlik çözüm.

**4.5 Kapalı kutuda EEVEE ortam ışığı sızar** (gri, kumlu görüntü) → karanlık anlarda Pozlama [Exposure]
anahtarı (0 → -7 → 0).

**4.6 Malzeme:** cam rafta DITHERED kırılma düşük örnekte kumlu → BLENDED alfa. AgX çok güçlü ışımayı
beyaza kaydırır → doygun kırmızı efektlerde Işık Yayma [Emission] gücü 3–5.

**4.7 Işık teşhisi eleme ile yapılır:** "güneş şeridi görünmüyor" sorununda perde/tavan tek tek gizlendi;
sonunda suçlu aşırı dolgu ışığıydı. Buzdolabı taşma ışığı 140 W yüzü düzleştirdi → 40 W.

**4.8 Çekim sınırı hatası:** kesme karesinde hareket bulanıklığı [Motion Blur] bir sonraki çekimin kamerasından
iz taşıyordu (kare 60) — kalite ajanı yakaladı. Çözüm: bulanıklık konumu START + her çekimin animasyonu son
karesinin 0.6 kare ötesine kadar sürer; böylece bulanıklık penceresi kesmeyi aşmaz.

**4.9 Stil kararını kullanıcı verir:** karanlık/ruhani ilk ışık denemesi reddedildi ("gündüz, tamamen aydınlık").
Uzun render öncesi stil karesini onaylatmak saatler kazandırır.

---

## 5. Kurgu, ses, altyazı

**5.1 Anlatımı önce ölç.** Onaylı metin görüntüyle eşleşince 11.7 sn tuttu, video 9.5 sn'ydi. Çözüm iki adımlı
oldu: yeni bir kapanış çekimi (S05) ve sonra animasyona dokunmadan **kurgu masasında kısaltma** (EDL: 357
kaynak kare → 268 film karesi). Ders: TTS'i animasyondan **önce** üret, süresini ölç, çekimleri ona göre planla.

**5.2 TTS tek seferde okunur, sonra kesilir.** Tüm metin tek parça okununca tonlama doğal; kelime sınırı
zamanlarından satırlara bölünüp her satır planlı karesine yerleştirilir. Kelime kelime SRT'de satır sonu kelimesi
sonraki satırın ilk kelimesiyle üst üste biniyordu → düzeltildi (kelimeler asla örtüşmez).

**5.3 Ses yüksekliğini ölç:** hedef **-14 LUFS, gerçek tepe ≤ -1 dBTP**, ölçüm AAC kodlamasından **sonra**.
İlk karışım -16.8 LUFS / -0.42 dBTP ve uğultu dış sese 4 LU yakındı; ducking + kompresör + ileri bakışlı
limiter ile -14.01 LUFS / -1.50 dBTP, konuşma-efekt farkı 16.5–33 LU. Telefon hoparlörü için 400 Hz yüksek
geçirenle ayrıca kontrol. Ölçüm modülü: [`loudness.py`](blender_shorts/loudness.py) (BS.1770-4, öz testli).

**5.4 Efekt zamanlaması:** whoosh tepe noktası tam kesme karesinde; döngü noktasında iki vurgu üst üste
binince "çift vuruş" → ikincisi ters vurguya çevrildi; saat tıkırtısı kapı açılınca durur.

**5.5 Efektleri numpy ile sentezle:** indirme yok, lisans sorunu yok, istenen uzunlukta.

**5.6 ffmpeg şart değil:** PNG dizisi Blender video düzenleyicisiyle H.264'e çevrilir. Kodlarken görünüm
dönüşümünü **Standard** yap — kareler zaten AgX'ten geçti, yoksa renkler iki kez dönüşüp solar.

**5.7 Her projenin kendi çıktı klasörü:** eski projenin `kare_0001…png` dosyaları aynı klasördeyse
kaldığı-yerden-devam mantığı onları "var" sayıp atlar → yanlış film. Son render kamerayı işaretçiden
**açıkça** seçip her satıra yazar ([`render_resume.py`](blender_shorts/render_resume.py)).

---

## 6. Shorts formatı

- 1080x1920, 30 fps. Güvenli alan: alt ~%20 ve sağ ~%15 YouTube arayüzü altında kalır.
- Kanca ilk 1 saniyede; çekim 1.5–3 sn'de bir değişir.
- Son kare ilk kareye (veya ikinci çekimin ilk karesine) görsel olarak bağlanır → döngü.
- Kısa ve soru soran video ("Why do we all do this? Tell me in the comments.") yorum davet eder.
- Hedef kitle ABD/Kanada/İngiltere ise İngilizce dış ses ve İngilizce gömülü altyazı.

---

## 7. Lisans ve hukuk

- Her varlık `LICENSES.md` tablosuna: kaynak URL, yazar, lisans, ticari kullanım, atıf gerekir mi.
- CC0 (Poly Haven, çoğu MakeHuman paketi) atıf istemez; **CC-BY** olanlar (ör. bir kapüşonlu, kahraman ayak)
  video açıklamasına atıf ister — hazır metni dosyada tut.
- Mixamo: ücretsiz, telifsiz ticari kullanım.
- **edge-tts dış sesinin para kazanılan videoda lisansı belirsiz** → para kazanma açılacaksa kendi sesinle
  yeniden kaydet (betik: yalnız ses dosyasını değiştir, montajı yeniden çalıştır).

---

## 8. Süre bütçesi (GTX 950M)

| İş | Süre |
|---|---|
| Önizleme ızgarası (8–12 kare, 270x480, 16 örnek) | birkaç dakika |
| Son render, 1080x1920, 64 örnek | 30–74 sn/kare → 268 kare ≈ 4 saat; 1050 kare ≈ 10 saat |
| Karışım + ölçüm (numpy) | < 1 dakika |

Render'ı geceye bırak; kaldığı yerden devam ettiğinden kesinti sorun değil.

---

## 9. Yeni proje kontrol listesi

1. `templates/` içinden CLAUDE.md, shots.md, PROGRESS.md, ajanları kopyala; hikâyeyi shots.md'ye yaz.
2. Anlatımı yaz → TTS üret → **süreyi ölç** → çekim kare aralıklarını buna göre koy.
3. Karakteri doğrula: kemik sayısı, 52 yüz anahtarı, **gerçek boy ölçümü**.
4. Mixamo kliplerini indir → `retarget_mixamo.py` → `contact_report` ile gömülme/kayma kontrolü.
5. Her çekim: kamera + işaretçi, düzeltme katmanı, yüz anahtarları + göz kırpma → `preview_grid.py` →
   kareleri aç, kontrol listesini raporla → kullanıcı onayı.
6. Kurguyu `EDL` ile tek kaynaktan kur; ses planı ve render oradan okusun.
7. Karışım → `loudness.py` ile -14 LUFS / ≤ -1 dBTP → sesli önizleme → onay.
8. `render_resume.py` (projeye özel klasör) → `encode_mp4.py` → AAC sonrası yeniden ölç.
9. LICENSES.md atıf metnini video açıklamasına ekle.
