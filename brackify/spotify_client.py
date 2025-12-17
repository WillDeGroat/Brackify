from typing import List, TypedDict, Optional, TYPE_CHECKING, Any
import os

try:  # pragma: no cover - optional convenience helper
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional
    load_dotenv = None

try:  # pragma: no cover - dependency presence is environment-specific
    import spotipy  # type: ignore
    from spotipy.oauth2 import SpotifyClientCredentials  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully at runtime
    spotipy = None
    SpotifyClientCredentials = None

if TYPE_CHECKING:  # pragma: no cover
    import spotipy as spotipy_type


class TrackInfo(TypedDict):
    track_id: Optional[str]
    song_name: str
    artists: str
    album_name: str
    image_url: Optional[str]


def extract_playlist_id(inp: str) -> str:
    s = inp.strip()

    if 'https://open.spotify.com/playlist/' in s:
        s = s.split('open.spotify.com/playlist/')[1]
        s = s.split('?')[0].split('/')[0]

    return s


def get_spotify_client() -> 'spotipy_type.Spotify':
    if spotipy is None or SpotifyClientCredentials is None:
        raise RuntimeError('spotipy is required to talk to the Spotify API. Install it with pip install spotipy.')

    if load_dotenv is not None:
        load_dotenv()

    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

    if not client_id or not client_secret:
        raise RuntimeError('SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is missing from the environment.')

    auth = SpotifyClientCredentials(client_id = client_id, client_secret = client_secret)

    return spotipy.Spotify(auth_manager = auth)


def fetch_playlist_tracks(inp: str, sp: Any, limit: int = 100) -> List[TrackInfo]:
    pid = extract_playlist_id(inp)

    res: List[TrackInfo] = []
    offset = 0

    if limit <= 0:
        raise ValueError('limit must be a positive integer')

    while True:
        page = sp.playlist_items(playlist_id = pid, offset = offset, limit = limit,
                                 fields = 'items(added_at,track(id,name,album(name),artists(name))),next,total', additional_types = ['track'])

        items = page.get('items', [])
        for item in items:
            s = item.get('track')
            if not s:
                continue

            images = ((s.get('album') or {}).get('images') or [])
            image_url = images[0]['url'] if images else None
            track_id = s.get('id')
            song_name = s.get('name')
            album_name = (s.get('album') or {}).get('name')
            artists = [a.get('name') for a in (s.get('artists') or []) if a.get('name')]

            res.append({
                'track_id': track_id,
                'song_name': song_name,
                'artists': ', '.join(artists),
                'album_name': album_name,
                'image_url': image_url,
            })

        if not page.get('next'):
            break

        offset += limit

    return res
