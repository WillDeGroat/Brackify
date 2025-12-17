import pytest

spotipy = pytest.importorskip('spotipy')

from brackify.spotify_client import extract_playlist_id, get_spotify_client


def test_extract_playlist_id_from_url():
    inp = 'https://open.spotify.com/playlist/3lLCifNYnouhplcrQIC1iX?si=abc123'
    assert extract_playlist_id(inp) == '3lLCifNYnouhplcrQIC1iX'


def test_extract_playlist_id_from_id():
    inp = '3lLCifNYnouhplcrQIC1iX'
    assert extract_playlist_id(inp) == '3lLCifNYnouhplcrQIC1iX'


def test_get_spotify_client_missing_env(monkeypatch):
    monkeypatch.delenv('SPOTIFY_CLIENT_ID', raising = False)
    monkeypatch.delenv('SPOTIFY_CLIENT_SECRET', raising = False)

    with pytest.raises(RuntimeError):
        get_spotify_client()


def test_fetch_playlist_tracks_rejects_invalid_limit(monkeypatch):
    from brackify import spotify_client

    class DummyClient:
        def playlist_items(self, *args, **kwargs):
            raise AssertionError('playlist_items should not be called for invalid limit')

    with pytest.raises(ValueError):
        spotify_client.fetch_playlist_tracks('123', DummyClient(), limit = 0)
