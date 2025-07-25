from spotify_utils import get_spotify_client, update_french_playlist

def run():
    try:
        sp = get_spotify_client("fr")
        update_french_playlist(sp)
        print("✅ Playlist Classiques Français mise à jour !")
    except Exception as e:
        print(f"❌ Erreur Classiques Français : {e}")

if __name__ == "__main__":
    run()
