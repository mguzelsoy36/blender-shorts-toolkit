"""Kurgu listesi (EDL) — animasyonu yeniden yapmadan filmi kısaltmanın TEK KAYNAĞI.

Ders: Onaylı anlatım görüntüden uzun/kısa çıktığında animasyonu ve kameraları yeniden yapmak yerine,
sahneyi tek kesintisiz kaynak olarak bırakıp filmi kaynaktan seçilen aralıklarla "kurgu masasında" kurmak
çok daha güvenli. Kesmeleri kamera geçişlerine koyun: zaman sıçraması izleyiciye doğal kesme olarak okunur.
Ses planı, son render ve montaj betikleri aynı EDL'den okur → kare numaraları asla kaymaz.

Örnek:
    edl = EDL([("S01", 1, 38), ("S02", 74, 106)], fps=30)
    edl.end            # 71 (filmin son karesi)
    edl.src_of(39)     # 74 (film karesi → kaynak karesi)
    edl.out_of(80)     # 45 (kaynak karesi → film karesi, atıldıysa None)
"""


class EDL:
    def __init__(self, cuts, fps=30):
        """cuts: [(ad, kaynak_başı, kaynak_sonu), ...] — film karelerine sırayla dizilir (1'den başlar)."""
        if not cuts:
            raise ValueError("EDL boş")
        for name, s0, s1 in cuts:
            if s1 < s0:
                raise ValueError("%s: kaynak sonu başından küçük (%d < %d)" % (name, s1, s0))
        self.cuts, self.fps = list(cuts), fps

    def segments(self):
        """[(ad, film_başı, film_sonu, kaynak_başı, kaynak_sonu), ...]"""
        out, n = [], 1
        for name, s0, s1 in self.cuts:
            out.append((name, n, n + s1 - s0, s0, s1))
            n += s1 - s0 + 1
        return out

    @property
    def end(self):
        return self.segments()[-1][2]

    @property
    def duration(self):
        return self.end / self.fps

    def src_of(self, n):
        for _, o0, o1, s0, _ in self.segments():
            if o0 <= n <= o1:
                return s0 + n - o0
        raise ValueError("film karesi aralık dışı: %d" % n)

    def out_of(self, f):
        """Kaynak karesi → film karesi. Aynı kaynak kare birden çok kez kullanıldıysa ilki döner."""
        for _, o0, _, s0, s1 in self.segments():
            if s0 <= f <= s1:
                return o0 + f - s0
        return None

    def cut_frames(self):
        """Film içindeki kesme kareleri (ilk parça hariç her parçanın başı) — ses whoosh'ları için."""
        return [seg[1] for seg in self.segments()[1:]]

    def seconds(self, n):
        """Film karesi n'nin başlangıç zamanı (sn): (n-1)/fps."""
        return (n - 1) / self.fps

    def report(self):
        lines = ["%-10s film %4d–%4d  kaynak %4d–%4d  (%d kare, %.2f sn)"
                 % (seg + (seg[2] - seg[1] + 1, (seg[2] - seg[1] + 1) / self.fps)) for seg in self.segments()]
        lines.append("FILM %d kare = %.2f sn" % (self.end, self.duration))
        return "\n".join(lines)
