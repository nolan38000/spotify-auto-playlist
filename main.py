from flask import Flask
import os
import random
import time
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# === CONFIGURATION ===
SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = "317izldq6upf2ptacp5b4qklwjd4"  # Ton vrai username Spotify
CACHE_PATH = f".cache-{USERNAME}"

# === UTILITAIRE SPOTIFY ===
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPE,
        username=USERNAME,
        cache_path=CACHE_PATH
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

# === GLOBAL HITS ===
ASIAN_CHAR_PATTERN = re.compile(r'[\u3040-\u30FF\u3400-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]')
def contains_asian_chars(text):
    return bool(ASIAN_CHAR_PATTERN.search(text))

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
    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    playlist_name = "🌍 Global Hits - Les Incontournables"
    playlist_description = "Une sélection des plus grands hits internationaux, tous styles confondus."
    playlist_id = find_or_create_playlist(sp, user_id, playlist_name, playlist_description)

    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks]
    DAILY_CHANGE_COUNT = 5
    INITIAL_TRACKS_COUNT = 700

    if len(current_tracks) < INITIAL_TRACKS_COUNT:
        initial_tracks = get_initial_tracks(sp, INITIAL_TRACKS_COUNT)
        uris_to_add = [t['uri'] for t in initial_tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(playlist_id, uris_to_add[i:i+100])
        return

    to_remove = random.sample(current_uris, DAILY_CHANGE_COUNT)
    sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)
    new_tracks = get_initial_tracks(sp, DAILY_CHANGE_COUNT * 3)
    new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
    new_uris = new_uris[:DAILY_CHANGE_COUNT]
    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)

# === PLAYLIST FRANÇAISE 70-2000 ===
def update_french_playlist():
    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    playlist_name = "🇫🇷 Classiques Français 70-2000"
    playlist_description = "Les plus grands tubes français des années 70 à 2000."
    playlist_id = find_or_create_playlist(sp, user_id, playlist_name, playlist_description)

    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks]

    # Supprimer 10 morceaux aléatoires s’il y en a assez
    if len(current_uris) >= 10:
        to_remove = random.sample(current_uris, 10)
        sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)

    # Ajouter des nouveautés
    query = 'year:1970-2000 tag:fr OR genre:"chanson française"'
    results = sp.search(q=query, type='track', limit=50)
    new_tracks = [t for t in results['tracks']['items'] if t['uri'] not in current_uris]
    new_uris = [t['uri'] for t in new_tracks[:10]]

    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)

# === FLASK ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Serveur actif. Accède à /run-all pour lancer les deux playlists."

@app.route('/run-global')
def run_global():
    try:
        update_global_playlist()
        return "🌍 Playlist Global Hits mise à jour !"
    except Exception as e:
        return f"❌ Erreur : {e}", 500

@app.route('/run-french')
def run_french():
    try:
        update_french_playlist()
        return "🇫🇷 Playlist Classiques Français mise à jour !"
    except Exception as e:
        return f"❌ Erreur : {e}", 500

@app.route('/run-all')
def run_all():
    try:
        update_global_playlist()
        update_french_playlist()
        return "✅ Les deux playlists ont été mises à jour !"
    except Exception as e:
        return f"❌ Erreur : {e}", 500

@app.route('/callback')
def callback():
    return "🔁 Autorisation reçue. Tu peux fermer cette page."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
