import os
import re
import time
import random
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPE = "playlist-modify-private playlist-modify-public playlist-read-private"
USERNAME = "317izldq6upf2ptacp5b4qklwjd4"
WEBHOOK_URL = "https://discord.com/api/webhooks/1398352899670671544/tHEbGMMuTqeQl6n_tCnQP5NXVjXUEi_qwJ89i0fCpW0cAKQ7NAtTTNyaKAZnNsFN6iwQ"

def send_log(message):
    try:
        requests.post(WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print("Erreur webhook :", e)

def get_spotify_client():
    cache_path = f".cache-{USERNAME}"
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

# ========== GLOBAL HITS (titres avec >500M streams par sélection manuelle) ==========

KNOWN_HITS = [
    "Blinding Lights", "Shape of You", "Dance Monkey", "Stay", "Uptown Funk",
    "Sunflower", "Rockstar", "One Dance", "Perfect", "Someone You Loved",
    "Senorita", "Bad Guy", "Believer", "Levitating", "Shallow", "Closer"
]

def search_super_hits(sp):
    tracks = []
    for name in KNOWN_HITS:
        results = sp.search(q=f'track:"{name}"', type='track', limit=3)
        for t in results['tracks']['items']:
            if t['popularity'] >= 90:
                tracks.append(t)
        time.sleep(0.2)
    return tracks

def update_global_playlist(sp):
    user_id = sp.current_user()['id']
    name = "🌍 Global Hits - Les Incontournables"
    desc = "Une sélection des titres les plus streamés dans le monde."
    pid = find_or_create_playlist(sp, user_id, name, desc)

    current_uris = [t['uri'] for t in get_playlist_tracks(sp, pid)]
    INITIAL_COUNT, DAILY_CHANGE = 100, 5

    if len(current_uris) < INITIAL_COUNT:
        new_tracks = search_super_hits(sp)
        uris_to_add = [t['uri'] for t in new_tracks if t['uri'] not in current_uris]
        for i in range(0, len(uris_to_add), 100):
            sp.playlist_add_items(pid, uris_to_add[i:i+100])
        send_log(f"📀 Ajout initial de {len(uris_to_add)} titres à la playlist **Global Hits**.")
    else:
        to_remove = random.sample(current_uris, min(DAILY_CHANGE, len(current_uris)))
        sp.playlist_remove_all_occurrences_of_items(pid, to_remove)
        new_tracks = search_super_hits(sp)
        new_uris = [t['uri'] for t in new_tracks if t['uri'] not in current_uris][:DAILY_CHANGE]
        if new_uris:
            for i in range(0, len(new_uris), 100):
                sp.playlist_add_items(pid, new_uris[i:i+100])
        send_log(f"🌍 Playlist **Global Hits** mise à jour : {len(new_uris)} ajoutés, {len(to_remove)} supprimés.")

# ========== FRANÇAIS VARIÉTÉS CONNUES ==========

FRENCH_QUERY = 'artist:"Francis Cabrel" OR artist:"Mylène Farmer" OR artist:"Indochine" OR artist:"Johnny Hallyday" OR artist:"Michel Sardou" OR artist:"Claude François" OR artist:"Daniel Balavoine" OR artist:"Renaud" OR artist:"Jean-Jacques Goldman"'

def search_french_tracks(sp, limit=50, offset=0):
    return sp.search(q=FRENCH_QUERY, type='track', limit=limit, offset=offset)['tracks']['items']

def get_french_tracks(sp, count):
    tracks, offset = [], 0
    while len(tracks) < count and offset < 1000:
        batch = search_french_tracks(sp, 50, offset)
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
            for i in range(0, len(new_uris), 100):
                sp.playlist_add_items(pid, new_uris[i:i+100])
        send_log(f"🇫🇷 Playlist **Classiques Français** mise à jour : {len(new_uris)} ajoutés, {len(to_remove)} supprimés.")
