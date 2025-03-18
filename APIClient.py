import spotipy
from spotipy.oauth2 import SpotifyOAuth

from datetime import datetime

def current_time():
    return f"{datetime.now():%d.%m.%y (%H:%M:%S)}"

class APIClient(object):
    '''
    A class to handle the Spotify API with special functions for formatting and returning specific API call results.
    '''
    _api: spotipy.Spotify = None
    _device: str = None
    _debug: bool = False
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scope: str):
        '''
        A constructor for the APIClient class.
        
        :param client_id:
            Your Spotify application's client ID
        :param client_secret:
            Your Spotify application's client secret
        :param redirect_uri:
            One of your Spotify application's redirect URIs
        :param scope:
            The scopes you want to use for the API
        '''
        self._api = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope))
        print(current_time(), "Connected to Spotify")
    
    def find_device(self, *device_id: str):
        '''
        A function that finds an available device to play from.
        Raises an exception if it can't find any.
        
        :param device_id:
            The ID of the device to use if the user specified one, otherwise the first available device will be used
        '''
        
        if (self._device):
            return None
    
        device_list: list = self._api.devices()['devices']
        
        if (not device_list):
            print("[ERROR] No active devices found")
        else:
            if (len(device_list) == 1):
                self._device = self._api.devices()['devices'][0]['id']
            elif (len(device_list) > 1) and (device_id):
                self._device = [x for x in device_list if x['id'] == device_id][0]['id']
            else:
                run: bool = True
                while (run):
                    for (i, x) in enumerate(device_list):
                        print(f"[{i}]: Device: {x['name']}")
                    _ = int(input("Please enter the index of the device to use: "))
                    
                    if (device_list[_]['id']):
                        self._device = device_list[_]['id']
                        run = False
                        break
                    else:
                        print("[ERROR] Invalid index")

            print(f"Active device: {self._device}") if self._debug else None
    
    def run_action(self, action: callable, *args):
        '''
        A function that attempts to run the given action with the given arguments and if it can't, it will attempt to run it with the stored device ID.
        This is only useful for actions that require there to be an active device, such as pausing/resuming playback.
        
        :param action:
            The function to call
        :param args:
            The arguments to pass to the function
        '''
        
        self.find_device()
        
        try:
            action(*args, self._device) if args else action(device_id = self._device)
            print(f"[SUCCESS] Action '{action}' ran successfully") if self._debug else None
        except:
            print("[ERROR] Device not found")
    
    def get_playback_states(self, shuffle = "read", repeat = "read", playing = "read") -> str:
        '''
        A function that returns the current playback states of the active device (shuffle, repeat, and playing).
        
        :param shuffle:
            If shuffle is `read`, it'll use the current shuffle state. Otherwise, it'll use the given value (`true` or `false`)
        :param repeat:
            If repeat is `read`, it'll use the current repeat state. Otherwise, it'll use the given value (`track`, `context`, or `off`)
        :param playing:
            If playing is `read`, it'll use the current playing state. Otherwise, it'll use the given value (`true` or `false`)
            
        :return payload:
            The playback states in the following format:
            `[INIT]\t{shuffle}\t{repeat}\t{playing}`
        '''
        
        payload: str = "[INIT]\t"
        result: str  = self._api.current_playback()
        
        if (result is None):
            return "[ERROR] No playback active"
        
        shuffle_state: bool = result["shuffle_state"]
        payload += (str(shuffle_state) + "\t") if (shuffle == "read") else shuffle + "\t"
        
        repeat_state: str = result["repeat_state"]
        payload += (repeat_state.capitalize() + "\t") if (repeat == "read") else repeat + "\t"
        
        is_playing: bool = result["is_playing"]
        payload += str(is_playing) if (playing == "read") else playing
        
        return payload
    
    def get_track_data(self, track_dict: dict, ws_call: str) -> str:
        '''
        A function that returns the track data from the given track dictionary.
        
        :param track_dict:
            The track dictionary to get the data from
        :param ws_call:
            The specific keyword the websocket listens to know how to deal with the payload (`current` is the only one so far)
        
        :return payload:
            The track data in the following format:
            `[{ws_call}]\t{artists}\t{track_name}\t{album_name}\t{album_cover}\t{uri}`
        '''
        
        data: str  = ""
        info: dict = track_dict['item']
        
        try:    
            header: str = f"[{ws_call.capitalize()}]"
            
            for idx, artist in enumerate(info['artists']):
                data += artist['name']
                data += ", " if (idx + 1 != len(info['artists'])) else ""
            artists: str = data
            
            track_name: str = info['name']
            album_name: str = info['album']['name']
            uri: str        = info['uri'] if ws_call != "current" else info["external_urls"]["spotify"]
            
            try:
                album_cover: str = info['album']['images'][0]['url']
            except IndexError: # If the track doesn't have an album cover
                album_cover: str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"
            
            payload: str = (header + "\t" +
                            artists + "\t" +
                            track_name + "\t" +
                            album_name + "\t" +
                            album_cover + "\t" +
                            uri)
        except:
            payload: str = "[ERROR] Error getting song data"
        
        return payload
    
    def get_results(self, results: dict, ws_call: str, keyword = "items") -> str:
        '''
        A function that returns the results of the given results dictionary, whether from searching, listing the playback queue, or from listing an album's or playlist's tracks.
        
        :param results:
            The results dictionary to get the data from
        :param ws_call:
            The specific keyword the websocket listens to to know how to deal with the payload (`search`, `queue`, `album`, or `playlist`)
        :param keyword:
            The keyword of the results to get the data from (`queue` if `ws_call == queue`)
            
            Setting `keyword = ""` will ignore the keyword and use the results dictionary as is
            
        :return payload:
            The results in the following format:
            `[{ws_call}]\t{name}\t{artists}\t{uri}\t{icon}\n...`
        '''
        
        data: str    = ""
        payload: str = f"[{ws_call.upper()}]"
        
        iterate: dict = results[keyword] if keyword != "" else results
        
        for i in range(len(iterate)):
            try:
                item: dict = iterate[i]['track']
            except:
                item: dict = iterate[i]
            
            data = ""
            for idx, artist in enumerate(item['artists']):
                data += artist['name']
                data += ", " if (idx + 1 != len(item['artists'])) else ""
            artists: str = data
            
            name: str = item['name']
            uri: str  = item['uri']
            
            try: # Checking if the result is that of a track
                icon: str = item['album']['images'][0]['url']
            except:
                try: # Checking if the result is that of an album
                    icon: str = item['images'][0]['url']
                    name = f"<u>{name}</u>"
                except: # If there's no album cover
                    icon: str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"
            
            payload += ("\t" + name + "\t" + artists + "\t" + uri + "\t" + icon + "\n")
        
        return payload
    
    def get_artists(self, results: dict) -> str:
        '''
        A function that returns the artists of the given results dictionary
        
        :param results:
            The results dictionary to get the data from
        
        :return payload:
            The artists in the following format:
            `[ARTISTS]\t{name}\t{count}\t{uri}\t{icon}\n...`
        '''
        
        payload: str = "[SEARCH]"
        
        for artist in results["items"]:
            name:       str = artist["name"]
            uri:        str = artist["external_urls"]["spotify"]
            try:
                icon:       str = artist["images"][0]["url"]
            except:
                icon:       str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"
            followers:  str = str(artist["followers"]["total"]) + " Followers"
            
            payload += ("\t" + name + "\t" + followers + "\t" + uri + "\t" + icon + "\n")
        
        return payload
    
    def get_playlists(self) -> str:
        '''
        A function that returns the saved playlists of the current user, as well as their liked songs playlist
        
        :return payload:
            The playlists in the following format:
            `[PLAYLISTS]\t{name}\t"{count} Songs"\t{uri}\t{icon}`
        '''
        
        result: str  = self._api.current_user_saved_tracks()
        payload: str = ("[PLAYLISTS]\t" + "Liked Songs" + "\t" + f"{str(result['total'])} Songs" + "\t"
                        + f"{self._api.current_user()['uri']}:collection" + "\t" + "https://developer.spotify.com/images/guidelines/design/icon3@2x.png" + "\n")
        
        result = self._api.current_user_playlists()
        
        for i in range(len(result["items"])):
            item: dict = result['items'][i]
            
            name: str  = item['name']
            count: str = item['tracks']['total']
            uri: str   = item['uri']
            
            try:
                icon: str = item['images'][0]['url']
            except:
                icon: str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"

            payload += "\t" + name + "\t" + f"{str(count)} Songs" + "\t" + uri + "\t" + icon + "\n"
        
        return payload
    
    def display_album(self, album: dict) -> str:
        '''
        A function that displays the album information from the given album dictionary
        
        :param album:
            The album dictionary to read from
        
        :return payload:
            The album data (and tracks) in the following format:
            `[ALBUM]\t{name}\t{artists}\t{count}\t{uri}\t{tracks}`
        '''
        
        data: str    = ""
        payload: str = "[ALBUM]"
        
        for idx, artist in enumerate(album["artists"]):
            data += artist["name"]
            data += ", " if (idx + 1 != len(album["artists"])) else ""
        artists: str = data
        
        name: str  = album["name"]
        count: str = str(album["total_tracks"])
        uri: str   = album["uri"]
        icon: str  = album["images"][0]["url"]
        
        disc1_dict: list[dict] = []
        disc2_dict: list[dict] = []
        
        for idx, item in enumerate(album["tracks"]["items"]):
            if (item["disc_number"] == 1):
                disc1_dict.append(item)
            elif (item["disc_number"] == 2):
                disc2_dict.append(item)
                
        payload += ("\t" + name + "\t" + artists + "\t" + count + "\t" + uri + "\t" + icon + "\n")
        
        disc1: str = self.get_results(disc1_dict, ws_call="none", keyword="")
        payload += disc1.removeprefix("[NONE]\t")
        
        if (len(disc2_dict) > 0):
            disc2: str = self.get_results(disc2_dict, ws_call="none", keyword="")
            payload += ("\t" + "[DISC2]\t" + disc2.removeprefix("[NONE]\t"))
        
        return payload
    
    def display_playlist(self, playlist: dict, offset: int, uri: str = "") -> str:
        '''
        A function that displays the playlist information from the given playlist dictionary
        
        :param playlist:
            The playlist dictionary to read from
        
        :return payload:
            The playlist data in the following format:
            `[PLAYLIST]\t{name}\t{count}\t{uri}\t{tracks}`
        '''
        
        payload: str = "[PLAYLIST]"
        
        try:
            name: str  = playlist["name"]
            owner: str = playlist["owner"]["display_name"]
            count: str = str(playlist["tracks"]["total"])
            uri: str   = playlist["uri"]
            
            track_dict: dict = self._api.playlist_tracks(playlist_id=playlist["uri"], offset=int(count)-offset-20, limit=20)
            track_dict["items"] = track_dict["items"][::-1]
        except:
            name: str  = "Liked Songs"
            owner: str = " "
            count: str =str(playlist["total"])
            
            track_dict: dict = self._api.current_user_saved_tracks(offset=offset, limit=20)

        try:
            icon: str  = playlist["images"][0]["url"]
        except:
            icon: str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"
        
        tracks: str         = self.get_results(track_dict, ws_call="none")
        
        payload += ("\t" + name + "\t" + owner + "\t" + count + "\t" + uri + "\t" + icon + "\n" + tracks.removeprefix("[NONE]\t") + "\t")
        
        return payload

    def display_artist(self, artist: dict, artist_top_tracks: dict, aritst_albums: dict) -> str:
        '''
        A function that returns the artist information from the given artist dictionary
        
        :param artist:
            General artit information
        :param artist_top_tracks:
            The top tracks of the artist
        :param aritst_albums:
            The albums of the artist
        
        :return payload:
            The artist data in the following format:
            `[ARTIST]\t{name}\t{uri}\t{icon}\t{followers}\t{top_tracks}\t{albums}`
        '''
        
        payload: str = "[ARTIST]"
        
        name:       str = artist["name"]
        url:        str = artist["uri"]
        icon:       str = artist["images"][0]["url"]
        followers:  str = str(artist["followers"]["total"])
        
        top_tracks: str = self.get_results(artist_top_tracks, ws_call="TOP", keyword="tracks")
        albums:     str = self.get_results(aritst_albums, ws_call="ALBUMS", keyword="items")
        
        payload += ("\t" + name + "\t" + url + "\t" + icon + "\t" + followers + "\t\t\t" + top_tracks.removeprefix("[NONE]\t") + "\t\t\t" + albums.removeprefix("[NONE]\t"))
        
        return payload