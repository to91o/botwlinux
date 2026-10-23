#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
command -v pacman >/dev/null || { echo 'Run this installer on Arch Linux or an Arch derivative.' >&2; exit 1; }
# Use a full upgrade: partial upgrades are unsupported on Arch.
sudo pacman -Syu --needed base-devel clang lld pkgconf python sdl3 ffmpeg vulkan-headers vulkan-icd-loader vulkan-memory-allocator shaderc vulkan-tools ttf-dejavu
pkg-config --atleast-version=3.4.0 sdl3 || { echo 'SDL >= 3.4 is required (SDL_LoadPNG). Update Arch first.' >&2; exit 1; }
pkg-config --atleast-version=1.4.350 vulkan || { echo 'Update vulkan-headers to >= 1.4.350; older headers lack required extension declarations.' >&2; exit 1; }
python -m venv tools/venv
tools/venv/bin/python -m pip install 'lz4==4.4.5' 'capstone==5.0.9' 'unicorn==2.1.4'
make -j"${JOBS:-4}" SHADERC="$(pkg-config --libs shaderc)"
tools/venv/bin/python tools/test_layout.py
echo 'Built. Install the Vulkan driver described in docs/ARCH.md, then run tools/arch/run.sh.'
