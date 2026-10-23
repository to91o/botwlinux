#!/usr/bin/env bash
# Savage Wind on Arch Linux / CachyOS in one step: builds the launcher from this checkout as a pacman
# package (tools/arch/pkg-src/PKGBUILD) and installs it. Afterwards: `savagewind`, or Savage Wind in
# the app menu. Remove with `sudo pacman -R savagewind` (your game files and saves in
# ~/.local/share/savagewind stay).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

command -v pacman >/dev/null || { echo 'This installer is for Arch Linux and Arch-based systems (CachyOS, EndeavourOS, ...).' >&2; exit 1; }
[ "$(id -u)" -ne 0 ] || { echo 'Run this as your normal user, not with sudo: it asks for your password when it needs it.' >&2; exit 1; }
[ "$(uname -m)" = x86_64 ] || { echo 'Only x86-64 is supported here.' >&2; exit 1; }
grep -qw avx2 /proc/cpuinfo || { echo 'Savage Wind needs a CPU with AVX2.' >&2; exit 1; }

echo '==> Build tools'
sudo pacman -S --needed base-devel git

# A Vulkan driver for the GPU, when none is installed. NVIDIA's must match its kernel module, so it is
# only pointed out, not installed.
if ! compgen -G '/usr/share/vulkan/icd.d/*.json' >/dev/null; then
    drivers=()
    for v in /sys/class/drm/card*/device/vendor; do
        case $(cat "$v" 2>/dev/null) in
            0x1002) drivers+=(vulkan-radeon) ;;
            0x8086) drivers+=(vulkan-intel) ;;
            0x10de) echo 'NVIDIA GPU: install the nvidia-utils that matches your NVIDIA kernel driver.' ;;
        esac
    done
    if [ ${#drivers[@]} -gt 0 ]; then
        echo '==> Vulkan driver'
        sudo pacman -S --needed "${drivers[@]}"
    fi
fi

echo '==> Building and installing Savage Wind (several minutes)'
cd tools/arch/pkg-src
makepkg -sicf
cat <<'MSG'

Installed. Start Savage Wind from your app menu or with:  savagewind
The first start asks for the folder with your own extracted game files (version 1.8.2: exefs and romfs).
Settings and game files later:  savagewind --config
MSG
