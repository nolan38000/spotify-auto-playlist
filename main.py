from flask import Flask
import os
import random
import time
import re
import sys
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# === CONFIGURATION ===
SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = "TON_USERNAME_SPOTIFY"  # ⚠️ Remplace par ton username réel
INITIAL_TRACKS_COUNT = 700
DAILY_CHANGE_COUNT = 5

# === PATTERN D’EXCLUSION ASIATIQUE ===
ASIAN_CHAR_PATTERN = re.compile(r'[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]')
def contains_asian_chars(text):
    return bool(ASIAN_CHAR_PATTERN.search(text))

# === CLIENT SPOTIPY ===
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=SCOPE,
        username=USERNAME,
        cache_path=f".cache-{USERNAME}"
    ))

# === UTILS ===
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

# === GLOBAL HITS ===
def search_global_hits(sp, limit=50, offset=0):
    results = sp.search(q='year:1980-2025', type='track', limit=limit, offset=offset)
    return [t for t in results['tracks']['items'] if t['popularity'] >= 90 and not contains_asian_chars(t['name'])]

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

def update_global_playlist():
    print("➡️ Mise à jour de la playlist internationale", file=sys.stderr)
    sp = get_spotify_client()
    user_id = sp.current_user()['id']

    name = "🌍 Global Hits - Les Incontournables"
    desc = "Une sélection des plus grands hits internationaux, tous styles confondus."
    playlist_id = find_or_create_playlist(sp, user_id, name, desc)

    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks]

    if len(current_uris) < INITIAL_TRACKS_COUNT:
        print("🔼 Remplissage initial...")
        new_tracks = get_initial_tracks(sp, INITIAL_TRACKS_COUNT)
    else:
        print("🔁 Mise à jour quotidienne...")
        sp.playlist_remove_all_occurrences_of_items(playlist_id, random.sample(current_uris, DAILY_CHANGE_COUNT))
        new_tracks = get_initial_tracks(sp, DAILY_CHANGE_COUNT * 3)

    new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris][:DAILY_CHANGE_COUNT]
    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)
        print(f"✅ {len(new_uris)} titres ajoutés")
    else:
        print("⚠️ Aucun nouveau titre à ajouter")

# === PLAYLIST FRANÇAISE ===
def update_french_classics_playlist():
    print("➡️ Mise à jour de la playlist française", file=sys.stderr)
    sp = get_spotify_client()
    user_id = sp.current_user()['id']

    name = "🇫🇷 Classiques Français 70-2000"
    desc = "Les plus grands tubes français des années 70 à 2000."
    playlist_id = find_or_create_playlist(sp, user_id, name, desc)

    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks]

    if current_uris:
        to_remove = random.sample(current_uris, min(10, len(current_uris)))
        sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)
        print(f"❌ {len(to_remove)} titres supprimés")

    queries = [
        "Claude François", "France Gall", "Michel Sardou", "Johnny Hallyday",
        "Jean-Jacques Goldman", "Balavoine", "Michel Berger", "Renaud",
        "Patrick Bruel", "Francis Cabrel", "Mylène Farmer", "Indochine"
    ]

    new_uris = []
    for artist in queries:
        results = sp.search(q=f'{artist} year:1970-2000', type='track', limit=10)
        for t in results['tracks']['items']:
            if t['uri'] not in current_uris and t['uri'] not in new_uris:
                new_uris.append(t['uri'])
            if len(new_uris) >= 10:
                break
        if len(new_uris) >= 10:
            break

    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)
        print(f"✅ {len(new_uris)} titres ajoutés")
    else:
        print("⚠️ Aucun titre trouvé pour ajout", file=sys.stderr)

# === FLASK APP ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Serveur en ligne. Utilise /run, /run-french ou /run-all"

@app.route('/run')
def run_global():
    try:
        update_global_playlist()
        return "🎵 Playlist internationale mise à jour"
    except Exception as e:
        return f"❌ Erreur : {e}", 500

@app.route('/run-french')
def run_french():
    try:
        update_french_classics_playlist()
        return "🇫🇷 Playlist française mise à jour"
    except Exception as e:
        return f"❌ Erreur : {e}", 500

@app.route('/run-all')
def run_both():
    try:
        update_global_playlist()
        update_french_classics_playlist()
        return "✅ Les deux playlists ont été mises à jour"
    except Exception as e:
        return f"❌ Erreur : {e}", 500

if __name__ == "__main__" and os.environ.get("RENDER") is None:
    app.run(host="0.0.0.0", port=10000)

