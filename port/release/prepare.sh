#!/bin/sh
# Silent Hill DS+: puts your own copy of the game into the port folder.
# Put your .bin and .cue (or a .zip with them) into the "game" folder, then run:
#   sh prepare.sh
set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
GAME="$HERE/game"
PORT="$HERE/ports/silent-hill-rgds-plus"
DEST="$PORT/gamedata"
USA_SHA1=34278d31d9b9b12b3b5db5e45bcbe548991ecbc7
WORK="$HERE/game/unpacked"

fail() {
    echo
    echo "$*"
    echo
    exit 1
}

sha1() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 1 "$1" | cut -d' ' -f1
    else
        sha1sum "$1" | cut -d' ' -f1
    fi
}

[ -f "$PORT/SilentHillPC" ] && [ -d "$DEST" ] || fail "I can't find ports/silent-hill-rgds-plus next to this script. Run it from the unpacked release folder."
mkdir -p "$GAME"

# A zipped image is unpacked first.
zips=$(find "$GAME" -maxdepth 1 -type f -iname '*.zip')
if [ -n "$zips" ]; then
    [ "$(printf '%s\n' "$zips" | wc -l)" -eq 1 ] || fail "There is more than one .zip in the game folder. Leave only the one with Silent Hill."
    command -v unzip >/dev/null 2>&1 || fail "unzip is not installed. Unpack the .zip yourself and put the .bin and .cue into the game folder."
    echo "Unpacking $(basename "$zips")..."
    rm -rf "$WORK"
    mkdir -p "$WORK"
    unzip -q -o "$zips" -d "$WORK" || fail "Could not unpack $(basename "$zips")."
fi

bins=$(find "$GAME" -maxdepth 3 -type f -iname '*.bin')
if [ -z "$bins" ]; then
    other=$(find "$GAME" -maxdepth 3 -type f \( -iname '*.chd' -o -iname '*.pbp' -o -iname '*.iso' -o -iname '*.7z' -o -iname '*.rar' \) | head -1)
    [ -z "$other" ] || fail "$(basename "$other") can't be used as it is. The game needs a BIN/CUE image. A CHD can be converted with chdman: chdman extractcd -i \"Silent Hill (USA).chd\" -o \"Silent Hill (USA).cue\""
    fail "No game found. Put your Silent Hill .bin and .cue (or a .zip with them) into the game folder and run this again."
fi
[ "$(printf '%s\n' "$bins" | wc -l)" -eq 1 ] || fail "There is more than one .bin in the game folder. Leave only your Silent Hill image."
bin=$bins
name=$(basename "$bin")
name=${name%.*}

echo "Checking $name.bin..."
if [ "$(sha1 "$bin")" = "$USA_SHA1" ]; then
    echo "This is the North American disc (SLUS-00707 v1.1)."
else
    echo "This is another version of the disc. The port is made for the North American disc (SLUS-00707 v1.1)."
fi

echo "Copying it into the port folder..."
for old in "$DEST"/*; do
    case $old in
        *.bin|*.BIN|*.cue|*.CUE) rm -f "$old" ;;
    esac
done
if [ -d "$WORK" ]; then
    mv "$bin" "$DEST/$name.bin" || fail "Could not copy the game. Is there enough free space?"
    rm -rf "$WORK"
else
    cp "$bin" "$DEST/$name.bin" || fail "Could not copy the game. Is there enough free space?"
fi
printf 'FILE "%s.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n' "$name" >"$DEST/$name.cue"
mkdir -p "$DEST/save"
chmod +x "$HERE/ports/SilentHill.sh" "$PORT/SilentHillPC"

echo
echo "Done. Now copy everything inside the ports folder into roms/ports on your console,"
echo "restart the console and start SilentHill from Ports."
echo
