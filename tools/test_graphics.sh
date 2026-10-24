#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test_dir=$(mktemp -d)
trap 'rm -rf -- "$test_dir"' EXIT
"${CC:-clang}" -O2 -ffunction-sections -fdata-sections -Iruntime   tools/test_graphics_settings.c runtime/settings.c runtime/language.c runtime/nvn/output_scale.c   -Wl,--gc-sections -lm -o "$test_dir/settings"
SAVAGEWIND_SETTINGS="$test_dir/settings.ini" "$test_dir/settings"
"${CXX:-clang++}" -O2 -ffunction-sections -fdata-sections -Ithird_party/imgui -Iruntime -x c++   tools/test_graphics_slider.cpp runtime/ui/option_rows.mm third_party/imgui/imgui.cpp   third_party/imgui/imgui_draw.cpp third_party/imgui/imgui_tables.cpp third_party/imgui/imgui_widgets.cpp   -Wl,--gc-sections -o "$test_dir/slider"
"$test_dir/slider"
