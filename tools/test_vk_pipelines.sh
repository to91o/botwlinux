#!/bin/sh
# GPU test of the Vulkan shader path (tools/test_vk_pipelines.c): fuzzed Maxwell programs -> GLSL -> the
# backend's compile/reflection/layouts -> real pipelines on the device, under the validation layer if present.
# usage: tools/test_vk_pipelines.sh [count] [seed]      (Windows / MSYS2 ucrt64)
set -e
cd "$(dirname "$0")/.."
OUT=build/test_vk_pipelines
mkdir -p "$OUT"
CC=${CC:-clang}
case "$(uname -s)" in
    Linux) VK_LIB=-lvulkan; SHADERC=${SHADERC:-$(pkg-config --libs shaderc)} ;;
    *) VK_LIB=-lvulkan-1; SHADERC=${SHADERC:--lshaderc_shared} ;;
esac
make "$OUT/inc/smaa_hlsl.inc" B="$OUT"
# SHADERC is intentionally split into linker arguments from pkg-config.
$CC -O2 -w -Iruntime -Iruntime/nvn -I"$OUT/inc" -Ithird_party/smaa/Textures -D_FILE_OFFSET_BITS=64 tools/test_vk_pipelines.c runtime/nvn/maxwell/translate.c \
    runtime/nvn/vulkan/shaders.c runtime/nvn/smaa_data.c -o "$OUT/test_vk_pipelines" "$VK_LIB" $SHADERC
# the MSYS2 validation layer manifest lives next to its DLL
for d in /ucrt64/bin /c/msys64/ucrt64/bin; do
  [ -f "$d/VkLayer_khronos_validation.json" ] && export VK_ADD_LAYER_PATH="$(cygpath -w "$d")"
done
"$OUT/test_vk_pipelines" runtime/nvn/maxwell/translate.c "${1:-2000}" "${2:-1}"
