#!/bin/sh
# Silent Hill for Anbernic RG DS Plus / ROCKNIXDS (Ports).
# Top screen (DSI-2): the game. Bottom screen (DSI-1): the original inventory, live.
# Your own disc image stays in silent-hill-rgds-plus/gamedata and is not part
# of the distributed package. Only this script and that directory belong to the port.
set -u
. /etc/profile 2>/dev/null || true
PORTS_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
GAMEDIR="${SH_RGDS_GAMEDIR:-$PORTS_DIR/silent-hill-rgds-plus}"
cd "$GAMEDIR" || exit 1

export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/var/run/0-runtime-dir}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
export SWAYSOCK=${SWAYSOCK:-$XDG_RUNTIME_DIR/sway-ipc.0.sock}
export PULSE_SERVER=${PULSE_SERVER:-unix:$XDG_RUNTIME_DIR/pulse/native}
# The SPU output asks SDL for ~20 ms and pipewire-pulse then runs the graph at 256
# frames (5.8 ms): short audio dropouts under load on this console. 60 ms gives a
# 662-frame quantum and less pipewire CPU.
export PULSE_LATENCY_MSEC=${PULSE_LATENCY_MSEC:-60}
export SDL_VIDEODRIVER=${SH_RGDS_VIDEO_DRIVER:-wayland}
export SDL_VIDEO_WAYLAND_WMCLASS=silenthill-rgds
export SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1
export SH_RGDS=1
export SH_RGDS_MENU_FPS=${SH_RGDS_MENU_FPS:-30}
export SH_RGDS_MENU_IDLE_FPS=${SH_RGDS_MENU_IDLE_FPS:-30}
unset SH_RGDS_REFERENCE SH_RGDS_ROLE

RUN_ID=$(date +%Y%m%d-%H%M%S)-$$
STATE="$GAMEDIR/logs/$RUN_ID"
mkdir -p "$STATE" "$GAMEDIR/gamedata/save"
exec >"$STATE/launcher.log" 2>&1
echo "Start: $(date -Iseconds); Anbernic RG DS Plus; state=$STATE"

LOCK="$XDG_RUNTIME_DIR/silent-hill-rgds.lock"
BRIDGE="$XDG_RUNTIME_DIR/silent-hill-rgds-$$.bridge"
GAME_PID=
MENU_PID=
PLACE_PID=
FOCUS=
TOP_POWER=
BOT_POWER=
HAVE_LOCK=

if ! mkdir "$LOCK" 2>/dev/null; then
    OTHER=$(cat "$LOCK/pid" 2>/dev/null || true)
    if [ -n "$OTHER" ] && kill -0 "$OTHER" 2>/dev/null; then
        echo "Already running as pid $OTHER; not starting a second copy"
        exit 1
    fi
    echo "Removing stale lock of pid ${OTHER:-unknown}"
    rm -rf "$LOCK"
    mkdir "$LOCK" || exit 1
fi
HAVE_LOCK=1
echo "$$" >"$LOCK/pid"

sway() {
    swaymsg "$@" >/dev/null 2>&1 || true
}

