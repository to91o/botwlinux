# Experimental 1.9 support and performance controls

The 1.9 main build ID is recognized separately from the 1.8.2 hook layout. Set
`SAVAGEWIND_EXPERIMENTAL_19=1` to enable the experimental launcher path. Fixed-address
1.8.2 patches and variable-frame-rate writes are disabled for this version; native
30 fps pacing is retained. F1 opens runtime settings and F11 toggles fullscreen.
This remains experimental: broader gameplay and compatibility testing are unfinished.
Use your own game files and keys; none are distributed here.

## Graphics

Video settings expose Low, Balanced, High, Ultra and derived Custom presets,
50–150% scene render scale and FSR sharpening. Presets preserve the display mode,
frame limit and controls. HUD resolution is preserved. Slider tracks support mouse
dragging alongside keyboard/gamepad stepping. For a USB DualSense that SDL detects
but does not read correctly, the tested Linux workaround is
`SDL_JOYSTICK_HIDAPI_PS5=0`.

## Optional compiler mode

With matching Clang/LLVM 23 development files and llvm-config available:

```sh
make B=build/bounded BOUNDED_CODEGEN=1 GEN=generated
```

Use the normal dependency options for your platform. This mode was tested on Linux
x86-64; it is not a cross-platform promise. The LLVM plugin skips optional loop passes,
retains scalar O2 optimization, disables SLP vectorization and bounds backend work
for functions above 128 blocks or 5000 IR instructions. Smaller functions retain
optimized register allocation. Use a separate build directory when changing modes.
The matching executable and swgame library must remain together. Default compiler
mode is unchanged. Never commit generated game code or the game library.

## Linux CPU sampling and integration diagnostics

`SAVAGEWIND_LINUX_SAMPLE=60:20:1000` samples instruction pointers after 60 seconds
for 20 seconds, at a requested 1000 microsecond CPU-time interval. Set
`SAVAGEWIND_LINUX_SAMPLE_OUT` to choose the output path, then run
`python tools/profile_linux_samples.py PATH`. Counts are self CPU samples, not wall
time or a call graph. Sampling is opt-in, Linux x86-64/aarch64 only, and should be
disabled during performance benchmarks.

`SAVAGEWIND_TEST_INPUT_FILE` optionally reloads the existing integration-input syntax
from a local file each frame. `FRAME:SHOT:1` requests a screenshot. Normal launches
leave these test variables unset.

## Import dependency

The source-only patch `tools/patches/hactool-bktr-trailing-data.patch` was tested
against hactool commit `1d64a834` to read the tested update's bounded trailing BKTR
section data. Apply it to a separate hactool checkout, build it there and select that
binary with `SAVAGEWIND_HACTOOL`. The system hactool need not be replaced. Imported
NSO segment hashes were verified in the local test; no decrypted files are included.

## Validation and current limits (2026-10-24)

Python NSP tests: 19 passed. Layout checks: 55 passed. Native graphics settings tests
cover preset selection, persistence, scene-only scaling and invalid/empty values.
Run `bash tools/test_graphics.sh` on Linux to repeat these native tests.
The headless ImGui test covers dragging, snapping, release and disabled sliders.
A synthetic Linux sampler test attributed 99.6% of samples to its known hot function.

On a Core Ultra 5 125H / Intel Arc laptop on AC with the performance power profile,
the previous scalar O1 build reached 30.00 fps in a stationary outdoor Low-preset
sample, but actual movement/camera testing averaged 29.78 fps. A sustained minimum
30 fps across gameplay is therefore not yet established. Initial O0 testing was
about 16.8 fps under power-saver and 20 fps under the performance profile. These are
local observations, not hardware guarantees. Continue with repeated outdoor movement,
heavier views and save/reload testing before treating the performance goal as complete.

The optional bounded O2 build linked a 240 MB library versus 412 MB for the prior
scalar O1 build and successfully loaded the outdoor save. Its final scripted route
fell from a ledge and reached Game Over, so the run is not a valid sustained gameplay
comparison. The previously tested build remains the user's launcher default. A fair
repeated route, with screenshots confirming safe gameplay throughout, is next.
