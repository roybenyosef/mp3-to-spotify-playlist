import argparse
import math
import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def search_track(sp: spotipy.Spotify, track_name: str) -> str:
    results = sp.search(q=track_name, type="track", limit=1)
    if results["tracks"]["items"]:
        return results["tracks"]["items"][0]["id"]
    else:
        return None


def playlist_tracks_file(playlist_name: str) -> str:
    return f"{playlist_name}-tracks_to_add.txt"


def playlist_unmatched_file(playlist_name: str) -> str:
    return f"{playlist_name}-unmatched_tracks.txt"


def create_tracks_list(
    sp: spotipy.Spotify,
    music_folder: str,
    tracks_file: str,
    unmatched_file: str,
) -> Tuple[List, List]:
    tracks_to_add = []
    unmatched_tracks = []

    tracks_file_found = os.path.isfile(tracks_file)
    unmatched_file_found = os.path.isfile(unmatched_file)

    if tracks_file_found and unmatched_file_found:
        return read_tracks_from_cache(tracks_file, unmatched_file)

    music_extensions = "mp3 wav"
    for path in Path(music_folder).rglob(f"*.[{music_extensions}]*"):
        file = path.name
        track_id = search_track(sp, file[:-4])  # Remove extension from the file name
        if track_id:
            print(f"Found track for: {file}")
            tracks_to_add.append(track_id)
        else:
            print(f"Track : {file}, unmatched")
            unmatched_tracks.append(file)

    return tracks_to_add, unmatched_tracks


def read_tracks_from_cache(tracks_file: str, unmatched_file: str):
    print("Reading tracks from cache files")

    with open(tracks_file) as f:
        tracks_to_add = f.read().splitlines()

    with open(unmatched_file) as f:
        unmatched_tracks = f.read().splitlines()

    return tracks_to_add, unmatched_tracks


def write_list_to_file(unmatched_tracks: List[str], filename: str):
    with open(filename, "w") as f:
        for track in unmatched_tracks:
            f.write(f"{track}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--music-folder")
    parser.add_argument("-p", "--playlist-name")
    parser.add_argument("-d", "--dry-run", action="store_true")
    args = parser.parse_args()
    playlist_name = args.playlist_name

    tracks_file = playlist_tracks_file(playlist_name)
    unmatched_file = playlist_unmatched_file(playlist_name)

    if args.dry_run:
        print("Dry run, skipping mutating operations")

    load_dotenv()
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    redirect_uri = os.environ["SPOTIFY_REDIRECT_URI"]
    scope = "playlist-modify-public"

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
        )
    )
    user = sp.current_user()

    tracks_to_add, unmatched_tracks = create_tracks_list(
        sp, args.music_folder, tracks_file, unmatched_file
    )
    print(f"Found {len(unmatched_tracks)} unmatched tracks")

    write_list_to_file(tracks_to_add, tracks_file)
    write_list_to_file(unmatched_tracks, unmatched_file)

    print(f"Creating playlist: {playlist_name}")

    if not args.dry_run:
        playlist = sp.user_playlist_create(user["id"], playlist_name)

    print(f"Found {len(tracks_to_add)} tracks for playlist: {playlist_name}")

    for i in range(0, math.ceil(len(tracks_to_add) / 100)):
        tracks_batch = tracks_to_add[i * 100 : i * 100 + 100]
        print(f"Adding {len(tracks_batch)} to playlist")
        if not args.dry_run:
            sp.playlist_add_items(playlist["id"], tracks_batch)

    if not args.dry_run:
        os.remove(tracks_file)
        os.remove(unmatched_file)


if __name__ == "__main__":
    main()
