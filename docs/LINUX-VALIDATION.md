# Validation of the Arch preparation

Source: uploaded SavageWindRecomp-0.2.0-alpha.2.zip, archive comment commit
ad95614c2c90fc29f4a1ea40de38a70896666e15. This is a local import into the
previously empty botwlinux checkout. The release adds Arch setup instructions
and fixes the Vulkan pipeline test harness; it does not establish full gameplay.

Test host: Debian 13 x86-64, Clang 19, SDL 3.4.16, Vulkan headers 1.4.350.1,
Mesa 25.0.7 llvmpipe (software rendering), Xvfb. SDL and Vulkan header archives
were checked against the SHA-256 hashes pinned in tools/linux/build_deps.sh.
Dependencies were extracted into a workspace prefix because system installation
is unavailable on this cloud host. The prefix is a cloud-only setup, excluded
from the source distribution.

Passed:

- Native runtime compile and link with the existing Linux backend.
- Actual launcher startup and 1280x720 screenshot through Vulkan on Xvfb.
- Synthetic module layout: 55 checks.
- Portable SIMD differential test: validity scan of 1,048,640 encodings, followed
  by 200 sampled valid encodings and 800 execution cases, zero mismatches.
- Vulkan pipeline fuzz test: 29 graphics pairs, 19 compute programs, zero
  failures; 52 generated cases skipped because translation failed. Khronos
  validation layers were unavailable; zero validation messages is not evidence
  of a validation-layer pass.
- Syntax checks of Arch setup/launch scripts and the pipeline test shell script.
- Arch installer correction: download and SHA-256 verification of the pinned
  VMA 3.3.0 archive, a second cached run, and compilation of the Vulkan allocator
  implementation against the resulting local header. This avoids the unavailable
  `vulkan-memory-allocator` package reported on CachyOS.

Changes beyond the uploaded source:

- tools/arch/setup.sh and run.sh plus docs/ARCH.md for a native Arch workflow.
- Pipeline test: choose Linux's Vulkan and shaderc linker flags, include the
  existing SMAA source, and provide the test harness's missing device-loss hook.
  No renderer or gameplay assertions were disabled to get a pass.

Not verified: execution of pacman or the setup script on Arch; AMD/Intel hardware
rendering; game-code generation from real game files; gameplay, audio, input or
save/load; Steam/Proton. The uploaded Windows ZIP exceeded the file transfer
limit and was not inspected. The Linux runtime still has upstream compiler
warnings. This work does not certify full-game functionality of the alpha.

Next required input: extracted Breath of the Wild 1.8.2 exefs and merged romfs
available on a target PC, followed by the functional checks in docs/ARCH.md.

## Launcher theme update

The native runtime was rebuilt after the UI changes. The main configuration,
game-file setup and settings screens were rendered and inspected on software
Vulkan at 1280x720; game-file setup was also inspected at 800x600. This verifies
the new launcher layout and rendering. The shared in-game settings palette and
frame compile, but their appearance over real gameplay is not yet verified.
The panorama and ornaments use original vector geometry. Existing user splash
images still take precedence. No game assets are distributed with the theme.

## Launcher executable on Arch

Built in an Arch Linux rootfs (official bootstrap, packages current on
2026-10-23: SDL 3.4.18, Vulkan headers 1.4.363, shaderc 2026.4.1, clang):
the `tools/arch/setup.sh` steps compiled `build/savagewind` with no errors and
`tools/test_layout.py` passed 55 checks. `build/savagewind --config` ran on
Xvfb with Mesa lavapipe and drew the Game Files screen.

`make appimage` produced `Savage_Wind-0.2.0-alpha.2-x86_64.AppImage` (85 MB).
Run in the same Arch rootfs, it showed the first-run Welcome screen through
Vulkan (log: llvmpipe, Vulkan 1.4), and its bundled `zig` (0.17.0) and `swgen`
generator executed. Before this, the AppImage build failed at once: the source
import had dropped the executable bit from every tools script.

Not verified: setup with real game files, gameplay, hardware GPUs, FUSE mount
(run with `--appimage-extract-and-run` in the test chroot).

Because AppImages need FUSE and are unreliable on some Arch setups, the same
files also ship as a plain folder (tar.gz) and as an Arch package
(`tools/arch/pkg/PKGBUILD`). In the Arch rootfs, `makepkg` built
`savagewind-bin-0.2.0alpha2-1`, `pacman -U` installed it, and as an unprivileged
user both the installed `savagewind` command and the extracted folder drew the
launcher through Vulkan (llvmpipe), with the data folder created under
`~/.local/share/savagewind`.

## One-command install

`install-arch.sh` was run end to end in the Arch rootfs as a fresh unprivileged
user with passwordless sudo, accepting default answers: it installed base-devel
and git, built `savagewind-0.2.0alpha.2-1` from the checkout and installed it
(282 MiB, mostly Zig). As that user, `savagewind` drew the Welcome screen
through Vulkan (llvmpipe), the installed `swgen` ran, and the installed
`zig cc -march=x86_64_v3` compiled and ran a C program. `pacman -R savagewind`
removed `/opt/savagewind` and `/usr/bin/savagewind` and kept the data folder.
The Vulkan-driver step was not exercised (no GPU in the test host).
