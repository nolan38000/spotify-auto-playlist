import os
import re
import time
import random
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# === CONFIGURATION ===
SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = "317izldq6upf2ptacp5b4qklwjd4"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398352899670671544/tHEbGMMuTqeQl6n_tCnQP5NXVjXUEi_qwJ89i0fCpW0cAKQ7NAtTTNyaKAZnNsFN6iwQ"

# === OUTILS ===
def send_log(message):
    try:
        requests.post(WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print("Erreur webhook :", e)

def get_spotify_client(suffix=""):
    cache_path = f".cache-{suffix or USERNAME}"
    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPE,
        username=USERNAME,
        cache_path=cache_path
    )
    return spotipy.Spotify(auth_manager=auth_manager)

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

def get_initial_global_tracks(sp, target_count):
    tracks, offset = [], 0
    while len(tracks) < target_count and offset < 1000:
        batch = search_global_hits(sp, 50, offset)
        for t in batch:
            if t['uri'] not in [track['uri'] for track in tracks]:
                tracks.append(t)
        offset += 50
        time.sleep(0.3)
    return tracks[:target_count]

def update_global_playlist(sp):
    user_id = sp.current_user()['id']
    name = "🌍 Global Hits - Les Incontournables"
    desc = "Une sélection des plus grands hits internationaux, tous styles confondus."
    pid = find_or_create_playlist(sp, user_id, name, desc)

    current_uris = [t['uri'] for t in get_playlist_tracks(sp, pid)]
    INITIAL_COUNT, DAILY_CHANGE = 300, 5

    if len(current_uris) < INITIAL_COUNT:
        new_tracks = get_initial_global_tracks(sp, INITIAL_COUNT)
        uris_to_add = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(pid, uris_to_add[i:i+100])
        send_log(f"📀 Ajout initial de {len(uris_to_add)} titres à la playlist **Global Hits**.")
    else:
        to_remove = random.sample(current_uris, min(DAILY_CHANGE, len(current_uris)))
        sp.playlist_remove_all_occurrences_of_items(pid, to_remove)
        new_tracks = get_initial_global_tracks(sp, DAILY_CHANGE * 3)
        new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris][:DAILY_CHANGE]
        if new_uris:
            sp.playlist_add_items(pid, new_uris)
        send_log(f"🌍 Playlist **Global Hits** mise à jour : {len(new_uris)} ajoutés, {len(to_remove)} supprimés.")

# === FRANÇAIS ===
def search_french_classics(sp, limit=50, offset=0):
    q = 'year:1970-2000 tag:fr OR genre:"chanson française"'
    return sp.search(q=q, type='track', limit=limit, offset=offset)['tracks']['items']

def get_french_tracks(sp, count):
    tracks, offset = [], 0
    while len(tracks) < count and offset < 1000:
        batch = search_french_classics(sp, 50, offset)
        for t in batch:
            if t['uri'] not in [track['uri'] for track in tracks]:
                tracks.append(t)
        offset += 50
        time.sleep(0.3)
    return tracks[:count]

def update_french_playlist(sp):
    user_id = sp.current_user()['id']
    name = "🇫🇷 Classiques Français 70-2000"
    desc = "Les plus grands tubes français des années 70 à 2000."
    pid = find_or_create_playlist(sp, user_id, name, desc)

    current_uris = [t['uri'] for t in get_playlist_tracks(sp, pid)]
    INITIAL_COUNT, DAILY_CHANGE = 100, 5

    if len(current_uris) < INITIAL_COUNT:
        new_tracks = get_french_tracks(sp, INITIAL_COUNT)
        uris_to_add = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(pid, uris_to_add[i:i+100])
        send_log(f"📀 Ajout initial de {len(uris_to_add)} titres à la playlist **Classiques Français**.")
    else:
        to_remove = random.sample(current_uris, min(DAILY_CHANGE, len(current_uris)))
        sp.playlist_remove_all_occurrences_of_items(pid, to_remove)
        new_tracks = get_french_tracks(sp, DAILY_CHANGE * 3)
        new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris][:DAILY_CHANGE]
        if new_uris:
            sp.playlist_add_items(pid, new_uris)
        send_log(f"🇫🇷 Playlist **Classiques Français** mise à jour : {len(new_uris)} ajoutés, {len(to_remove)} supprimés.")
