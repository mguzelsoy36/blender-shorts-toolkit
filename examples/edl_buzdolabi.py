"""Gerçek örnek: "Buzdolabı Döngüsü" kurgusu. Anlatım 9.5 sn'lik görüntüye sığmayınca animasyon değiştirilmedi;
357 karelik kesintisiz kaynak sahneden 4 aralık seçilerek 268 karelik (8.93 sn) film kuruldu.
Kesmeler kamera geçişlerinde. render_resume.py -- --edl examples/edl_buzdolabi.py ile kullanılır.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "blender_shorts"))
from edl import EDL as _EDL  # noqa: E402

EDL = _EDL([
    ("S01", 1, 38),         # kanca: kapı 22'de aralanır, kesme kapı ~58°'de
    ("S02", 74, 106),       # içeriden bakış → el kafaya, kaşıma
    ("S03_S04", 151, 259),  # kapanış + karanlık + tekrar açılış + umut
    ("S05", 268, 355),      # yakın çekim: tarama → lense bakış → boş bakış (döngü)
], fps=30)

if __name__ == "__main__":
    print(EDL.report())
