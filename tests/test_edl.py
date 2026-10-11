import pytest

from blender_shorts.edl import EDL

# Buzdolabı Döngüsü'nün gerçek kurgusu: 357 karelik kaynak → 268 karelik film
REAL = [("S01", 1, 38), ("S02", 74, 106), ("S03_S04", 151, 259), ("S05", 268, 355)]


def test_real_project_length():
    e = EDL(REAL)
    assert e.end == 268
    assert abs(e.duration - 8.93) < 0.01


def test_round_trip():
    e = EDL(REAL)
    for n in range(1, e.end + 1):
        assert e.out_of(e.src_of(n)) == n


def test_cut_frames_and_dropped_source():
    e = EDL(REAL)
    assert e.cut_frames() == [39, 72, 181]
    assert e.src_of(39) == 74
    assert e.out_of(50) is None          # kurguda atılan kaynak kare


def test_out_of_range():
    with pytest.raises(ValueError):
        EDL(REAL).src_of(269)


def test_bad_cut():
    with pytest.raises(ValueError):
        EDL([("X", 10, 5)])
