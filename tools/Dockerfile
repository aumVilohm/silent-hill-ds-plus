FROM --platform=linux/arm64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git pkg-config python3 python3-pip python3-venv \
    libsdl2-dev libopenal-dev libjpeg-dev libgl1-mesa-dev libgles2-mesa-dev \
    libegl1-mesa-dev libcurl4-openssl-dev libwayland-dev wayland-protocols \
    ca-certificates binutils file zip unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work/silent-hill/upstream
