#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
# Reproducible builds: the build stamp compiled into the game is the pinned upstream commit time.
epoch=${SOURCE_DATE_EPOCH:-$(git -C "$root/silent-hill/upstream" log -1 --format=%ct)}
docker run --rm --network none --platform linux/arm64 \
    --mount "type=bind,src=$root,dst=/work" \
    -e SOURCE_DATE_EPOCH="$epoch" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory \
    -e GIT_CONFIG_VALUE_0=/work/silent-hill/upstream \
    rgds-silent-hill-builder:ubuntu24.04 sh -c '
        cmake -S pc_port -B ../build/arm64 -G Ninja \
          -DCMAKE_BUILD_TYPE=Release -DSH_RGDS=ON -DSH_BUILD_MAP_DLLS=ON \
          -DSH_FMV_FFMPEG=OFF -DSH_ENABLE_RETROACHIEVEMENTS=OFF
        cmake --build ../build/arm64 -j4
    '
