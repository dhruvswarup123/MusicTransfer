from gmusicapi import Mobileclient, Musicmanager
import spotipy
import spotipy.util as util
import itertools as it
from fuzzywuzzy import fuzz

import sys
import vlc
import re
import webbrowser
import time


# Source: https://docs.python.org/2/library/itertools.html Section 9.7.2: Recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return list(it.zip_longest(fillvalue=fillvalue, *args))


def initial_login_google(client):
    client.perform_oauth()
    return


def login_google():
    client = Mobileclient()
    if not client.oauth_login(Mobileclient.FROM_MAC_ADDRESS):
        print("Not logged in before! Follow instructions below! Once logged in, no need to log in again...")
        initial_login_google(client)
    return client


def getSongsGoogle(client):
    google_library = client.get_all_songs()
    return [(s['title'], s['artist']) for s in google_library]


def spotifyLogin(username, clientid, clientsecret, redirect):
    token = util.prompt_for_user_token(username, 'playlist-modify-public',
                                       client_id=clientid,
                                       client_secret=clientsecret,
                                       redirect_uri=redirect)
    return spotipy.Spotify(auth=token)


def lower(j):
    return tuple([i.lower() for i in j])


def compare(str1, str2):
    if fuzz.token_set_ratio(str1, str2) < 75:
        return False
    return True

if __name__ == '__main__':
    google_client = login_google()
    google_songs = getSongsGoogle(google_client)
    google_songs.sort(key=lower)

    username = ''
    playlist_name = ''
    clientid = ''
    clientsecret = ''
    redirect = "http://localhost:/callback"

    sp = spotifyLogin(username, clientid, clientsecret, redirect)
    sp.trace = False

    playlists = sp.user_playlists(username)
    # for i in google_songs:
    #     print(i)

    playlist_id = None
    for playlist in playlists['items']:
        if playlist['owner']['id'] == username:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']

    if not playlist_id:
        raise ValueError("Error: Spotify Playlist name not found!")

    track_ids = []
    alladded = []

    with open("not_added.txt", "w") as fp:
        for song, artist in google_songs:
            try:
                song = re.sub("\(.*\)", "", song) # Remove parenthesis for easier matching
                results = sp.search(q=f'{song} artist:{artist}')
                items = results['tracks']['items']

                spotifyartist = ''
                for i in items[0]['artists']:
                    spotifyartist += i['name'] + ', '

                if not compare(artist, spotifyartist):
                    raise ValueError("Wrong artist")

                track_id = items[0]['uri']
                track_ids.append(track_id)
                alladded.append(song)

            except Exception as e:
                fp.write(song + '    ' + str(e) + '\n')
                print(song + '    ' + str(e) + f'    {artist} <-> {spotifyartist}')

    with open("added.txt", "w") as fp:
        for i in alladded:
            fp.write(i + '\n')

    print("Adding...")
    for limited_track_ids in grouper(track_ids, 100):
        limited_track_ids = [track_id for track_id in limited_track_ids if track_id is not None]
        results = sp.user_playlist_add_tracks(username, playlist_id, limited_track_ids)
        print("Added hundred.")
    print("All Done...")
