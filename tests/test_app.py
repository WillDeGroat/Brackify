from datetime import datetime, timedelta, timezone

from brackify.app import EXPIRATION_HOURS, create_app, remaining_ttl_seconds


def _sample_bracket(bracket_id: str, created_at: datetime) -> dict:
    return {
        'size': 4,
        'order': 'playlist',
        'seed_count': 4,
        'seeds': [],
        'matches': [],
        'total_tracks': 4,
        'bracket_name': 'Test bracket',
        'bracket_id': bracket_id,
        'share_url': f'/bracket/{bracket_id}',
        'created_at': created_at.isoformat(),
    }


def _save_bracket(app, bracket_id: str, created_at: datetime) -> None:
    payload = _sample_bracket(bracket_id, created_at)
    ttl = remaining_ttl_seconds(created_at, app.expiration_delta)
    app.bracket_store.save(bracket_id, payload, ttl)


def test_expired_bracket_is_removed_and_returns_not_found():
    app = create_app()
    client = app.test_client()

    expired_time = datetime.now(timezone.utc) - timedelta(hours = EXPIRATION_HOURS + 1)
    _save_bracket(app, 'expired', expired_time)

    response = client.get('/api/bracket/expired')

    assert response.status_code == 404
    assert app.bracket_store.get('expired') is None


def test_active_bracket_stays_available():
    app = create_app()
    client = app.test_client()

    fresh_time = datetime.now(timezone.utc)
    _save_bracket(app, 'fresh', fresh_time)

    response = client.get('/api/bracket/fresh')

    assert response.status_code == 200
    assert response.get_json()['bracket_id'] == 'fresh'
    assert app.bracket_store.get('fresh') is not None


def test_bracket_creation_requires_name(monkeypatch):
    app = create_app()
    client = app.test_client()

    monkeypatch.setattr('brackify.app.get_spotify_client', lambda: None)
    monkeypatch.setattr(
        'brackify.app.fetch_playlist_tracks',
        lambda playlist, sp: [
            {
                'track_id': str(i),
                'song_name': f'Song {i}',
                'artists': 'Artist',
                'album_name': 'Album',
                'image_url': None,
            }
            for i in range(1, 33)
        ],
    )

    response = client.post('/api/bracket', json = {
        'playlist': 'dummy',
        'order': 'playlist',
        'size': 16,
    })

    assert response.status_code == 400
    assert 'bracket_name' in response.get_json()['error']
