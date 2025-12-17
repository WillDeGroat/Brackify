import argparse
from brackify.spotify_client import get_spotify_client, fetch_playlist_tracks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description = 'Fetch tracks from a Spotify playlist.')
    parser.add_argument('playlist', help = 'Spotify playlist URL or ID.')
    parser.add_argument('--limit', type = int, default = 100, help = 'Page size for playlist fetches (default: 100).')

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sp = get_spotify_client()
    tracks = fetch_playlist_tracks(args.playlist, sp, limit = args.limit)

    print(f'Found {len(tracks)} tracks')
    for row in tracks:
        print(f"{row['song_name']} | {row['artists']} ({row['album_name']})")


if __name__ == '__main__':
    main()
