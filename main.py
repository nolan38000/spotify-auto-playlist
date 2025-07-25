from flask import Flask 
import os
import random
import time
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests

# === CONFIGURATION ===
SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = "317izldq6upf2ptacp5b4qklwjd4"
CACHE_PATH = f".cache-{USERNAME}"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398352899670671544/tHEbGMMuTqeQl6n_tCnQP5NXVjXUEi_qwJ89i0fCpW0cAKQ7NAtTTNyaKAZnNsFN6iwQ"

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

def send_log_to_discord(message):
    try:
        requests.post(WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print(f"❌ Erreur envoi webhook : {e}")

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
            if t['uri'] not in [track['uri'] for track in tracks]:
                tracks.append(t)
            if len(tracks) >= target_count:
                break
        offset += batch_size
        time.sleep(0.3)
    return tracks[:target_count]

def update_global_playlist(sp):
    user_id = sp.current_user()['id']
    playlist_name = "🌍 Global Hits - Les Incontournables"
    playlist_description = "Une sélection des plus grands hits internationaux, tous styles confondus."
    playlist_id = find_or_create_playlist(sp, user_id, playlist_name, playlist_description)

    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks if t]

    INITIAL_TRACKS_COUNT = 300
    DAILY_CHANGE_COUNT = 5

    if len(current_uris) < INITIAL_TRACKS_COUNT:
        print("💽 Ajout initial à la playlist internationale...")
        initial_tracks = get_initial_tracks(sp, INITIAL_TRACKS_COUNT)
        uris_to_add = [t['uri'] for t in initial_tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(playlist_id, uris_to_add[i:i+100])
        send_log_to_discord(f"📀 Ajout initial de {len(uris_to_add)} titres à la playlist **Global Hits**.")

    print("🔁 Mise à jour de la playlist internationale...")
    to_remove = random.sample(current_uris, min(DAILY_CHANGE_COUNT, len(current_uris)))
    sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)

    new_tracks = get_initial_tracks(sp, DAILY_CHANGE_COUNT * 3)
    new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
    new_uris = new_uris[:DAILY_CHANGE_COUNT]

    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)
        send_log_to_discord(f"🌍 Playlist **Global Hits** mise à jour : {len(new_uris)} titres ajoutés, {len(to_remove)} supprimés.")
    else:
        send_log_to_discord(f"⚠️ Playlist **Global Hits** mise à jour : 0 titres ajoutés, {len(to_remove)} supprimés. Aucun titre neuf trouvé.")

# === CLASSIQUES FRANÇAIS 70-2000 ===
def search_french_classics(sp, limit=50, offset=0):
    query = 'year:1970-2000 tag:fr OR genre:"chanson française"'
    results = sp.search(q=query, type='track', limit=limit, offset=offset)
    return results['tracks']['items']

def get_french_tracks(sp, count):
    tracks = []
    offset = 0
    while len(tracks) < count and offset < 1000:
        batch = search_french_classics(sp, limit=50, offset=offset)
        for t in batch:
            if t['uri'] not in [track['uri'] for track in tracks]:
                tracks.append(t)
            if len(tracks) >= count:
                break
        offset += 50
        time.sleep(0.3)
    return tracks[:count]

def update_french_playlist(sp):
    user_id = sp.current_user()['id']
    playlist_name = "🇫🇷 Classiques Français 70-2000"
    playlist_description = "Les plus grands tubes français des années 70 à 2000."
    playlist_id = find_or_create_playlist(sp, user_id, playlist_name, playlist_description)

    current_tracks = get_playlist_tracks(sp, playlist_id)
    current_uris = [t['uri'] for t in current_tracks if t]

    INITIAL_TRACKS_COUNT = 100
    DAILY_CHANGE_COUNT = 5

    if len(current_uris) < INITIAL_TRACKS_COUNT:
        print("💽 Ajout initial à la playlist française...")
        tracks = get_french_tracks(sp, INITIAL_TRACKS_COUNT)
        uris_to_add = [t['uri'] for t in tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(playlist_id, uris_to_add[i:i+100])
        send_log_to_discord(f"📀 Ajout initial de {len(uris_to_add)} titres à la playlist **Classiques Français**.")

    print("🔁 Mise à jour de la playlist française...")
    to_remove = random.sample(current_uris, min(DAILY_CHANGE_COUNT, len(current_uris)))
    sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)

    new_tracks = get_french_tracks(sp, DAILY_CHANGE_COUNT * 3)
    new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
    new_uris = new_uris[:DAILY_CHANGE_COUNT]

    if new_uris:
        sp.playlist_add_items(playlist_id, new_uris)
        send_log_to_discord(f"🇫🇷 Playlist **Classiques Français** mise à jour : {len(new_uris)} titres ajoutés, {len(to_remove)} supprimés.")
    else:
        send_log_to_discord(f"⚠️ Playlist **Classiques Français** mise à jour : 0 titres ajoutés, {len(to_remove)} supprimés. Aucun titre neuf trouvé.")

# === FLASK ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Serveur actif. Accède à /run-all pour lancer les deux playlists."

@app.route('/run-global')
def run_global():
    try:
        sp = get_spotify_client()
        update_global_playlist(sp)
        return "🌍 Playlist Global Hits mise à jour !"
    except Exception as e:
        send_log_to_discord(f"❌ Erreur Global Hits : {e}")
        return f"❌ Erreur (global) : {e}", 500

@app.route('/run-french')
def run_french():
    try:
        sp = get_spotify_client()
        update_french_playlist(sp)
        return "🇫🇷 Playlist Classiques Français mise à jour !"
    except Exception as e:
        send_log_to_discord(f"❌ Erreur Classiques Français : {e}")
        return f"❌ Erreur (français) : {e}", 500

@app.route('/run-all')
def run_all():
    try:
        sp = get_spotify_client()
        update_global_playlist(sp)
        update_french_playlist(sp)
        return "✅ Les deux playlists ont été mises à jour !"
    except Exception as e:
        send_log_to_discord(f"❌ Erreur globale (run-all) : {e}")
        return f"❌ Erreur globale : {e}", 500

@app.route('/callback')
def callback():
    return "🔁 Autorisation reçue. Tu peux fermer cette page."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
