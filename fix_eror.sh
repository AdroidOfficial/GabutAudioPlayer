#!/bin/bash

echo "📦 Memulai instalasi dependency..."

# Cek apakah python3 dan pip sudah terinstal
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 tidak ditemukan. Silakan install Python3 terlebih dahulu."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 tidak ditemukan. Silakan install python3-pip terlebih dahulu."
    exit 1
fi

# Instal library Python dari requirements.txt
if [ -f "requirements.txt" ]; then
    echo "🔧 Menginstal library Python..."
    pip3 install -r requirements.txt
else
    echo "⚠️ File requirements.txt tidak ditemukan!"
    echo "🔧 Menginstal library secara manual..."
    pip3 install PyQt5 python-vlc
fi

# Instal VLC sistem (Ubuntu/Debian)
echo "🎬 Menginstal VLC Media Player..."
sudo apt update && sudo apt install -y vlc

echo "✅ Instalasi selesai!"
echo "🔊 Kamu bisa menjalankan aplikasi dengan:"
echo "   python3 main.py"
