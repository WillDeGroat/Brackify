from typing import Any, Dict, Optional

from datetime import datetime, timedelta, timezone
import secrets
from flask import Flask, jsonify, render_template, request, url_for
from brackify.brackets import AllowedBracketSizes, build_seed_list, chunk_matches
from brackify.spotify_client import get_spotify_client, fetch_playlist_tracks

EXPIRATION_HOURS = 72
EXPIRATION_DELTA = timedelta(hours = EXPIRATION_HOURS)


def create_app() -> Flask:
    app = Flask(__name__)
    brackets: Dict[str, Dict[str, Any]] = {}

    def now() -> datetime:
        return datetime.now(timezone.utc)

    def parse_timestamp(value: Any) -> Optional[datetime]:
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def is_expired(created_at: Any) -> bool:
        created_dt = parse_timestamp(created_at)
        if not created_dt:
            return False

        return now() - created_dt > EXPIRATION_DELTA

    def cleanup_expired_brackets():
        expired_ids = [bid for bid, payload in brackets.items() if is_expired(payload.get('created_at'))]
        for bid in expired_ids:
            brackets.pop(bid, None)

    app.brackets = brackets  # type: ignore[attr-defined]
    app.is_expired = is_expired  # type: ignore[attr-defined]
    app.cleanup_expired_brackets = cleanup_expired_brackets  # type: ignore[attr-defined]

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/bracket/<bracket_id>')
    def view_bracket(bracket_id: str):
        return render_template('bracket.html', bracket_id = bracket_id)

    @app.post('/api/bracket')
    def api_bracket():
        cleanup_expired_brackets()
        payload = request.get_json(silent = True) or {}

        playlist = (payload.get('playlist') or '').strip()
        order = (payload.get('order') or 'playlist').strip().lower()
        size = payload.get('size')

        if not playlist:
            return jsonify({'error': 'playlist is required'}), 400

        try:
            size_int = int(size)
        except (TypeError, ValueError):
            return jsonify({'error': f'size must be one of {AllowedBracketSizes}'}), 400

        try:
            sp = get_spotify_client()
            tracks = fetch_playlist_tracks(playlist, sp)

            if len(tracks) < size_int:
                raise ValueError(f'Not enough tracks for a {size_int}-song bracket. This playlist has {len(tracks)} track(s).')

            seeds = build_seed_list(tracks, size_int, order = order)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({'error': str(exc)}), 500

        bracket_payload = {
            'size': size_int,
            'order': order,
            'seed_count': len(seeds),
            'seeds': seeds,
            'matches': chunk_matches(seeds),
            'total_tracks': len(tracks),
            'created_at': now().isoformat(),
        }

        bracket_id = secrets.token_urlsafe(8)
        bracket_payload['bracket_id'] = bracket_id
        bracket_payload['share_url'] = url_for('view_bracket', bracket_id = bracket_id, _external = True)

        brackets[bracket_id] = bracket_payload

        return jsonify(bracket_payload)

    @app.get('/api/bracket/<bracket_id>')
    def get_bracket(bracket_id: str):
        cleanup_expired_brackets()
        bracket = brackets.get(bracket_id)

        if not bracket:
            return jsonify({'error': 'Bracket not found'}), 404

        if is_expired(bracket.get('created_at')):
            brackets.pop(bracket_id, None)
            return jsonify({'error': 'Bracket expired'}), 404

        return jsonify(bracket)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 8000)
