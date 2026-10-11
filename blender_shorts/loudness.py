"""ITU-R BS.1770-4 ses yüksekliği (LUFS) ve gerçek tepe (dBTP) ölçümü — yalnız numpy, Blender gerekmez.

Neden: YouTube/Shorts sesi ~-14 LUFS'e çeker; "kulağa iyi geliyor" yetmez. Gerçek projede ilk karışım
-16.8 LUFS / -0.42 dBTP çıktı ve arka plan uğultusu dış sese 4 LU yaklaşmıştı; ölçerek düzeltince
-14.0 LUFS / -1.5 dBTP ve konuşma ile efekt arasında 16+ LU fark elde edildi.

Komut satırı:  python -m blender_shorts.loudness karisim.wav
Kütüphane   :  integrated(x, sr), true_peak(x, sr), short_term_max(x, sr), self_test()
x: (n,) mono veya (n, 2) stereo float dizi, -1..1.
"""
import sys
import wave

import numpy as np


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-12))


def st2(x):
    x = np.asarray(x, float)
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


def filt(x, *secs, sr=44100, pad=None):
    """Biquad kademesini FFT ızgarasında doğrusal evrişim olarak uygular (sıfır dolgu IIR kuyruğunun başa
    sarmasını önler; Python döngüsü yok, uzun dosyalarda hızlı)."""
    n = x.shape[0]
    pad = sr // 2 if pad is None else pad
    m = 1 << int(np.ceil(np.log2(n + pad)))
    zi = np.exp(-2j * np.pi * np.arange(m // 2 + 1) / m)
    H = np.ones(m // 2 + 1, complex)
    for b, a in secs:
        H *= np.polyval(np.asarray(b)[::-1], zi) / np.polyval(np.asarray(a)[::-1], zi)
    X = np.fft.rfft(x, m, axis=0)
    return np.fft.irfft(X * (H[:, None] if x.ndim == 2 else H), m, axis=0)[:n]


def kweight(sr):
    """K-ağırlık filtreleri (raf + yüksek geçiren), herhangi bir örnekleme hızı için (libebur128 formülleri)."""
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / sr)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    shelf = (np.array([(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]),
             np.array([1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]))
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / sr)
    d = 1 + K / Q + K * K
    hp = (np.array([1.0, -2.0, 1.0]), np.array([1.0, 2 * (K * K - 1) / d, (1 - K / Q + K * K) / d]))
    return shelf, hp


def kpower(x, sr):
    y = filt(st2(x), *kweight(sr), sr=sr, pad=sr)
    return (y ** 2).sum(axis=1)


def _blocks(p, sr, win, hop):
    b, h = int(round(win * sr)), int(round(hop * sr))
    cs = np.concatenate([[0.0], np.cumsum(p)])
    st = np.arange(0, max(len(p) - b + 1, 1), h)
    return (cs[np.minimum(st + b, len(p))] - cs[st]) / b


def integrated(x, sr=44100):
    """Kapılı entegre ses yüksekliği (LUFS): 400 ms blok / 100 ms adım, -70 LUFS mutlak, -10 LU göreli kapı."""
    z = _blocks(kpower(x, sr), sr, 0.4, 0.1)
    lv = -0.691 + 10 * np.log10(np.maximum(z, 1e-20))
    g = lv > -70.0
    if not g.any():
        return -np.inf
    rel = -0.691 + 10 * np.log10(z[g].mean()) - 10.0
    g &= lv > rel
    return float(-0.691 + 10 * np.log10(z[g].mean()))


def short_term_max(x, sr=44100):
    """En yüksek kısa süreli (3 sn) ses yüksekliği."""
    z = _blocks(kpower(x, sr), sr, 3.0, 0.1)
    return float(-0.691 + 10 * np.log10(max(z.max(), 1e-20)))


def oversample(x, k=4):
    x = st2(x)
    n = x.shape[0]
    X = np.fft.rfft(x, axis=0)
    Y = np.zeros((n * k // 2 + 1, x.shape[1]), complex)
    Y[:X.shape[0]] = X
    if n % 2 == 0:
        Y[n // 2] *= 0.5
    return np.fft.irfft(Y, n * k, axis=0) * k


def true_peak(x, sr=44100):
    """Gerçek tepe (dBTP), 4× aşırı örnekleme. Örnek tepesi 0 dBFS altında olsa da AAC/MP3 sonrası
    kırpılabilecek ara tepeleri yakalar — hedef ≤ -1 dBTP."""
    return float(db(np.abs(oversample(x)).max()))


def self_test(sr=44100):
    """997 Hz, -20 dBFS tepe stereo sinüs → -20.0 LUFS; fs/4 + 45° sinüs → örnek tepe -3.01 dBFS, gerçek tepe 0 dBTP."""
    t = np.arange(10 * sr) / sr
    s = 0.1 * np.sin(2 * np.pi * 997 * t)
    li = integrated(np.stack([s, s], 1), sr)
    q = np.sin(2 * np.pi * (sr / 4) * t[:sr] + np.pi / 4) * np.hanning(sr) ** 0.05
    tp, sp = true_peak(q, sr), float(db(np.abs(q).max()))
    ok = abs(li + 20.0) < 0.05 and abs(tp) < 0.1 and abs(sp + 3.01) < 0.1
    return ok, dict(lufs=li, sample_peak=sp, true_peak=tp)


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError("yalnız 16 bit PCM WAV destekleniyor")
    x = np.frombuffer(raw, "<i2").astype(float).reshape(-1, ch) / 32768.0
    return (x[:, 0] if ch == 1 else x[:, :2]), sr


def main(argv):
    if not argv:
        ok, r = self_test()
        print("OZ_TEST", "TAMAM" if ok else "HATA", r)
        return 0 if ok else 1
    for p in argv:
        x, sr = read_wav(p)
        li, tp = integrated(x, sr), true_peak(x, sr)
        flag = "TAMAM" if (abs(li + 14) <= 1 and tp <= -1) else "KONTROL"
        print("%s  %.2f LUFS  %.2f dBTP  kısa maks %.1f LUFS  %.2f sn  [%s: hedef -14 LUFS, ≤ -1 dBTP]"
              % (p, li, tp, short_term_max(x, sr), len(x) / sr, flag))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
