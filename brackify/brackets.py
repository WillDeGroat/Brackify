from typing import List, Optional, Sequence
import math
import random
from brackify.spotify_client import TrackInfo


AllowedBracketSizes = (16, 32, 64)


def _validated_size(size: int) -> int:
    if size not in AllowedBracketSizes:
        raise ValueError(f'size must be one of {AllowedBracketSizes}')

    return size


def build_seed_list(tracks: Sequence[TrackInfo], size: int, order: str = 'playlist', rng: Optional[random.Random] = None) -> List[Optional[TrackInfo]]:
    validated_size = _validated_size(size)

    if rng is None:
        rng = random.Random()

    ordered_tracks = list(tracks)
    if order == 'randomized':
        rng.shuffle(ordered_tracks)
    elif order != 'playlist':
        raise ValueError('order must be playlist or randomized')

    seeds = ordered_tracks[:validated_size]

    if len(seeds) < validated_size:
        seeds.extend([None] * (validated_size - len(seeds)))

    return seeds


def chunk_matches(seeds: Sequence[Optional[TrackInfo]]) -> List[List[Optional[TrackInfo]]]:
    if not seeds or math.log2(len(seeds)) % 1 != 0:
        raise ValueError('seed list length must be a power of two')

    return [list(seeds[i:i + 2]) for i in range(0, len(seeds), 2)]
