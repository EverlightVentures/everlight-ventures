#!/bin/bash
# Music Downloader Script for MPD

# Check if URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <YouTube URL>"
    exit 1
fi

# Set download directory
MUSIC_DIR=~/Music

# Download and convert to MP3
echo "Downloading and converting to MP3..."
yt-dlp -x --audio-format mp3 -o "$MUSIC_DIR/%(title)s.%(ext)s" "$1"

# Update MPD library
echo "Updating MPD library..."
mpc update

echo "Download complete! Music is ready in MPD."

