#!/bin/bash
# Einmal pro neuer Sitzung ausfuehren: installiert alles, was das Studio braucht.
set -e
cd "$(dirname "$0")/studio"
pip install --break-system-packages -q pycairo numpy kokoro-onnx pillow
mkdir -p ~/.fonts modelle
[ -f ~/.fonts/LilitaOne-Regular.ttf ] || curl -sSLf -o ~/.fonts/LilitaOne-Regular.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/lilitaone/LilitaOne-Regular.ttf
fc-cache -f
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -f modelle/$f ] || curl -sSLf -o modelle/$f https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f
done
python3 motojumper_studio.py --liste
