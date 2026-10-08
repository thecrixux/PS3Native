<div align="center">

# DukePS3

**PlayStation 3 emulation for Android — built on RPCS3, tuned through real-device testing.**

![Version](https://img.shields.io/badge/Version-1.0.0-FFB800?style=flat-square)
![Android](https://img.shields.io/badge/Android-12%2B-18181B?style=flat-square&logo=android&logoColor=FFB800)
![Architecture](https://img.shields.io/badge/Architecture-ARM64-18181B?style=flat-square)
![Renderer](https://img.shields.io/badge/Renderer-Vulkan-18181B?style=flat-square)
![Frame generation](https://img.shields.io/badge/Frame_Generation-LSFG_%2B_DIS-FF8A00?style=flat-square)

[Releases](https://github.com/thecrixux/DukePS3/releases) · [Source code](https://github.com/thecrixux/DukePS3)

</div>

DukePS3 is an Android-focused fork of [RPCS3](https://github.com/RPCS3/rpcs3), developed from PS3Native and the original RPCS3-Android port. Its priorities are **compatibility, stability, frame pacing and practical performance on both Snapdragon/Adreno and MediaTek/Mali**.

The RPCS3 core and Android front end live in the same source tree. Upstream improvements are merged alongside Android-specific fixes and a Compose Material 3 interface with DukePS3's own identity.

## What DukePS3 offers

| Area | Features |
| --- | --- |
| **Emulation** | Vulkan rendering, LLVM-based PPU/SPU recompilers and reusable compilation caches. |
| **Frame generation** | Two Vulkan engines: proprietary Lossless Scaling shaders through LSFG, or built-in, free DIS optical flow. |
| **Games and settings** | Searchable library, compatibility browser, global/per-game settings, game-update sources and patch management. |
| **Graphics and drivers** | Separate PS3 video mode and internal render scale; custom driver import and driver repositories where supported. |
| **Playing** | Editable on-screen controls and an in-game menu with pause/resume, settings and shutdown. |
| **Performance tools** | Customizable HUD, frame-time graph, separate game and output FPS, and exportable benchmark captures. |
| **Audio and diagnostics** | Automatic/AAudio/OpenSL ES output selection, log sharing, system information and WAV + log export. |
| **Interface** | Duke Gold dark theme, illustrated welcome screen, branded navigation menu and adaptive/themed launcher icons. |

## Recent improvements

- **Faster first-start PPU preparation:** duplicated directory scans and executable checks are avoided. LLVM worker creation respects the existing memory budget, and compilation stages now report their timings. Faster starts have been reported in device testing; the saving depends on the game and cache state.
- **Reusable caches:** later launches keep using previously compiled modules instead of rebuilding them unnecessarily.
- **Graphics fixes:** corrections for corrupted rendering after upstream updates, plus a clearer distinction between the game's video mode and internal resolution scaling.
- **More detail on Mali:** G-Force has been tested with a 720p video mode and 150% render scale, retaining a reported 60 FPS in the reference scene.
- **Smoother free frame generation:** DIS incorporates adapted OpenFlow optimizations, with improvements to its Vulkan presentation path and frame pacing. G-Force's perceived smoothness improved in Adreno 710 testing after these changes.
- **Better measurements:** improved FPS/frame-time sampling, a separate `OUT` presentation-rate indicator and benchmark exports that exclude generated frames from the game-FPS measurement.
- **Loading-screen artwork restored:** the game's background image now appears during module preparation instead of a black background.
- **MediaTek audio improvements:** producer-side changes substantially reduced intermittent artifacts on the Dimensity 8300 test device. A small residual issue remains pending.
- **Easier troubleshooting:** benchmark archives contain `summary.json` and `frames.csv`; audio capture export packages the latest completed WAV with the current log.

## Tested on real hardware

G-Force is the current reference game, tested repeatedly in the same scene by the maintainer.

| Device | Reported results |
| --- | --- |
| **Snapdragon / Adreno 710** | Around **35–42 game FPS at native resolution** in the reference tests; improved smoothness with the optimized DIS engine. Audio reported clean. |
| **POCO X6 Pro / Dimensity 8300 / Mali** | Around **60 game FPS in the reference scene**, including testing at **720p + 150% render scale**. Previous resolution-related corruption was resolved in that test. |

These are observations from specific builds, settings and one game, rather than a compatibility guarantee for every title or device. Game FPS and frame-generated output FPS are different measurements. Drivers, available memory and thermal conditions affect the results. LSFG integration is available, but it was not part of these maintainer tests because the proprietary shaders were not available.

## Frame generation: choose your engine

| Engine | What you need | What is included |
| --- | --- | --- |
| **DIS — Dense Inverse Search** | A compatible GPU/driver. **No purchase or DLL required.** | The free optical-flow engine and its shaders are built into the app. |
| **LSFG — Lossless Scaling** | Your own licensed copy of Lossless Scaling and a compatible `Lossless.dll`. | Vulkan integration and shader-import tools. **The proprietary DLL/shaders are not distributed.** |

Open **Frame Gen** from the library menu or the in-game menu. Select the engine, choose a preset and enable generation. DIS provides **Light, Fast, Balanced and Quality** presets; both engines expose multipliers **2×/3×/4×** or target rates **60/90/120 FPS**.

LSFG imports shader data from the DLL, translates it when required and caches it locally. The DLL is parsed as data, not executed.

Frame generation can improve visual smoothness, but it adds GPU work and latency. A higher output number does not increase the game's simulation speed or guarantee better responsiveness. The HUD's `OUT` indicator reports presentation rate, including real and interpolated frames; it is not a count of generated frames alone.

The built-in DIS engine comes from the work of **qwertypower (DEVAR Entertainment LLC)** in WinNative, now named **OpenFlow**, with roots in OpenCV's DISOpticalFlow and Till Kroeger's OF_DIS. We adapt its optimizations to RPCS3's Vulkan renderer; the hardware motion-estimation path is not included. See the [full credits and source lineage](#credits) at the end of this page.

## Getting started

1. Install the APK and complete storage access and firmware setup. **Games and PS3 firmware are not included.**
2. Add a game folder, boot a disc image or install a package using the library tools.
3. Start with the default graphics settings. To test higher detail, keep **PS3 video mode at 720p** and adjust **Render scale**. At a 1280×720 base, 150% corresponds to 1920×1080; actual scaling depends on the game and its surfaces.
4. Try DIS from **Frame Gen** if you want the built-in free engine, then compare the same scene with generation disabled and enabled.

**Requirements:** Android 12 or newer, an ARM64 device with the CPU features required by the build, and a compatible Vulkan driver. The current CPU check covers LSE atomics, FP16, RDM and dot-product support. Available RAM influences how many compilation workers can run at once.

**Package:** `com.crixux.dukeps3` · **App version:** `1.0.0`.

Changing from the old PS3Native package creates a separate Android installation. Existing saves, firmware, caches and private preferences are not migrated automatically; keep the old app until any needed data has been copied and checked.

## Measure and report

The HUD can show FPS, frame times, RAM and supported device sensors. A sensor that the device/driver does not expose may show `N/A`.

For useful comparisons, keep the game, scene, settings and temperature conditions consistent. Benchmark captures record **RSX flip intervals**, exclude loading/pauses and generated frames, and export a JSON summary plus CSV frame timings. For first-start testing, distinguish a PPU rebuild from a later cached launch.

To investigate sound, enable **Dump to file**, reproduce the problem, stop the game normally and use **Debug → Export audio capture**. This exports the completed WAV and current log. Leave dumping disabled for normal play when a capture is not needed.

Reports are most useful with the game/title ID, device, driver, settings, reproduction steps and a log or benchmark archive.

## Pending work

- Expand compatibility testing beyond G-Force.
- Resolve the small residual audio artifacts on MediaTek.
- Continue checking driver and frame-generation engine availability across different GPUs.
- RPCN still has no Android sign-in interface; end-to-end netplay is not verified.

## Build from source

The build uses **JDK 17, Android SDK 35, NDK 29.0.14206865 and CMake 3.31.6**, with LLVM and FFmpeg prepared for `arm64-v8a`.

From the repository root, in an environment that can run the Bash scripts:

```bash
git submodule update --init --recursive
cd android
./build-ffmpeg-android.sh
./build-llvm-android.sh
./gradlew assembleStandardDebug
```

With the dependencies and SDK already prepared, PowerShell can build with:

```powershell
cd android
.\gradlew.bat assembleStandardDebug
```

The dependencies do not need rebuilding for ordinary interface or documentation changes. APKs are written under `android/app/build/outputs/apk/`.

The normal flavor is `standard`. Legacy task names `antutu`, `ludashi` and `pubg` remain available for build-script compatibility, but **all current flavors use `com.crixux.dukeps3`**.

## Credits

DukePS3 builds on the work of RPCS3, RPCS3-Android, PS3Native and WinNative/OpenFlow. The attributions and source lineage of the frame-generation components are retained below.

* the [RPCS3](https://github.com/RPCS3/rpcs3) team, for the emulator
* [PS3Native](https://github.com/maxjivi05/PS3Native), for the Android fork this project builds on
* [thecrixux](https://github.com/thecrixux), for maintaining DukePS3, its identity and hands-on Android testing
* the [RPCS3-Android](https://github.com/RPCS3/rpcs3-android) port this build started from
* the [WinNative](https://github.com/WinNative-Emu) developers, for the interface work and Android fixes

<details>
<summary><strong>Frame generation credits and source lineage</strong></summary>

### Frame generation

The interpolation chain in [`rpcs3/Emu/RSX/VK/lsfg/`](rpcs3/Emu/RSX/VK/lsfg) is not original work. It reaches this tree through:

* **[lsfg-vk](https://github.com/PancakeTAS/lsfg-vk)** by PancakeTAS and contributors (MIT) — the original Vulkan reimplementation of the Lossless Scaling frame generation chain, and the source of its structure: the mipmap pyramid, the alpha/beta/gamma/delta flow passes and the generation pass.
* **Camille LaVey**, in the **[Eden Emulator Project](https://git.eden-emu.dev/eden-emu/eden)** (GPL-3.0-or-later) — the port of that chain into an emulator's Vulkan renderer, landed as eden PR #4263, *[vulkan, android] Initial implementation of LSFG-VK*. This is the work that made the feature possible here: getting the Lossless Scaling compute chain running correctly on Vulkan on mobile GPUs is the hard part, and it was already solved. Every `lsfg_*.cpp` and `lsfg_*.hpp` in this tree descends from `src/video_core/renderer_vulkan/present/` in that port and keeps its SPDX headers. That includes the pacer: `lsfg_pacer` began as `frame_gen_pacer` and has since been rewritten around the panel refresh rate and the guest present rate, but the design is theirs. What is written for this project is the RPCS3 side — `VKFrameGeneration`, the presenter wiring in `VKPresent`, and the settings and menu surface around them.
* **[DXVK](https://github.com/doitsujin/dxvk)** — copyright Philip Rebohle, Joshua Ashton, Robin Kertels and Jeffrey Ellison, zlib/libpng licence. Its DXBC-to-SPIR-V shader translator is vendored at [`3rdparty/dxbc`](3rdparty/dxbc), taken from a standalone repackaging of those files rather than from the DXVK tree itself. Steam builds of Lossless Scaling ship the shaders as DXBC rather than SPIR-V, so they are translated once on import. This entry is the acknowledgment the zlib licence asks for.
* **[Lossless Scaling](https://store.steampowered.com/app/993090/Lossless_Scaling/)** by THS — the shaders themselves. `Lossless.dll` is proprietary and remains the property of THS; it is read from the user's own installed copy at runtime, and neither it nor any shader extracted from it is redistributed here.
* **[LSFG-Android](https://github.com/FrankBarretta/LSFG-Android)** by FrankBarretta — the first project to run the lsfg-vk pipeline on Android, and a reference while this port was written. It takes a different route, compositing over a `MediaProjection` capture in a system overlay rather than inside a renderer, so no code is shared with it. Its repository is not under a single licence: the root is MIT, `lsfg-vk-android/` is MIT inherited from lsfg-vk, and the `LSFG-Android/` application subtree is under a custom licence that forbids app-store publication and commercial use.

lsfg-vk is MIT, which is compatible with both GPLv2 and GPLv3. The files under `rpcs3/Emu/RSX/VK/lsfg/` descend from Camille LaVey's Eden port rather than from lsfg-vk directly, so they carry its GPL-3.0-or-later terms and those SPDX headers have to survive. The two files there without such a header — `lsfg_dll.*`, which walks the PE resource tree, and `lsfg_dxbc.*`, which bridges to DXVK's translator — were written for the Android side.

The free DIS engine in `rpcs3/Emu/RSX/VK/dis/` is a port of
**qwertypower (DEVAR Entertainment LLC)**'s GPL-3.0-or-later implementation in
[WinNative, now named OpenFlow](https://github.com/WinNative-Emu/WinNative/tree/098227e8aea3544210347321ab3a2535bd4c00c4/app/src/main/cpp/openflow).
The algorithm comes from OpenCV's DISOpticalFlow and Till Kroeger's OF_DIS.
Our Vulkan port began with PS3Native PR #25. The shared-tile inverse search,
subsampled propagation and packed SOR coefficients incorporate the author's
[optimization work in PR #776](https://github.com/WinNative-Emu/WinNative/pull/776)
(commit `31f0864f31dd013fdce940fe328562766aa898ea`), adapted to this engine's
existing descriptors. The hardware motion-estimation path is not included.
These files retain their original copyright and license headers.

</details>

## License

Most files are licensed under **GPL-2.0-only**; see [LICENSE](LICENSE). Other components have their own licenses, including frame-generation files under **GPL-3.0-or-later**. Check the corresponding headers and licenses. DukePS3 is not affiliated with or endorsed by Sony Interactive Entertainment.
