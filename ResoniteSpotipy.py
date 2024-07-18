import asyncio
import websockets
import spotipy

from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth

def current_time():
    return f"{datetime.now():%d.%m.%y (%H:%M:%S)}"

#---------------------------------
# Spotify API initialization code
#---------------------------------

# Reads data from the IDs.txt file and parses them to be used in the API
def read_data():
    results: list[str | int] = ["", "", "", 0]
    indices: list[int]       = [1, 2, 5, 9]
    
    with open("IDs.txt") as file:
        lines: list[str] = file.readlines()
    
    for i in range(0, 4):
        results[i] = lines[indices[i]].split(" ")[2].removesuffix("\n")
        i += 1
    
    results[3] = int(results[3])
    return results

[CLIENT_ID, CLIENT_SECRET, REDIRECT_URL, PORT] = read_data()
print(read_data())
SCOPE = "user-library-modify,user-library-read,user-read-currently-playing,user-read-playback-position,user-read-playback-state,user-modify-playback-state,app-remote-control,streaming,playlist-read-private,playlist-modify-private,playlist-modify-public,playlist-read-collaborative"

sp: spotipy.Spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URL, scope=SCOPE))

print(current_time(), "Connected to Spotify")

#--------------------------------------------------------------

SEARCH_MENU = ""
DEVICE = ""

# Finds the active playback device
def find_device():
    global DEVICE
    
    if (not sp.devices()['devices']):
        print("[ERROR] No devices found")
        raise Exception("No devices found")
    else:
        DEVICE = sp.devices()['devices'][0]['id']
        print(f"Active device: {DEVICE}")

# Attempts to run the given action with the given arguments and if it can't, it will attempt to run it with the stored device ID
def run_action(action: callable, *args):
    find_device()
    
    try:
        action(*args, DEVICE) if args else action(device_id = DEVICE)
    except:
        print("[ERROR] Device not found")

# Parses song data from the dictionary of information
def get_song_data(song_data, type: str):
    data: str  = ""
    info: dict = song_data['item']
    
    try:    
        header: str = f"[{type.capitalize()}]"
        
        for idx, artist in enumerate(info['artists']):
            data += artist['name']
            data += ", " if (idx + 1 != len(info['artists'])) else ""
        artists: str = data
        
        track_name: str = info['name']
        album_name: str = info['album']['name']
        
        try:
            album_cover: str = info['album']['images'][0]['url']
        except IndexError:
            album_cover: str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"
        
        payload: str = (header + "\t" +
                        artists + "\t" +
                        track_name + "\t" +
                        album_name + "\t" +
                        album_cover)
    except:
        payload: str = "[ERROR] Error getting song data"
    
    return payload

# Parses shuffle, repeat, and playing information from the current player
def get_playback_states(shuffle = "read", playback = "read", playing = "read"):
    payload: str = "[INIT]\t"
    result: str  = sp.current_playback()
    
    if (result == None):
        return "[ERROR] No playback active"
    
    try:
        shuffle_state: bool = result["shuffle_state"]
    except: # This only runs if the shuffle state is the Smart Shuffle
        shuffle_state: bool = True
    finally:
        payload += (str(shuffle_state) + "\t") if (shuffle == "read") else shuffle + "\t"
    
    repeat_state: str = result["repeat_state"]
    payload += (repeat_state.capitalize() + "\t") if (playback == "read") else playback + "\t"
    
    is_playing: bool = result["is_playing"]
    payload += str(is_playing) if (playing == "read") else playing
    
    return payload

# Parses the search/queue results found
def get_song_results(result, type: str, keyword = "items"):
    data: str    = ""
    payload: str = f"[{type.upper()}]"
    
    for i in range(len(result[keyword])):
        item: dict = result[keyword][i]
        data = ""
        for idx, artist in enumerate(item['artists']):
            data += artist['name']
            data += ", " if (idx + 1 != len(item['artists'])) else ""
        artists: str = data
        
        name: str = item['name']
        uri: str  = item['uri']
        
        try:
            icon: str = item['album']['images'][0]['url']
        except:
            icon: str = "https://developer.spotify.com/images/guidelines/design/icon3@2x.png"
        
        payload += ("\t" + name + "\t" + artists + "\t" + uri + "\t" + icon + "\n")
    
    return payload

# Parses the user's playlists, including the user's Liked Songs
def get_playlists():
    result: str  = sp.current_user_saved_tracks()
    payload: str = ("[PLAYLISTS]\t" + "Liked Songs" + "\t" + f"{str(result['total'])} Songs" + "\t"
                    + f"{sp.current_user()['uri']}:collection" + "\t" + "https://developer.spotify.com/images/guidelines/design/icon3@2x.png" + "\n")
    
    result = sp.current_user_playlists()
    
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