cleanup() {
    trap - EXIT INT TERM HUP
    if [ -n "$PLACE_PID" ]; then kill "$PLACE_PID" 2>/dev/null || true; fi
    for pid in $GAME_PID $MENU_PID; do
        kill -TERM "$pid" 2>/dev/null || true
    done
    n=0
    while [ "$n" -lt 30 ]; do
        alive=
        for pid in $GAME_PID $MENU_PID; do
            if kill -0 "$pid" 2>/dev/null; then alive=1; fi
        done
        [ -n "$alive" ] || break
        sleep 0.1
        n=$((n + 1))
    done
    for pid in $GAME_PID $MENU_PID; do
        kill -KILL "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    done
    rm -f "$BRIDGE" "$BRIDGE.tmp"
    for log in "$GAMEDIR"/SilentHill_*.log; do
        if [ -f "$log" ]; then mv "$log" "$STATE/" 2>/dev/null || true; fi
    done
    [ "$TOP_POWER" != false ] || sway 'output DSI-2 power off'
    [ "$BOT_POWER" != false ] || sway 'output DSI-1 power off'
    if [ -n "$FOCUS" ]; then sway "[con_id=$FOCUS] focus"; fi
    if [ -n "$HAVE_LOCK" ]; then rm -rf "$LOCK"; fi
    # Keep the last ten runs (BusyBox head has no negative counts).
    runs=$(ls -1d "$GAMEDIR"/logs/*/ 2>/dev/null | wc -l)
    if [ "$runs" -gt 10 ]; then
        ls -1d "$GAMEDIR"/logs/*/ | sort | head -n $((runs - 10)) | while read -r old; do rm -rf "$old"; done
    fi
    echo "End: $(date -Iseconds)"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

# Files copied over MTP or a network share arrive without the executable bit.
[ -f "$GAMEDIR/SilentHillPC" ] && [ ! -x "$GAMEDIR/SilentHillPC" ] && chmod +x "$GAMEDIR/SilentHillPC"
missing=
[ -x "$GAMEDIR/SilentHillPC" ] || missing="$missing SilentHillPC"
[ -d "$GAMEDIR/maps" ] || missing="$missing maps/"
ls "$GAMEDIR"/gamedata/*.cue >/dev/null 2>&1 || ls "$GAMEDIR"/gamedata/*.bin >/dev/null 2>&1 || missing="$missing gamedata/<your disc>.cue+.bin"
if [ -n "$missing" ]; then
    echo "Missing:$missing"
    exit 1
fi

swaymsg -t get_outputs -r >"$STATE/outputs-before.json" 2>/dev/null || true
swaymsg -t get_tree -r >"$STATE/tree-before.json" 2>/dev/null || true
if command -v jq >/dev/null 2>&1; then
    FOCUS=$(jq -r '.. | objects | select(.focused? == true and (.type? == "con" or .type? == "floating_con")) | .id' "$STATE/tree-before.json" 2>/dev/null | head -1)
    TOP_POWER=$(jq -r '.[] | select(.name == "DSI-2") | .power' "$STATE/outputs-before.json" 2>/dev/null)
    BOT_POWER=$(jq -r '.[] | select(.name == "DSI-1") | .power' "$STATE/outputs-before.json" 2>/dev/null)
fi

# Both windows fullscreen on their own panel (Top on DSI-2, Bottom on DSI-1)?
# Every get_tree leaks about 75 KB in sway, so the tree is read rarely and saved
# to the run's log folder.
placed() {
    command -v jq >/dev/null 2>&1 || return 1
    swaymsg -t get_tree -r 2>/dev/null | tee "$STATE/tree-running.json" | jq -e '[.nodes[] | select(.type == "output") | .name as $out
        | .. | objects | select((.name? // "") | startswith("Silent Hill RGDS")) | select(.fullscreen_mode == 1)
        | select((.name == "Silent Hill RGDS [Top]" and $out == "DSI-2") or (.name == "Silent Hill RGDS [Bottom]" and $out == "DSI-1"))]
        | length == 2' >/dev/null 2>&1
}

place_windows() {
    # Only wake a panel that is actually off: re-applying "power on" to a lit
    # panel is not needed.
    [ "$TOP_POWER" != false ] || sway 'output DSI-2 power on'
    [ "$BOT_POWER" != false ] || sway 'output DSI-1 power on'
    # The game creates each window fullscreen on its panel, so normally nothing
    # is left to do. No "focus" either: focusing the top window took both out of
    # fullscreen. Moving and re-fullscreening is only the fallback.
    n=0
    while [ "$n" -lt 6 ]; do
        sleep 2
        if placed; then
            echo "Windows in place"
            return
        fi
        n=$((n + 1))
    done
    echo "Placing windows"
    for pass in 1 2; do
        sway '[title="^Silent Hill RGDS \[Top\]$"] fullscreen disable, move window to output DSI-2, focus, fullscreen enable'
        sway '[title="^Silent Hill RGDS \[Bottom\]$"] fullscreen disable, move window to output DSI-1, fullscreen enable'
        sway '[title="^Silent Hill RGDS \[Top\]$"] focus'
        sleep 1
    done
    swaymsg -t get_tree -r >"$STATE/tree-running.json" 2>/dev/null || true
}

start_menu() {
    SH_RGDS_ROLE=inventory SDL_AUDIODRIVER=dummy ALSOFT_DRIVERS=null \
        ./SilentHillPC -data ./gamedata >>"$STATE/menu.out" 2>&1 &
    MENU_PID=$!
    echo "Menu pid $MENU_PID"
}

export SH_RGDS_BRIDGE="$BRIDGE"
SH_RGDS_ROLE=game ./SilentHillPC -data ./gamedata >>"$STATE/game.out" 2>&1 &
GAME_PID=$!
echo "Game pid $GAME_PID"

# The menu attaches to the world's bridge; starting it only once the world has
# created it also keeps the two processes from reading config.cfg mid-write.
n=0
while [ "$n" -lt 300 ] && [ ! -s "$BRIDGE" ] && kill -0 "$GAME_PID" 2>/dev/null; do
    sleep 0.1
    n=$((n + 1))
done
if ! kill -0 "$GAME_PID" 2>/dev/null; then
    wait "$GAME_PID"
    STATUS=$?
    GAME_PID=
    echo "Game exited before the bridge appeared: $STATUS"
    exit "$STATUS"
fi
start_menu
place_windows &
PLACE_PID=$!

RESTARTS=0
while kill -0 "$GAME_PID" 2>/dev/null; do
    if [ -n "$MENU_PID" ] && ! kill -0 "$MENU_PID" 2>/dev/null; then
        wait "$MENU_PID"
        MENU_STATUS=$?
        MENU_PID=
        if [ "$MENU_STATUS" -ne 0 ] && [ "$RESTARTS" -lt 3 ] && kill -0 "$GAME_PID" 2>/dev/null; then
            RESTARTS=$((RESTARTS + 1))
            echo "Menu exited with $MENU_STATUS; restart $RESTARTS of 3"
            start_menu  # the game opens its window fullscreen on DSI-1 itself
        else
            echo "Menu exited with $MENU_STATUS"
        fi
    fi
    sleep 0.5
done
wait "$GAME_PID"
STATUS=$?
GAME_PID=
echo "Game exit: $STATUS"
exit "$STATUS"
