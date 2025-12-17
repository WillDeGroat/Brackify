from typing import Any, Dict
import secrets
from flask import Flask, jsonify, render_template, request, url_for
from brackify.brackets import AllowedBracketSizes, build_seed_list, chunk_matches
from brackify.spotify_client import get_spotify_client, fetch_playlist_tracks


def create_app() -> Flask:
    app = Flask(__name__)
    brackets: Dict[str, Dict[str, Any]] = {}

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
        }

        bracket_id = secrets.token_urlsafe(8)
        bracket_payload['bracket_id'] = bracket_id
        bracket_payload['share_url'] = url_for('view_bracket', bracket_id = bracket_id, _external = True)

        brackets[bracket_id] = bracket_payload

        return jsonify(bracket_payload)

    @app.get('/api/bracket/<bracket_id>')
    def get_bracket(bracket_id: str):
        bracket = brackets.get(bracket_id)

        if not bracket:
            return jsonify({'error': 'Bracket not found'}), 404

        return jsonify(bracket)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 8000)