async def socket(websocket: websockets.WebSocketClientProtocol):
    # Initializing the websocket
    global SEARCH_MENU
    
    ID = str(websocket.id)
    print(f"{current_time()} Client {ID[:8]} connected!")
    find_device()
    
    await websocket.send(get_playback_states())
    
    try:
        async for message in websocket:
            # Message format: "command" "search results"
            parsed: list[str] = message.split(" ")
            received: str     = parsed[0]
            data: str | None  = " ".join(parsed[1:]) if len(parsed) > 1 else None
            if (data):
                print(f"[{ID[:8]}] {current_time()} Command received: {received} | {data}")
            else:
                received = message
                print(f"[{ID[:8]}] {current_time()} Command received: {received}")
            
            if (received == "current"):
                try:
                    _ = sp.current_user_playing_track()['item'] # Throws an error if there's no currently playing track
                    
                    await websocket.send(get_song_data(sp.current_user_playing_track(), type="current") + "\n" + get_playback_states())
                except:
                    await websocket.send("[ERROR] No current song active")
                    
            elif (received == "states"):
                try:
                    await websocket.send(get_playback_states())
                except:
                    await websocket.send("[ERROR] Error getting playback states")
                    
            elif (received == "next"):
                try:
                    run_action(sp.next_track)
                    
                    await websocket.send("[NEXT SONG]")
                except:
                    await websocket.send("[ERROR] Error going to next song")
            
            elif (received == "previous"):
                try:
                    if (sp.current_playback()["progress_ms"] > 4000):
                        run_action(sp.seek_track, 0)
                    else:
                        run_action(sp.previous_track)
                    
                    await websocket.send("[PREVIOUS SONG]")
                except:
                    await websocket.send("[ERROR] Error going to previous song")
            
            elif (received == "pause"):
                try:
                    run_action(sp.pause_playback)
                    
                    await websocket.send(get_playback_states(playing="False"))
                except:
                    await websocket.send("[ERROR] Error pausing playback")
            
            elif (received == "resume"):
                try:
                    run_action(sp.start_playback)
                    
                    await websocket.send(get_playback_states(playing="True"))
                except:
                    await websocket.send("[ERROR] Error resuming playback")
            
            elif (received == "shuffle"):
                try:
                    shuffle: bool = sp.current_playback()["shuffle_state"]
                    run_action(sp.shuffle, not shuffle)
                    
                    await websocket.send(get_playback_states(shuffle=str(not shuffle)))
                except:
                    await websocket.send("[ERROR] Error changing shuffle state")
            
            elif (received == "repeat"):
                try:
                    states: list[str] = ["track", "context", "off"]
                    repeat: str       = sp.current_playback()["repeat_state"]
                    change: str       = states[(states.index(repeat) + 1) if (repeat != "off") else 0]
                    run_action(sp.repeat, change)

                    await websocket.send(get_playback_states(playback=change.capitalize()))
                except:
                    await websocket.send("[ERROR] Error changing repeat state")
            
            elif (received == "playlists"):
                SEARCH_MENU = "playlists"
                await websocket.send(get_playlists())
            
            elif (received == "search"):
                if (data != ""):
                    SEARCH_MENU = "search"
                    await websocket.send(get_song_results(sp.search(data, market="US")["tracks"], type="search"))
                
            elif (received == "queue"):
                try:
                    _ = sp.queue()["queue"][0] # Throws an error if there's no queue available
                    
                    SEARCH_MENU = "queue"
                    await websocket.send(get_song_results(sp.queue(), type="queue", keyword="queue"))
                except:
                    await websocket.send("[ERROR] No queue found")
            
            elif (received == "play" and data != None):
                try:
                    if (SEARCH_MENU == "search"):
                        sp.start_playback(uris=[data]) # Plays just the searched song
                    elif (SEARCH_MENU == "playlists"):
                        sp.start_playback(context_uri=data) # Plays the playlist clicked on
                    else:
                        sp.start_playback(context_uri=sp.currently_playing()["context"]["uri"], offset={"uri": data}) # Plays song in the queue that was clicked on
                except:
                    await websocket.send("[ERROR] Error playing song")
            
            else:
                await websocket.send("[ERROR] Unknown command")
                
    except:
        print(current_time(), "Connection error with client.")

async def main():
    print(current_time(), "Booted up. Awaiting interaction...")
    async with websockets.serve(socket, 'localhost', PORT):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())