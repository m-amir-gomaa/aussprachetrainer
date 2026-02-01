# Packaging Guide

This guide covers how to package **Aussprachetrainer** for various Linux distributions.

## 1. Nix Package (Native)

Since this project is built with Nix Flakes, creating a package for NixOS or any Nix-enabled system is the native workflow.

### Build Locally
To build the package and produce a `./result` symlink:

```bash
nix build
```

The binary will be available at `./result/bin/aussprachetrainer`.
Note: This binary links to libraries in `/nix/store` and will *only* run on systems with standard Nix paths.

### Install on NixOS
Add the flake to your `flake.nix` inputs:

```nix
inputs = {
  aussprachetrainer.url = "github:m-amir-gomaa/aussprachetrainer";
};
```

Then add it to your `environment.systemPackages`:

```nix
environment.systemPackages = [
  inputs.aussprachetrainer.packages.${pkgs.system}.default
];
```

## 2. AppImage (Universal Linux)

The easiest way to create an AppImage that runs on *any* Linux distro (Ubuntu, Fedora, Arch, etc.) without requiring Nix installed on the target machine is to bundle the Nix package.

We recommend using `nix-appimage` to bundle the flake output.

### Build AppImage

```bash
nix run github:nix-community/nix-appimage -- bundle .
```

This will produce an `aussprachetrainer.AppImage` (or similar name) in your current directory.
You can rename and distribute this file. It contains all dependencies (Python, GTK, espeak-ng, piper, etc.) self-contained.

### Verify AppImage
```bash
chmod +x aussprachetrainer-*.AppImage
./aussprachetrainer-*.AppImage
```

## 3. Flatpak

To distribute via Flathub or install as a Flatpak, you need to build a containerized application.

### Prerequisites
1. Install `flatpak` and `flatpak-builder`.
2. Install the GNOME SDK (as `customtkinter` relies on TK/Tcl which works well with the Freedesktop/GNOME runtime).

```bash
flatpak install org.freedesktop.Sdk//23.08 org.freedesktop.Platform//23.08
```

### Manifest (`org.github.m_amir_gomaa.aussprachetrainer.yml`)

Create a file named `org.github.m_amir_gomaa.aussprachetrainer.yml`:

```yaml
app-id: org.github.m_amir_gomaa.aussprachetrainer
runtime: org.freedesktop.Platform
runtime-version: '23.08'
sdk: org.freedesktop.Sdk
command: aussprachetrainer
finish-args:
  # X11 / Wayland access
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  # Audio access
  - --socket=pulseaudio
  # Filesystem access (optional, tailored for usage)
  - --filesystem=home
  # Network access (for online TTS/ASR)
  - --share=network

modules:
  # 1. Native Dependencies
  - name: espeak-ng
    buildsystem: autotools
    config-opts:
      - --without-async
      - --without-mbrola
    sources:
      - type: archive
        url: https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.51.tar.gz
        sha256: 'ab6a77dcccb82eb91b9a97217030588147d3399z' # Replace with actual SHA
    # Note: You may need to build portaudio/speech-dispatcher here if not in SDK

  # 2. Python & Dependencies
  - name: aussprachetrainer
    buildsystem: simple
    build-commands:
      - pip install --prefix=/app --no-deps .
    sources:
      - type: dir
        path: .
    modules:
      # Use flatpak-pip-generator to generate a requirements.json for all python deps
      # flatpak-pip-generator pyttsx3 gTTS customtkinter numpy ...
      # Include the generated json here:
      # - requirements.json
      pass

```

**Note on Flatpak**: The Flatpak build works best if you generate a precise `python3-requirements.json` using [flatpak-pip-generator](https://github.com/flatpak/flatpak-builder-tools/tree/master/pip).
Since this app has complex C-extension dependencies (wrapping `text_engine.c` and `zep_wrapper.cpp`), you might need to adjust the build commands to ensure `gcc` and headers are available during the `pip install` phase.

For a pure "build from source" Flatpak without Nix, you typically need to list every library (`espeak-ng`, `portaudio`) as a module in the manifest.

### Recommended Approach
Use the **AppImage** method (Section 2) for generic Linux distribution as it leverages the already-working Nix configuration to handle the complex dependency graph automatically.

---

## 🔄 Updating Packages

### AppImage
To update your AppImage, simply pull the latest source code and re-run the bundle command:
```bash
git pull
nix run github:nix-community/nix-appimage -- bundle .
```
Then replace your old AppImage with the newly generated one.

### Flatpak
If installed from a repository (e.g., Flathub), use:
```bash
flatpak update org.github.m_amir_gomaa.aussprachetrainer
```
If you are developing locally, rebuild and re-install:
```bash
flatpak-builder --force-clean --install build-dir org.github.m_amir_gomaa.aussprachetrainer.yml
```
