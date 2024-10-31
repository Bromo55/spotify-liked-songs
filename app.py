import os
import json
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Cargar las variables de entorno desde un archivo .env
load_dotenv()

# Configuración de autenticación
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')

# Cargar el mapeo de géneros desde el archivo JSON
with open('genres_map.json', 'r') as f:
    genre_to_playlist = json.load(f)

# Configuración de la aplicación de Streamlit
st.title("Music GenAi Magic Turbo v4")
st.write("Genera listas de reproducción automáticamente basadas en tus canciones marcadas como 'Me gusta'.")

# Autenticación con Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope='playlist-modify-public user-library-read'
))

# Función para verificar si una canción ya está en una lista de reproducción
def is_track_in_playlist(playlist_id, track_id):
    playlist_tracks = sp.playlist_tracks(playlist_id, fields='items.track.id')
    track_ids = [item['track']['id'] for item in playlist_tracks['items']]
    return track_id in track_ids

# Botón de Streamlit para iniciar el proceso
if st.button('Generar listas de reproducción'):
    # Obtener las canciones marcadas como 'Me gusta'
    results = sp.current_user_saved_tracks()
    all_tracks = results['items']

    while results['next']:
        results = sp.next(results)
        all_tracks.extend(results['items'])

        # Obtener todas las listas de reproducción del usuario
    playlists = sp.current_user_playlists(limit=50)
    playlist_map = {playlist['name'].lower(): playlist['id'] for playlist in playlists['items']}

    # Definir las listas de reproducción que necesitas
    required_playlists = ['dale weon', 'toy o no toy', 'canto do dusha', 'rapapolvo', 'k lo k', 'blackhole']

    # Crear listas de reproducción que no existen
    for playlist_name in required_playlists:
        if playlist_name not in playlist_map:
            # Crear la lista de reproducción
            new_playlist = sp.user_playlist_create(
                user=sp.me()['id'],
                name=playlist_name,
                public=True,
                description=f'Playlist de género {playlist_name}'
            )
            # Añadir al mapa de listas de reproducción
            playlist_map[playlist_name] = new_playlist['id']





    # Crear la lista "Blackhole" si no existe
    if "blackhole" not in playlist_map:
        new_playlist = sp.user_playlist_create(
            user=sp.me()['id'],
            name="Blackhole",
            public=True,
            description="Canciones sin género o con géneros no clasificados"
        )
        playlist_map["blackhole"] = new_playlist['id']

    # Procesar y asignar las canciones a listas basadas en el mapeo de géneros
    for item in all_tracks:
        track = item['track']
        track_name = track['name']
        track_id = track['id']
        artist_name = track['artists'][0]['name']
        artist_id = track['artists'][0]['id']

        # Obtener géneros asociados al artista
        genres = sp.artist(artist_id)['genres']
        if not genres:
            genres = ['Sin género']

        # Contar a qué lista pertenece cada género
        playlist_count = {}
        for genre in genres:
            genre_lower = genre.lower()
            for playlist, genre_list in genre_to_playlist.items():
                if genre_lower in genre_list:
                    playlist_count[playlist] = playlist_count.get(playlist, 0) + 1

        # Determinar la lista con la mayoría de géneros
        if playlist_count:
            max_count = max(playlist_count.values())
            possible_playlists = [playlist for playlist, count in playlist_count.items() if count == max_count]
            target_playlist = possible_playlists[0]  # Elegir la primera en caso de empate
        else:
            target_playlist = "Blackhole"

        # Verificar si la canción ya está en la lista de reproducción
        if not is_track_in_playlist(playlist_map[target_playlist.lower()], track_id):
            sp.playlist_add_items(playlist_map[target_playlist.lower()], [track_id])
            st.write(f'Canción "{track_name}" de {artist_name} añadida a la lista "{target_playlist}".')
        else:
            st.write(f'Canción "{track_name}" de {artist_name} ya está en la lista "{target_playlist}".')

    st.success("Proceso completado. Las canciones se han asignado a las listas de reproducción.")
