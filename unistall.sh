#!/bin/bash
APP_NAME="gabutaudioplayer"

# Hapus paket
sudo dpkg -r $APP_NAME

# Hapus ikon & konfigurasi
sudo rm -rf /usr/share/gabutaudioplayer
sudo rm -f /usr/share/applications/gabutaudioplayer.desktop
rm -rf ~/.config/gabutaudioplayer
rm -rf ~/.cache/gabutaudioplayer

echo "$APP_NAME telah dihapus sepenuhnya dari sistem."