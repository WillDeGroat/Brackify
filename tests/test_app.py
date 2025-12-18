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
        'playlist': 'playlist123',
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


def _tracks(count: int = 16):
    return [{'track_id': str(i), 'song_name': f'Song {i}', 'artists': 'Artist', 'album_name': 'Album', 'image_url': None} for i in range(1, count + 1)]


def test_reuses_existing_bracket_and_refreshes_timestamp(monkeypatch):
    app = create_app()
    client = app.test_client()
    fetch_calls = {'count': 0}

    app.bracket_index.clear()

    monkeypatch.setattr('brackify.app.get_spotify_client', lambda: None)

    def _fetch(playlist, sp):
        fetch_calls['count'] += 1
        return _tracks()

    monkeypatch.setattr('brackify.app.fetch_playlist_tracks', _fetch)

    initial_response = client.post('/api/bracket', json = {
        'playlist': 'playlist123',
        'order': 'playlist',
        'size': 16,
        'bracket_name': 'My bracket',
    })

    first_payload = initial_response.get_json()
    original_id = first_payload['bracket_id']

    stale_time = datetime.now(timezone.utc) - timedelta(hours = 1)
    stored_payload = app.bracket_store.get(original_id)
    assert stored_payload
    stored_payload['created_at'] = stale_time.isoformat()
    ttl = remaining_ttl_seconds(stale_time, app.expiration_delta)
    app.bracket_store.save(original_id, stored_payload, ttl)

    reused_response = client.post('/api/bracket', json = {
        'playlist': 'playlist123',
        'order': 'playlist',
        'size': 16,
        'bracket_name': 'My bracket',
    })

    reused_payload = reused_response.get_json()

    assert reused_response.status_code == 200
    assert reused_payload['bracket_id'] == original_id
    assert reused_payload['share_url'] == first_payload['share_url']
    assert datetime.fromisoformat(reused_payload['created_at']) > stale_time
    assert fetch_calls['count'] == 1


def test_creates_new_bracket_when_existing_is_expired(monkeypatch):
    app = create_app()
    client = app.test_client()
    fetch_calls = {'count': 0}

    monkeypatch.setattr('brackify.app.get_spotify_client', lambda: None)

    def _fetch(playlist, sp):
        fetch_calls['count'] += 1
        return _tracks()

    monkeypatch.setattr('brackify.app.fetch_playlist_tracks', _fetch)

    initial_response = client.post('/api/bracket', json = {
        'playlist': 'playlist123',
        'order': 'playlist',
        'size': 16,
        'bracket_name': 'My bracket',
    })

    first_payload = initial_response.get_json()
    first_id = first_payload['bracket_id']

    expired_time = datetime.now(timezone.utc) - timedelta(hours = EXPIRATION_HOURS + 1)
    stored_payload = app.bracket_store.get(first_id)
    assert stored_payload
    stored_payload['created_at'] = expired_time.isoformat()
    ttl = remaining_ttl_seconds(expired_time, app.expiration_delta)
    app.bracket_store.save(first_id, stored_payload, ttl)

    new_response = client.post('/api/bracket', json = {
        'playlist': 'playlist123',
        'order': 'playlist',
        'size': 16,
        'bracket_name': 'My bracket',
    })

    new_payload = new_response.get_json()

    assert new_response.status_code == 200
    assert new_payload['bracket_id'] != first_id
    assert app.bracket_store.get(first_id) is None
    assert fetch_calls['count'] == 2
