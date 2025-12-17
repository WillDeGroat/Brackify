from datetime import datetime, timedelta, timezone

from brackify.app import EXPIRATION_HOURS, create_app


def _sample_bracket(bracket_id: str, created_at: datetime) -> dict:
    return {
        'size': 4,
        'order': 'playlist',
        'seed_count': 4,
        'seeds': [],
        'matches': [],
        'total_tracks': 4,
        'bracket_id': bracket_id,
        'share_url': f'/bracket/{bracket_id}',
        'created_at': created_at.isoformat(),
    }


def test_expired_bracket_is_removed_and_returns_not_found():
    app = create_app()
    client = app.test_client()

    expired_time = datetime.now(timezone.utc) - timedelta(hours = EXPIRATION_HOURS + 1)
    app.brackets['expired'] = _sample_bracket('expired', expired_time)

    response = client.get('/api/bracket/expired')

    assert response.status_code == 404
    assert 'expired' not in app.brackets


def test_active_bracket_stays_available():
    app = create_app()
    client = app.test_client()

    fresh_time = datetime.now(timezone.utc)
    app.brackets['fresh'] = _sample_bracket('fresh', fresh_time)

    response = client.get('/api/bracket/fresh')

    assert response.status_code == 200
    assert response.get_json()['bracket_id'] == 'fresh'
    assert 'fresh' in app.brackets
