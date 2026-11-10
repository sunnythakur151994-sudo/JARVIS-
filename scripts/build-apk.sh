#!/bin/bash
# Build the JARVIS Music Shorts Factory Android APK.
# Toolchain (all offline in tools/):
#   - apktool 2.9.3   : assembles manifest + smali + resources into an APK
#   - apksigner       : signs (v1 + v2 + v3) with a generated debug keystore
#   - keytool (JDK)   : creates the keystore
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/tools"
JAVA="$TOOLS/ext/jdk4py/jdk4py/java-runtime/bin/java"
KEYTOOL="$TOOLS/ext/jdk4py/jdk4py/java-runtime/bin/keytool"
APKTOOL="$TOOLS/npmpk/postar-pkg/lib/apktool.jar"
APKSIGNER="$TOOLS/npmpk/postar-pkg/lib/apksigner.jar"
PROJ="$ROOT/apps/mobile/apkproj"
DIST="$ROOT/dist"
KS="$TOOLS/debug.keystore"

# keep the app UI in sync with the shared dashboard
cp "$ROOT/apps/ui/index.html" "$PROJ/assets/www/index.html"

# wheel extraction strips exec bits; the JVM needs jspawnhelper executable to run aapt2
chmod +x "$TOOLS/ext/jdk4py/jdk4py/java-runtime/lib/jspawnhelper" 2>/dev/null || true
chmod -R +x "$TOOLS/ext/jdk4py/jdk4py/java-runtime/bin" 2>/dev/null || true

mkdir -p "$DIST"

if [ ! -f "$KS" ]; then
  echo "== generating debug keystore =="
  "$KEYTOOL" -genkeypair -v -keystore "$KS" -storepass android \
    -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 \
    -validity 10000 -dname "CN=JARVIS Music Shorts Factory, OU=Apps, O=JARVIS, C=IN"
fi

echo "== assembling APK (apktool) =="
"$JAVA" --enable-native-access=ALL-UNNAMED -jar "$APKTOOL" b "$PROJ" \
  -o "$DIST/JARVIS-MusicShortsFactory-unsigned.apk" -f

echo "== signing (apksigner) =="
"$JAVA" --enable-native-access=ALL-UNNAMED -jar "$APKSIGNER" sign \
  --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias androiddebugkey --min-sdk-version 24 \
  --out "$DIST/JARVIS-MusicShortsFactory.apk" \
  "$DIST/JARVIS-MusicShortsFactory-unsigned.apk"

echo "== verifying =="
"$JAVA" --enable-native-access=ALL-UNNAMED -jar "$APKSIGNER" verify \
  --print-certs --verbose "$DIST/JARVIS-MusicShortsFactory.apk" | head -20

ls -la "$DIST/JARVIS-MusicShortsFactory.apk"
echo "== APK build done =="
