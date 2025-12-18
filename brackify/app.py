from typing import Any, Dict, Optional, Tuple

from datetime import datetime, timedelta, timezone
import os
import secrets
from flask import Flask, jsonify, render_template, request, url_for
from brackify.brackets import AllowedBracketSizes, build_seed_list, chunk_matches
from brackify.spotify_client import get_spotify_client, fetch_playlist_tracks
from brackify.store import BracketStore, create_store_from_env

EXPIRATION_HOURS = 72
EXPIRATION_DELTA = timedelta(hours = EXPIRATION_HOURS)


def now() -> datetime:
    return datetime.now(timezone.utc)


def remaining_ttl_seconds(created_at: datetime, expiration_delta: timedelta) -> int:
    elapsed = now() - created_at
    remaining = expiration_delta - elapsed
    return max(0, int(remaining.total_seconds()))


def bracket_signature(playlist: str, size: int, order: str, bracket_name: str) -> Tuple[str, int, str, str]:
    return (
        playlist.strip(),
        size,
        order.strip().lower(),
        bracket_name.strip(),
    )


def signature_key(signature: Tuple[str, int, str, str]) -> str:
    playlist, size, order, bracket_name = signature
    return '|'.join([playlist, str(size), order, bracket_name])


def create_app(store: Optional[BracketStore] = None, expiration_hours: Optional[int] = None) -> Flask:
    app = Flask(__name__)

    configured_hours = expiration_hours or int(os.getenv('BRACKET_EXPIRATION_HOURS', EXPIRATION_HOURS))
    app.expiration_delta = timedelta(hours = configured_hours)  # type: ignore[attr-defined]
    app.bracket_ttl_seconds = int(app.expiration_delta.total_seconds())  # type: ignore[attr-defined]

    app.bracket_store = store or create_store_from_env()  # type: ignore[attr-defined]
    app.bracket_index: Dict[Tuple[str, int, str, str], str] = {}  # type: ignore[attr-defined]

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/bracket/<bracket_id>')
    def view_bracket(bracket_id: str):
        return render_template('bracket.html', bracket_id = bracket_id)

    @app.post('/api/bracket')
    def api_bracket():
        payload = request.get_json(silent = True) or {}

        playlist = (payload.get('playlist') or '').strip()
        order = (payload.get('order') or 'playlist').strip().lower()
        bracket_name = (payload.get('bracket_name') or '').strip()
        size = payload.get('size')

        if not playlist:
            return jsonify({'error': 'playlist is required'}), 400

        if not bracket_name:
            return jsonify({'error': 'bracket_name is required'}), 400

        try:
            size_int = int(size)
        except (TypeError, ValueError):
            return jsonify({'error': f'size must be one of {AllowedBracketSizes}'}), 400

        signature = bracket_signature(playlist, size_int, order, bracket_name)
        existing_id = app.bracket_index.get(signature)  # type: ignore[attr-defined]
        if not existing_id:
            mapping = app.bracket_store.get(signature_key(signature))  # type: ignore[attr-defined]
            if mapping:
                existing_id = mapping.get('bracket_id')
                if existing_id:
                    app.bracket_index[signature] = existing_id  # type: ignore[attr-defined]

        if existing_id:
            existing_bracket = app.bracket_store.get(existing_id)  # type: ignore[attr-defined]

            if existing_bracket:
                refreshed_at = now()
                existing_bracket['created_at'] = refreshed_at.isoformat()
                ttl_seconds = remaining_ttl_seconds(refreshed_at, app.expiration_delta)  # type: ignore[attr-defined]
                app.bracket_store.save(existing_id, existing_bracket, ttl_seconds)  # type: ignore[attr-defined]
                app.bracket_store.save(signature_key(signature), {'bracket_id': existing_id}, ttl_seconds)  # type: ignore[attr-defined]
                return jsonify(existing_bracket)

            app.bracket_index.pop(signature, None)  # type: ignore[attr-defined]

        try:
            sp = get_spotify_client()
            tracks = fetch_playlist_tracks(playlist, sp)

            if len(tracks) < size_int:
                raise ValueError(f'This playlist does not have enough tracks for a {size_int}-song bracket.')

            seeds = build_seed_list(tracks, size_int, order = order)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({'error': str(exc)}), 500

        created_at = now()
        bracket_id = secrets.token_urlsafe(8)

        bracket_payload: Dict[str, Any] = {
            'size': size_int,
            'order': order,
            'seed_count': len(seeds),
            'seeds': seeds,
            'matches': chunk_matches(seeds),
            'total_tracks': len(tracks),
            'bracket_name': bracket_name,
            'playlist': playlist,
            'bracket_id': bracket_id,
            'share_url': url_for('view_bracket', bracket_id = bracket_id, _external = True),
            'created_at': created_at.isoformat(),
        }

        ttl_seconds = remaining_ttl_seconds(created_at, app.expiration_delta)  # type: ignore[attr-defined]
        app.bracket_store.save(bracket_id, bracket_payload, ttl_seconds)  # type: ignore[attr-defined]
        app.bracket_store.save(signature_key(signature), {'bracket_id': bracket_id}, ttl_seconds)  # type: ignore[attr-defined]
        app.bracket_index[signature] = bracket_id  # type: ignore[attr-defined]

        return jsonify(bracket_payload)

    @app.get('/api/bracket/<bracket_id>')
    def get_bracket(bracket_id: str):
        bracket = app.bracket_store.get(bracket_id)  # type: ignore[attr-defined]

        if not bracket:
            return jsonify({'error': 'Bracket not found or expired'}), 404

        return jsonify(bracket)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 8000)
