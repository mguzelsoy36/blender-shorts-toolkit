import numpy as np
import pytest

from blender_shorts import loudness as L


@pytest.mark.parametrize("sr", [44100, 48000])
def test_self_test(sr):
    ok, r = L.self_test(sr)
    assert ok, r


def test_gain_shifts_lufs_exactly():
    sr = 48000
    rng = np.random.default_rng(1)
    x = 0.05 * rng.standard_normal((sr * 5, 2))
    a = L.integrated(x, sr)
    b = L.integrated(x * 10 ** (6 / 20), sr)
    assert abs((b - a) - 6.0) < 0.01


def test_silence_is_gated():
    assert L.integrated(np.zeros(48000 * 2), 48000) == -np.inf


def test_wav_roundtrip(tmp_path):
    import wave
    sr = 44100
    t = np.arange(sr * 2) / sr
    s = (0.1 * np.sin(2 * np.pi * 997 * t) * 32767).astype("<i2")
    p = tmp_path / "t.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.stack([s, s], 1).tobytes())
    x, sr2 = L.read_wav(str(p))
    assert sr2 == sr and x.shape == (sr * 2, 2)
    assert abs(L.integrated(x, sr) + 20.0) < 0.1
