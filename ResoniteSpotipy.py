import asyncio as aio
import websockets as ws
import spotipy as sp

from APIClient import APIClient # The class that handles the Spotify API and custom functions

from datetime import datetime
def current_time():
    return f"{datetime.now():%d.%m.%y (%H:%M:%S)}"

import argparse as arg
parser = arg.ArgumentParser(description="The websocket server for the Resonite Spotipy project")
parser.add_argument("-d", "--debug", dest="debug", action="store_true", help="Prints debug messages", default=False)
args = parser.parse_args()

DEBUG: bool = args.debug # A variable for the program to know if it should print debug messages into the console

#--------------------------------------------------------------

DISPLAY: str = "" # A variable for the websocket to know what is displayed in the Spotify menu

# Displays current information about the currently playing track and/or the playback states
def display_current_info(received: str) -> str:
    payload: str = ""
    
    match (received):
        case "current_info": # Used for getting the currently playing track and the playback states
            try:
                _ = API.current_user_playing_track()['item'] # Throws an error if there's no currently playing track
                
                payload = CLIENT.get_track_data(API.current_user_playing_track(), ws_call="current") + "\n" + CLIENT.get_playback_states()
            except:
                payload = "[ERROR] No current song active"
        
        case "current_track":
            try:
                _ = API.current_user_playing_track()['item'] # Throws an error if there's no currently playing track
                
                payload = CLIENT.get_track_data(API.current_user_playing_track(), ws_call="current")
            except:
                payload = "[ERROR] No current song active"
        
        case "current_states":
            try:
                payload = CLIENT.get_playback_states()
            except:
                payload = "[ERROR] Error getting playback states"
    
    return payload

# Modifies the currently playing track, like going to the next or previous song, or playing a new song
def modify_current_track(received: str, data: str) -> str:
    payload: str = ""
    
    match (received):
        case "next":
            try:
                CLIENT.run_action(API.next_track)
                
                payload = "[NEXT SONG]"
            except:
                payload = "[ERROR] Error going to next song"
        
        case "previous":
            try:
                if (API.current_playback()["progress_ms"] > 4000):
                    CLIENT.run_action(API.seek_track, 0)
                else:
                    CLIENT.run_action(API.previous_track)
                
                payload = "[PREVIOUS SONG]"
            except:
                payload = "[ERROR] Error going to previous song"
        
        case "play":
            if (data != None):
                # Format for searching: "<track | album | track,album> <uri>"
                # Format for playing from playlist or album: "<uri> <offset uri>"
                # Format for playing from queue: "<offset uri>"
                play_data: list[str] = data.split(" ")
                try:
                    match (DISPLAY):
                        case "search":
                            if (play_data[0] == "track"):
                                API.start_playback(uris=[play_data[1]]) # Plays just the selected song
                                payload = "[PLAY] Played selected searched song"
                        
                        case "queue":
                            API.start_playback(context_uri=API.currently_playing()["context"]["uri"], offset={"uri": play_data[1]}) # Plays song in the queue that was clicked on
                            payload = "[PLAY] Played selected song in queue"
                        
                        case "playlist" | "album":
                            if (len(play_data) == 3):
                                API.start_playback(context_uri=play_data[1], offset={"uri": play_data[2]}) # Plays song in the playlist/album that was clicked on
                                payload = "[PLAY] Played selected song in playlist/album"
                            else:
                                API.start_playback(context_uri=play_data[1]) # Plays the playlist/album that was clicked on
                                payload = "[PLAY] Played selected playlist/album"
                        
                except:
                    payload = "[ERROR] Error playing song"

    return payload

# Modifies the playback states, like pausing, resuming, or changing the shuffle state
def modify_playback_states(received: str) -> str:
    payload: str = ""
    
    if (received == "pause" or received == "resume"):
        try:
            _ = API.current_user_playing_track()['is_playing']
        except:
            _ = False
        
        playing = "False" if _ else "True"
        
        try:
            CLIENT.run_action(API.pause_playback) if _ else CLIENT.run_action(API.start_playback)
            
            payload = CLIENT.get_playback_states(playing=playing)
        except:
            payload = "[ERROR] Error pausing/resuming playback"
             
    match (received):       
        case "shuffle":
            try:
                shuffle: bool = API.current_playback()["shuffle_state"]
                CLIENT.run_action(API.shuffle, not shuffle) # Throws an error if it can't change the shuffle state
                
                payload = CLIENT.get_playback_states(shuffle=str(not shuffle))
            except:
                payload = "[ERROR] Error changing shuffle state"
        
        case "repeat":
            try:
                states: list[str] = ["track", "context", "off"]
                repeat: str       = API.current_playback()["repeat_state"]
                change: str       = states[(states.index(repeat) + 1) if (repeat != "off") else 0]
                CLIENT.run_action(API.repeat, change) # Throws an error if it can't change the repeat state

                payload = CLIENT.get_playback_states(repeat=change.capitalize())
            except:
                payload = "[ERROR] Error changing repeat state"
    
    return payload

