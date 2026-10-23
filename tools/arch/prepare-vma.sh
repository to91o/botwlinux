#!/usr/bin/env bash
# VMA is header-only. Use the project's pinned upstream archive rather than
# requiring a distribution-specific package (not available in all Arch repos).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
deps="$PWD/build/arch-deps"
archive="$deps/VulkanMemoryAllocator-3.3.0.tar.gz"
mkdir -p "$deps/include/vma"
download=''
header=''
trap 'rm -f -- "${download:-}" "${header:-}"' EXIT
if [[ ! -f "$archive" ]]; then
    download=$(mktemp "$deps/vma-download.XXXXXX")
    curl --fail --location --retry 2 --connect-timeout 15 \
        https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator/archive/refs/tags/v3.3.0.tar.gz \
        --output "$download"
    echo "c4f6bbe6b5a45c2eb610ca9d231158e313086d5b1a40c9922cb42b597419b14e  $download" | sha256sum --check
    mv -- "$download" "$archive"
    download=''
fi
echo "c4f6bbe6b5a45c2eb610ca9d231158e313086d5b1a40c9922cb42b597419b14e  $archive" | sha256sum --check
header=$(mktemp "$deps/include/vma/vk_mem_alloc.XXXXXX")
tar -xOf "$archive" VulkanMemoryAllocator-3.3.0/include/vk_mem_alloc.h > "$header"
mv -- "$header" "$deps/include/vma/vk_mem_alloc.h"
header=''
