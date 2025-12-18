# Brackify

Brackify converts Spotify playlists into interactive brackets. This repository now includes a Flask web app that turns a playlist into a clickable bracket, plus utilities to fetch playlist tracks using the Spotify Web API.

## Setup

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Create a `.env` file with your Spotify credentials:

   ```bash
   SPOTIFY_CLIENT_ID=<your_client_id>
   SPOTIFY_CLIENT_SECRET=<your_client_secret>
   ```

## Run the web app

Start the Flask server:

```bash
FLASK_APP=brackify.app flask run --host=0.0.0.0 --port=8000
```

Open `http://localhost:8000` and paste a Spotify playlist URL or ID. Choose the bracket order (playlist or randomized) and the desired size (8, 16, or 32). Click songs to advance them through the bracket. Empty slots remain empty and cannot advance when a matchup lacks two songs.

## Storage configuration

Brackets are stored in a TTL-aware backend. By default the app uses an in-memory store with a 72-hour expiration window. To persist brackets across restarts or enable automatic expiry outside the app process, configure Redis:

```bash
export BRACKET_STORE_BACKEND=redis
export BRACKET_REDIS_URL=redis://localhost:6379/0
# Optional: override expiry hours
export BRACKET_EXPIRATION_HOURS=72
```

If Redis is unavailable or misconfigured the app will fall back to the in-memory store.

## Fetch playlist tracks

Use the CLI helper to pull tracks from a playlist URL or ID:

```bash
python -m brackify.scripts.fetch_playlist "https://open.spotify.com/playlist/..."
```

The output includes the song name, artists, and album for each track.
