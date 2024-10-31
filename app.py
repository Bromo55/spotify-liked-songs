import os
import json
import streamlit as st
import requests
from dotenv import load_dotenv

# Cargar las variables de entorno desde un archivo .env
load_dotenv()

# Configuración de autenticación
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = 'https://spotify-liked-songs.streamlit.app'  # Cambia esto según tu configuración
redirect_uri = 'http://localhost:8888/callback'  # Cambia esto según tu configuración

# Cargar el mapeo de géneros desde el archivo JSON
with open('genres_map.json', 'r') as f:
    genre_to_playlist = json.load(f)

# Configuración de la aplicación de Streamlit
st.title("Music GenAi Magic Turbo v4")
st.write("Genera listas de reproducción automáticamente basadas en tus canciones marcadas como 'Me gusta'.")

# Generar la URL de autenticación
auth_url = f"https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=playlist-modify-public user-library-read"

# Mostrar el enlace para iniciar la autenticación
st.markdown(f"[Iniciar Autenticación]({auth_url})", unsafe_allow_html=True)

# Obtener el código de la URL si está presente
query_params = st.query_params
if 'code' in query_params:
    code = query_params['code']  # Obtener el código de autorización
    st.success(f"Código de autorización recibido: {code}")

    # Intercambiar el código por un token de acceso
    token_url = "https://accounts.spotify.com/api/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    response = requests.post(token_url, data=token_data)
    response_data = response.json()

    if 'access_token' in response_data:
        access_token = response_data['access_token']
        st.success("Acceso autorizado. ¡Listo para hacer llamadas a la API!")

        # Obtener el usuario actual
        user_url = "https://api.spotify.com/v1/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get(user_url, headers=headers)

        if user_response.status_code == 200:
            current_user = user_response.json()
            st.success(f'Usuario actual: {current_user["display_name"]}')
            # Mostrar la imagen del usuario
            if current_user['images']:
                user_image_url = current_user['images'][0]['url']  # Obtener la primera imagen
                st.image(user_image_url, width=100)  # Ajusta el tamaño según sea necesario
            else:
                st.write("No hay imagen de perfil disponible.")

            # Obtener las canciones marcadas como 'Me gusta'
            results = requests.get("https://api.spotify.com/v1/me/tracks", headers=headers)
            st.success(results)
            all_tracks = results.json().get('items', [])

            if all_tracks:
                first_track = all_tracks[0]['track']  # Acceder a la primera canción
                track_name = first_track['name']       # Obtener el nombre de la canción
                artist_name = first_track['artists'][0]['name']  # Obtener el nombre del artista
                st.write(f'Primera canción: {track_name} de {artist_name}')
            else:
                st.write("No hay canciones guardadas.")

            # Obtener todas las listas de reproducción del usuario
            playlists = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
            playlist_map = {playlist['name'].lower(): playlist['id'] for playlist in playlists.json().get('items', [])}

            # Definir las listas de reproducción que necesitas
            required_playlists = ['dale weon', 'toy o no toy', 'canto do dusha', 'rapapolvo', 'k lo k', 'blackhole']
            
            # Crear listas de reproducción que no existen
            for playlist_name in required_playlists:
                if playlist_name not in playlist_map:
                    # Crear la lista de reproducción
                    new_playlist = requests.post(
                        f"https://api.spotify.com/v1/users/{current_user['id']}/playlists",
                        headers=headers,
                        json={
                            "name": playlist_name,
                            "public": True,
                            "description": f'Playlist de género {playlist_name}'
                        }
                    ).json()
                    # Añadir al mapa de listas de reproducción
                    playlist_map[playlist_name] = new_playlist['id']

            # Crear la lista "Blackhole" si no existe
            if "blackhole" not in playlist_map:
                new_playlist = requests.post(
                    f"https://api.spotify.com/v1/users/{current_user['id']}/playlists",
                    headers=headers,
                    json={
                        "name": "Blackhole",
                        "public": True,
                        "description": "Canciones sin género o con géneros no clasificados"
                    }
                ).json()
                playlist_map["blackhole"] = new_playlist['id']

            # Procesar y asignar las canciones a listas basadas en el mapeo de géneros
            for item in all_tracks:
                track = item['track']
                track_name = track['name']
                track_id = track['id']
                artist_name = track['artists'][0]['name']
                artist_id = track['artists'][0]['id']

                # Obtener géneros asociados al artista
                genres = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}", headers=headers).json().get('genres', [])
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
                track_check = requests.get(f"https://api.spotify.com/v1/playlists/{playlist_map[target_playlist.lower()]}/tracks", headers=headers)
                track_ids = [item['track']['id'] for item in track_check.json().get('items', [])]

                if track_id not in track_ids:
                    requests.post(
                        f"https://api.spotify.com/v1/playlists/{playlist_map[target_playlist.lower()]}/tracks",
                        headers=headers,
                        json={"uris": [f"spotify:track:{track_id}"]}
                    )
                    st.write(f'Canción "{track_name}" de {artist_name} añadida a la lista "{target_playlist}".')
                else:
                    st.write(f'Canción "{track_name}" de {artist_name} ya está en la lista "{target_playlist}".')

            st.success("Proceso completado. Las canciones se han asignado a las listas de reproducción.")
        else:
            st.error("Error al obtener el usuario actual.")
    else:
        st.error("Error al intercambiar el código por el token de acceso.")
else:
    st.write("Por favor, autentícate para continuar.")
