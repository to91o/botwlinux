# Arch Linux: native build and Proton fallback

This is SavageWind 0.2.0-alpha.2, including its existing Linux Vulkan backend.
It is an alpha: building the launcher does not establish full-game correctness.
The upstream README reports that only the opening and Great Plateau have been
tested on Windows, and Linux gameplay for this game is untested.

## AppImage (single executable)

`Savage_Wind-0.2.0-alpha.2-x86_64.AppImage` is the launcher as one file. It
bundles SDL3, FFmpeg, shaderc, the frozen game-code generator (`swgen`) and Zig,
so game-file setup needs no Python, clang or source checkout. Only glibc,
libstdc++, the Vulkan loader and your GPU driver come from the system:

```sh
sudo pacman -S --needed fuse3 vulkan-icd-loader vulkan-radeon   # or vulkan-intel / nvidia-utils
chmod +x Savage_Wind-0.2.0-alpha.2-x86_64.AppImage
./Savage_Wind-0.2.0-alpha.2-x86_64.AppImage            # first run: game-file setup
./Savage_Wind-0.2.0-alpha.2-x86_64.AppImage --config   # configuration screen
```

Build it yourself with `make appimage` (needs podman; it builds in Ubuntu 22.04
containers so the result runs on glibc 2.35+).

## Native Linux (preferred)

For the Ryzen 9600X + RX 6900 XT desktop, install Mesa RADV:

```sh
sudo pacman -Syu --needed mesa vulkan-radeon
```

For a Core Ultra 5 laptop using its integrated Intel GPU:

```sh
sudo pacman -Syu --needed mesa vulkan-intel
```

If the laptop has a separate GPU, choose the driver for the GPU you run on.
Both CPUs support AVX2. The renderer requires Vulkan 1.3; check the actual GPU:

```sh
vulkaninfo --summary
bash tools/arch/setup.sh
bash tools/arch/run.sh --config
```

Run these from a graphical desktop. Setup installs build dependencies, builds
the native runtime with four jobs (override with JOBS), and runs synthetic module
tests. SDL >= 3.4 is required: this release uses SDL_LoadPNG despite the older
minimum in docs/linux.md. No Proton is needed for this native executable.
Vulkan headers >= 1.4.350 are required by the current renderer. The installer
uses shaderc's pkg-config linker flags to handle Arch's shared-library name.
Vulkan Memory Allocator is downloaded from its pinned upstream v3.3.0 archive,
SHA-256 verified, and extracted under the ignored `build/arch-deps` directory.
No `vulkan-memory-allocator` pacman package or AUR helper is required.

In Configuration select the folder containing your extracted Breath of the Wild
1.8.2 files: exefs (main, main.npdm, rtld, sdk, subsdk0) and the merged romfs.
The launcher builds the game library locally. Allow substantial time and at least
35 GB free space. These game files are not included in this source release.

Launch again with `bash tools/arch/run.sh`. Data normally lives in
`~/.local/share/savagewind` (or `$XDG_DATA_HOME/savagewind`). An `extracted/`
directory in the source root selects portable development mode, which stores
data there instead. Keep this source directory: the launcher needs its generator,
Python environment and runtime headers to build your game library.

Validate on each PC: configuration window, game-file setup, boot into gameplay,
graphics and audio, controller input, save/load, and a restart. Record the terminal
output and GPU/driver details for failures. A working opening does not prove the
rest of the game works. DLC is unsupported upstream.

## Windows release through Steam Proton (fallback; unverified)

Use your original Windows release ZIP, extracted completely to a writable folder
on a Linux filesystem. Add savagewind.exe as a non-Steam game in Steam, set its
Start In directory to that extracted folder, and force Proton Experimental in
Compatibility. Start it and select your extracted game files. Keep all bundled
DLLs, the swgen directory, and the zig directory together with the executable.

For RADV install `lib32-vulkan-radeon` and `lib32-mesa` as well; for Intel use
`lib32-vulkan-intel` and `lib32-mesa` (Arch multilib must be enabled for Steam).
Use `PROTON_LOG=1 %command%` as Steam's launch options to collect a Proton log.
The game-data picker sees Linux files under Wine's Z: drive. Do not share generated
Windows DLLs with the native Linux build: each platform needs its own game library.

This fallback has not been tested here: the Windows upload exceeds the cloud
transfer limit, and this machine has neither Steam nor a hardware GPU. Do not
assume a particular Proton version resolves an untested application defect.
