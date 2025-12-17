import random
import pytest
from brackify.brackets import build_seed_list, chunk_matches, AllowedBracketSizes


TRACKS = [
    {'track_id': '1', 'song_name': 'A', 'artists': 'X', 'album_name': 'Al', 'image_url': None},
    {'track_id': '2', 'song_name': 'B', 'artists': 'Y', 'album_name': 'Al', 'image_url': None},
    {'track_id': '3', 'song_name': 'C', 'artists': 'Z', 'album_name': 'Al', 'image_url': None},
]


def test_build_seed_list_playlist_order_fills_missing():
    seeds = build_seed_list(TRACKS[:2], 16, order = 'playlist')
    assert len(seeds) == 16
    assert seeds[0]['track_id'] == '1'
    assert seeds[1]['track_id'] == '2'
    assert all(s is None for s in seeds[2:])


def test_build_seed_list_randomized_is_deterministic_with_seed():
    rng = random.Random(42)
    seeds = build_seed_list(TRACKS, 16, order = 'randomized', rng = rng)
    ids = [s['track_id'] if s else None for s in seeds]
    assert ids[:3] == ['2', '1', '3']


def test_build_seed_list_rejects_invalid_size():
    with pytest.raises(ValueError):
        build_seed_list(TRACKS, 8)


def test_chunk_matches_requires_power_of_two():
    with pytest.raises(ValueError):
        chunk_matches([None, None, None])


@pytest.mark.parametrize('size', AllowedBracketSizes)
def test_chunk_matches_shapes_pairs(size):
    seeds = build_seed_list(TRACKS, size)
    matches = chunk_matches(seeds)
    assert len(matches) == size // 2
    assert all(len(m) == 2 for m in matches)
