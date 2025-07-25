from flask import Flask
from spotify_utils import get_spotify_client, update_global_playlist

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Serveur actif. /run-global = global playlist"

@app.route('/run-global')
def run_global():
    try:
        sp = get_spotify_client("global")
        update_global_playlist(sp)
        return "🌍 Playlist Global Hits mise à jour !"
    except Exception as e:
        return f"❌ Erreur Global Hits : {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
