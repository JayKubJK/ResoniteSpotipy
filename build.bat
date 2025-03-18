python -m PyInstaller -F ResoniteSpotipy.py
tar -a -c -f ResoniteSpotipy.zip IDs.txt -C dist ResoniteSpotipy.exe