# Lists results stuff, such as playlists, currently playing queue, or search results
def list_stuff(received: str, data: str) -> str:
    global DISPLAY
    payload: str = ""
    
    match (received):
        case "list_playlists":
            DISPLAY = "playlists"
            payload = CLIENT.get_playlists()

        case "search":
            try:
                DISPLAY = "search"
                search_data: list[str] = data.split(" ") # Format: "<type> <search query>"
                
                if (len(search_data) > 1):
                    search_results = API.search(" ".join(search_data[1:]), type=search_data[0], market="US") # Valid arguments for type: "track", "album", "track,album"
                    
                    search_split = search_data[0].split(",")
                    if (len(search_split) > 1): # If the search is for more than one type
                        payload = ""
                        for type in search_split:
                            res = search_results[f"{type}s"]
                            payload += CLIENT.get_results(res, ws_call="search") if type != "artist" else CLIENT.get_artists(res)
                    elif (search_data[0] == "artist"):
                        payload = CLIENT.get_artists(search_results["artists"])
                    else:
                        payload = CLIENT.get_results(search_results[f"{search_data[0]}s"], ws_call="search")
            except:
                payload = "[ERROR] Error searching"
            
        case "list_queue":
            try:
                _ = API.queue()["queue"][0] # Throws an error if there's no queue available
                
                DISPLAY = "queue"
                payload = CLIENT.get_results(API.queue(), ws_call="queue", keyword="queue")
            except:
                payload = "[ERROR] No queue found"
    
    return payload

# Displays tracks in an album or playlist
def display_info(received: str, data: str) -> str:
    global DISPLAY
    payload: str = ""
    
    match (received):
        case "display_album":
            # Data format: <album uri>
            try:
                DISPLAY = "album"
                _ = API.album_tracks(data)["items"][0] # Throws an error if there are no tracks in the album
            
                payload = CLIENT.display_album(API.album(data))
            except:
                payload = "[ERROR] Error loading album tracks"

        case "display_playlist":
            # Data format: <playlist uri> <offset>
            DISPLAY = "playlist"
            spl = data.split(" ")
            try:
                if ("collection" in spl[0]):
                    _ = API.current_user_saved_tracks()["items"][0] # Throws an error if there are no tracks in their Liked Songs
                    
                    payload = CLIENT.display_playlist(API.current_user_saved_tracks(), offset=int(spl[1]), uri=spl[0])
                else:
                    _ = API.playlist(playlist_id=spl[0])["tracks"]["items"] # Throws an error if there are no tracks in the playlist
                
                    payload = CLIENT.display_playlist(API.playlist(playlist_id=spl[0]), offset=int(spl[1]))
            except:
                payload = "[ERROR] Error loading playlist tracks"
        
        case "display_artist":
            # Data format: <artist uri>
            DISPLAY = "artist"
            try:
                _ = API.artist_top_tracks(data)["tracks"][0] # Throws an error if the artist has no tracks
                
                payload = CLIENT.display_artist(API.artist(data), API.artist_top_tracks(data), API.artist_albums(data))
            except:
                payload = "[ERROR] Error loading artist"
    
    return payload

async def socket(websocket: ws.WebSocketClientProtocol):
    global DISPLAY
    
    # Initializing the websocket
    ID = str(websocket.id)
    print(f"{current_time()} Client {ID[:8]} connected!")
    
    await websocket.send(CLIENT.get_playback_states())
    
    try:
        async for message in websocket:
            # Message format: "command" "extra data"
            parsed: list[str] = message.removesuffix(" ").split(" ")
            received: str     = ""
            data: str | None  = None
            
            if (len(parsed) < 2):
                received = message
                print(f"[{ID[:8]}] {current_time()} Command received: {received}")
            else:
                received = parsed[0]
                data     = " ".join(parsed[1:])
                print(f"[{ID[:8]}] {current_time()} Command received: {received} | {data}")

            payload: str = ""
            
            if (received in ["current_info", "current_song", "current_states"]):
                payload = display_current_info(received)
                
            elif (received in ["next", "previous", "play"]):
                payload = modify_current_track(received, data)

            elif (received in ["pause", "resume", "shuffle", "repeat"]):
                payload = modify_playback_states(received)
                
            elif (received in ["list_playlists", "search", "list_queue"]):
                payload = list_stuff(received, data)
            
            elif (received in ["display_album", "display_playlist", "display_artist"]):
                payload = display_info(received, data)
            
            else:
                payload = "[ERROR] Unknown command"
        
            print(f"[{ID[:8]}] {current_time()} Response sent: {payload}") if DEBUG and payload != "" else None
            await websocket.send(payload)
            
    except:
        print(current_time(), "Connection error with client.")
        
#--------------------------------------------------------------

API: sp.Spotify = None
CLIENT: APIClient = None
PORT: int = 0000

# Reads data from the IDs.txt file and parses them to be used in the API
def connect_to_spotify():
    global API, CLIENT, PORT
    
    results: list[str | int] = ["", "", "", 0]
    indices: list[int]       = [1, 2, 5, 9]
    
    with open("IDs.txt") as file:
        lines: list[str] = file.readlines()
    
    for i in range(0, 4):
        results[i] = lines[indices[i]].split(" ")[2].removesuffix("\n").replace("<", "").replace(">", "")
        i += 1
    PORT = int(results[3])
    
    if (str(results[3]) in results[2]):
        raise Exception(f"Invalid port! ({PORT = }). Use a different port than the one used by the callback URI.")
    
    print(results) if DEBUG else None
    
    _ = """user-library-modify,user-library-read,user-read-currently-playing,user-read-playback-position,
            user-read-playback-state,user-modify-playback-state,app-remote-control,streaming,playlist-read-private,
            playlist-modify-private,playlist-modify-public,playlist-read-collaborative"""
    CLIENT = APIClient(results[0], results[1], results[2], _)
    API = CLIENT._api
    CLIENT._debug = DEBUG
    
    CLIENT.find_device()

async def main():
    connect_to_spotify()
    print(current_time(), "Booted up. Awaiting interaction...")
    
    async with ws.serve(socket, 'localhost', PORT):
        await aio.Future()

if __name__ == '__main__':
    aio.run(main())