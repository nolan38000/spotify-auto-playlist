from flask import Flask
import os
import random
import time
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# === CONFIGURATION ===
SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = "317izldq6upf2ptacp5b4qklwjd4"  # Remplace si besoin
CACHE_PATH = f".cache-{USERNAME}"

# === FILTRES ===
ASIAN_CHAR_PATTERN = re.compile(r'[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]')

def contains_asian_chars(text):
    return bool(ASIAN_CHAR_PATTERN.search(text))

# === CLIENT SPOTIFY ===
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=SCOPE,
        username=USERNAME,
        cache_path=CACHE_PATH
    ))

# === UTILS ===
def find_or_create_playlist(sp, user_id, name, description):
    playlists = sp.user_playlists(user_id)
    for p in playlists['items']:
        if p['name'].lower() == name.lower():
            return p['id']
    return sp.user_playlist_create(user_id, name, public=True, description=description)['id']

def get_playlist_tracks(sp, playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id)
    while results:
        tracks.extend([t['track'] for t in results['items'] if t['track']])
        if results['next']:
            results = sp.next(results)
        else:
            break
    return tracks

# === GLOBAL HITS ===
def update_global_hits():
    PLAYLIST_NAME = "🌍 Global Hits - Les Incontournables"
    DESCRIPTION = "Les plus grands hits internationaux, tous styles confondus."
    INITIAL_TRACKS_COUNT = 700
    DAILY_CHANGE_COUNT = 5

    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    playlist_id = find_or_create_playlist(sp, user_id, PLAYLIST_NAME, DESCRIPTION)

    tracks = get_playlist_tracks(sp, playlist_id)
    uris = [t['uri'] for t in tracks]

    def search_hits(limit=50, offset=0):
        results = sp.search(q="year:1980-2025", type='track', limit=limit, offset=offset)
        return [t for t in results['tracks']['items'] if t['popularity'] >= 80 and not contains_asian_chars(t['name'])]

    def get_tracks(count):
        result, offset = [], 0
        while len(result) < count and offset < 1000:
            result.extend(search_hits(limit=50, offset=offset))
            offset += 50
            time.sleep(0.2)
        return result[:count]

    if len(tracks) < INITIAL_TRACKS_COUNT:
        new_tracks = get_tracks(INITIAL_TRACKS_COUNT)
        new_uris = [t['uri'] for t in new_tracks if t['uri'] not in uris]
        for i in range(0, len(new_uris), 100):
            sp.playlist_add_items(playlist_id, new_uris[i:i+100])
        print(f"{len(new_uris)} titres ajoutés à {PLAYLIST_NAME}")
    else:
        to_remove = random.sample(uris, DAILY_CHANGE_COUNT)
        sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)
        new_tracks = get_tracks(DAILY_CHANGE_COUNT * 3)
        new_uris = [t['uri'] for t in new_tracks if t['uri'] not in uris][:DAILY_CHANGE_COUNT]
        if new_uris:
            sp.playlist_add_items(playlist_id, new_uris)
        print(f"{DAILY_CHANGE_COUNT} titres mis à jour dans {PLAYLIST_NAME}")

# === FRENCH CLASSICS ===
def update_french_classics():
    PLAYLIST_NAME = "🇫🇷 Classiques Français 70-2000"
    DESCRIPTION = "Les plus grands tubes français des années 70 à 2000."
    TRACK_COUNT = 200

    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    playlist_id = find_or_create_playlist(sp, user_id, PLAYLIST_NAME, DESCRIPTION)

    tracks = get_playlist_tracks(sp, playlist_id)
    uris = [t['uri'] for t in tracks]

    def search_french():
        query = "genre:chanson year:1970-2000 tag:fr"
        results = sp.search(q=query, type='track', limit=50)
        return [t for t in results['tracks']['items'] if t['popularity'] >= 50]

    new_tracks = search_french()
    new_uris = [t['uri'] for t in new_tracks if t['uri'] not in uris]

    if len(tracks) < TRACK_COUNT:
        to_add = new_uris[:TRACK_COUNT - len(tracks)]
        sp.playlist_add_items(playlist_id, to_add)
        print(f"{len(to_add)} titres ajoutés à {PLAYLIST_NAME}")
    else:
        to_remove = random.sample(uris, 10)
        sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)
        to_add = new_uris[:10]
        sp.playlist_add_items(playlist_id, to_add)
        print("Playlist française mise à jour.")

# === FLASK APP ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Serveur actif. Visite /run pour Global Hits, ou /run-french pour la playlist française."

@app.route('/run')
def run_global():
    try:
        update_global_hits()
        return "🌍 Playlist internationale mise à jour !"
    except Exception as e:
        return f"Erreur : {e}", 500

@app.route('/run-french')
def run_french():
    try:
        update_french_classics()
        return "🇫🇷 Playlist française mise à jour !"
    except Exception as e:
        return f"Erreur : {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
