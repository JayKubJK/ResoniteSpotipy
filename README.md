# Resonite Spotipy
A websocket server for talking with the Spotify API with a Resonite websocket client item to compliment it
![image](https://github.com/user-attachments/assets/77ffd3cb-40c4-4e48-99d1-e778760c18f3)

Here's the Resonite record link for the Resonite Spotipy audio player:
`resrec:///U-JayKub/R-CAF0B1B9598EF23797BE641C09DBBD3905EA75224EBD0F7F08F2AD4B61579001`

## Prerequisites
You'll need these Python packages: *websockets*, *asyncio*, *spotipy*. You'll also need Python 3.9 at least.
- To install these, run this command: ```pip install websockets asyncio spotipy```

## How to setup your Spotify application
**You'll need Spotify Premium to be able to do this!**
- Go to the Spotify Developer Dashboard: https://developer.spotify.com/dashboard
- Click on "Create app"
- Give it a name, description, and ensure that you have a redirect URL for the application (I recommend putting both of these in: "http://localhost:8000/callback" and "http://localhost:8000")
- Once created, go to the application's Settings panel
    - Here's where you'll find the application's Client ID and, by clicking on the "view client secret" button, the Secret ID

## How to setup the websocket server
- Download the ZIP package in the files and unzip it
- In the IDs.txt file, paste in your Spotify application's Client ID, Secret ID, and a Redirect link you're using for your application. Also put in the callback link as the redirect URI and the port ID you'll be using for Resonite
- Run the Python file in a terminal with `./ResoniteSpotipy.py` or run it through an IDE like VSCode

## How to setup the Resonite websocket client
- Spawn out the item from the folder
- Click on the Spotify tab to link up the player to the websocket server
    - Make sure you supply the same port ID as the one you're using for the websocket server!
