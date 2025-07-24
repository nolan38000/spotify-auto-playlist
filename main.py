from flask import Flask, request
import os
import random
import time
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# === CONFIGURATION ===
SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = os.getenv("317izldq6upf2ptacp5b4qklwjd4")
PLAYLIST_NAME = "🌍 Global Hits - Les Incontournables"
PLAYLIST_DESCRIPTION = "Une sélection des plus grands hits internationaux, tous styles confondus."
INITIAL_TRACKS_COUNT = 700
DAILY_CHANGE_COUNT = 5

ASIAN_CHAR_PATTERN = re.compile(r'[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]')

def contains_asian_chars(text):
    return bool(ASIAN_CHAR_PATTERN.search(text))

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPE,
        username=USERNAME
    ))

def find_or_create_playlist(sp, user_id, name, description):
    playlists = sp.user_playlists(user_id)
    for p in playlists['items']:
        if p['name'] == name:
            return p['id']
    playlist = sp.user_playlist_create(user_id, name, public=True, description=description)
    return playlist['id']

def get_playlist_tracks(sp, playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id)
    tracks.extend(results['items'])
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return [t['track'] for t in tracks if t['track']]

def search_global_hits(sp, limit=50, offset=0):
    results = sp.search(q='year:1980-2025', type='track', limit=limit, offset=offset)
    return [t for t in results['tracks']['items'] if t['popularity'] >= 80 and not contains_asian_chars(t['name'])]

def get_initial_tracks(sp, target_count):
    tracks = []
    offset = 0
    batch_size = 50
    max_offset = 1000
    while len(tracks) < target_count and offset < max_offset:
        batch = search_global_hits(sp, limit=batch_size, offset=offset)
        for t in batch:
            if t not in tracks:
                tracks.append(t)
            if len(tracks) >= target_count:
                break
        offset += batch_size
        time.sleep(0.5)
    return tracks[:target_count]

def update_playlist():
    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    playlist_id = find_or_create_playlist(sp, user_id, PLAYLIST_NAME, PLAYLIST_DESCRIPTION)
    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks]

    if len(current_tracks) < INITIAL_TRACKS_COUNT:
        print(f"Playlist courte ({len(current_tracks)} titres). Ajout initial...")
        initial_tracks = get_initial_tracks(sp, INITIAL_TRACKS_COUNT)
        uris_to_add = [t['uri'] for t in initial_tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(playlist_id, uris_to_add[i:i+100])
        print(f"{len(uris_to_add)} titres ajoutés.")
        return

    print(f"Playlist existante ({len(current_tracks)} titres). Mise à jour...")
    to_remove = random.sample(current_uris, DAILY_CHANGE_COUNT)
    sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)
    print(f"Supprimé {len(to_remove)} titres.")

    new_tracks = get_initial_tracks(sp, DAILY_CHANGE_COUNT * 3)
    new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
    new_uris = new_uris[:DAILY_CHANGE_COUNT]

    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)
        print(f"Ajouté {len(new_uris)} titres.")

# === Flask App ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Serveur en ligne ! Va sur /run pour mettre à jour la playlist."

@app.route('/run')
def run_script():
    update_playlist()
    return "🎵 Playlist mise à jour avec succès !"

@app.route('/callback')
def callback():
    code = request.args.get('code')
    return f"Code reçu : {code} - Tu peux fermer cette page."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
