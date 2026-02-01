# Aussprachetrainer 🇩🇪

A premium German pronunciation trainer with native Vim keybindings, specialized for regional dialects (**Germany**, **Austria**, **Switzerland**).

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Nix](https://img.shields.io/badge/built%20with-Nix-5277C3.svg)

---

## 📖 Overview

**Aussprachetrainer** is a modern desktop application designed to help learners master German pronunciation across different regional dialects. It combines powerful Text-to-Speech (TTS) and Automatic Speech Recognition (ASR) capabilities with a Vim-inspired text editor for a fully keyboard-driven workflow.

### Key Highlights

- **Mouseless Experience**: Complete keyboard control with Vim motions and global shortcuts
- **Dialect Support**: Specialized for German dialects (de-DE, de-AT, de-CH)
- **Offline-First**: Works completely offline with `espeak-ng`, `piper-tts`, and `pocketsphinx`
- **Smart Autocomplete**: Context-aware word suggestions powered by frequency analysis
- **IPA Transcription**: Real-time phonetic transcription using `espeak-ng`
- **Premium UI**: Dark mode with Catppuccin-inspired theme and resizable panels

---

## ✨ Features

### 🎯 Core Functionality

- **Text-to-Speech (TTS)**
  - Online: Google TTS with dialect support
  - Offline: Piper neural TTS, Kokoro ONNX, and espeak-ng fallback
  - Voice selection for different German accents

- **Speech Recognition (ASR)**
  - Online: Google Speech Recognition
  - Offline: Pocketsphinx with German language models
  - Pronunciation scoring with phonetic comparison

- **IPA Display**
  - Real-time phonetic transcription
  - Side-by-side comparison of target vs. actual pronunciation

### ⌨️ Vim Integration

- **Full Vim Motions**: `hjkl`, `w/b/e`, `gg/G`, `0/$`
- **Operators**: `d` (delete), `c` (change), `y` (yank)
- **Visual Modes**: Character-wise (`v`) and line-wise (`V`) selection
- **Multipliers**: `3w`, `2dd`, `5j`, etc.
- **Insert Mode**: `i`, `a`, `o`, `O`, `I`, `A`
- **Replace Mode**: `R` (bulk), `r` (single character)
- **Undo/Redo**: `u` / `Ctrl+r`

### 🚀 Mouseless Navigation

| Shortcut            | Action                              |
| ------------------- | ----------------------------------- |
| `Ctrl+Return`       | Generate speech and IPA             |
| `Ctrl+r`            | Toggle recording (start/stop)       |
| `Ctrl+p`            | Play last audio                     |
| `Ctrl+h`            | Toggle history panel                |
| `Ctrl+n` / `Ctrl+p` | Navigate autocomplete (Insert mode) |
| `F11`               | Toggle fullscreen                   |
| `Esc`               | Exit fullscreen / Normal mode       |

### 📊 Smart Features

- **Autocomplete**: Frequency-based German word suggestions that learn from your usage
- **History Management**: Searchable history with `j`/`k` navigation and "Clear All" functionality
- **Persistence**: Saves window geometry, mode preferences, audio files, and usage history
- **Automatic Mode Switching**: Detects internet connectivity and switches TTS/ASR modes

---

## 🚀 Installation

### Using Nix (Recommended)

If you have [Nix](https://nixos.org/download.html) installed with flakes enabled:

```bash
# Run directly from cachix, you won't need to build the application on your machine
nix run github:m-amir-gomaa/aussprachetrainer

# Or clone and run locally
git clone https://github.com/m-amir-gomaa/aussprachetrainer
cd aussprachetrainer
nix run

# Development shell
nix develop
```

#### Permanent Installation (NixOS / Home Manager)

To add Aussprachetrainer to your system permanently using Flakes:

1. **Verify the build** (optional but recommended):
   ```bash
   git clone https://github.com/m-amir-gomaa/aussprachetrainer
   cd aussprachetrainer
   nix build
   # Verify it runs
   ./result/bin/aussprachetrainer
   ```

2. **Add to your system `flake.nix`**:
   Add the repository to your `inputs`:
   ```nix
   inputs = {
     nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
     aussprachetrainer.url = "github:m-amir-gomaa/aussprachetrainer";
   };
   ```

3. **Install to `systemPackages`**:
   In your `outputs` or configuration file:
   ```nix
   environment.systemPackages = [
     inputs.aussprachetrainer.packages.${pkgs.system}.default
   ];
   ```

4. **Apply changes**:
   ```bash
   sudo nixos-rebuild switch --flake .
   ```

### Manual Installation

#### 1. System Dependencies

**Debian/Ubuntu:**

```bash
sudo apt install espeak-ng portaudio19-dev pulseaudio mpg123 gcc g++ cmake pkg-config python3-dev
```

**Arch Linux:**

```bash
sudo pacman -S espeak-ng portaudio pulseaudio mpg123 gcc cmake pkgconf python
```

**macOS:**

```bash
brew install espeak-ng portaudio mpg123 cmake pkg-config
```

#### 2. Python Dependencies

```bash
git clone https://github.com/m-amir-gomaa/aussprachetrainer
cd aussprachetrainer

# Install Python dependencies
pip install -e .

# Build C++ extensions
python -c "import pybind11; print(pybind11.get_include())"
# Use the output path in the following commands

# Build Zep Vim wrapper
g++ -O3 -Wall -shared -std=c++11 -fPIC \
    -I$(python3 -c "import pybind11; print(pybind11.get_include())") \
    -I$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
    src/aussprachetrainer/lib/zep_wrapper.cpp \
    -o src/aussprachetrainer/zep_vim.so

# Build text engine
gcc -shared -o src/aussprachetrainer/lib/text_engine.so \
    src/aussprachetrainer/lib/text_engine.c -fPIC
```

#### 3. Run

```bash
python -m aussprachetrainer
```

### Packaging for Distribution

For instructions on building a Nix package, Flatpak, or AppImage, see [PACKAGING.md](PACKAGING.md).

---

## 🔄 Updating

### Using Nix

If you run the application directly via `nix run`:

```bash
# Force Nix to check for the latest version from GitHub
nix run --refresh github:m-amir-gomaa/aussprachetrainer
```

If you installed it permanently in your system flake:

```bash
# Update the lockfile to point to the latest GitHub commit
nix flake update aussprachetrainer
sudo nixos-rebuild switch --flake .
```

If you have a local clone for development:

```bash
git pull
nix build    # Rebuild in ./result
nix run      # Run the local version
```

### Manual Installation

To pull the latest changes and rebuild the C extensions:

```bash
git pull

# Rebuild the Vim engine and text engine
nix develop --command bash -c 'g++ -O3 -Wall -shared -std=c++11 -fPIC \
    -I$(python3 -c "import pybind11; print(pybind11.get_include())") \
    -I$(python3 -c "import sysconfig; print(sysconfig.get_paths()[\"include\"])") \
    src/aussprachetrainer/lib/zep_wrapper.cpp \
    -o src/aussprachetrainer/zep_vim.so'

gcc -shared -o src/aussprachetrainer/lib/text_engine.so \
    src/aussprachetrainer/lib/text_engine.c -fPIC
```

---

## 📚 Usage

### Basic Workflow

1. **Launch the application**

   ```bash
   nix run github:m-amir-gomaa/aussprachetrainer
   ```

2. **Type German text** using the Vim editor
   - Press `i` to enter Insert mode
   - Type your German sentence
   - Press `Esc` or `jj` to return to Normal mode

3. **Generate speech**
   - Press `Ctrl+Return` or click "Speak & IPA"
   - Listen to the pronunciation
   - View the IPA transcription

4. **Record your pronunciation**
   - Press `Ctrl+r` or click "Start Recording"
   - Speak the sentence
   - Press `Ctrl+r` again to stop
   - View your pronunciation score

### Vim Cheat Sheet

```
NORMAL MODE:
  h j k l       - Move cursor left/down/up/right
  w b e         - Word navigation (forward/backward/end)
  0 $           - Line start/end
  gg G          - File start/end
  dd            - Delete line
  dw            - Delete word
  3dd           - Delete 3 lines
  yy            - Yank (copy) line
  p P           - Paste after/before cursor
  u             - Undo
  Ctrl+r        - Redo (in Normal mode)

INSERT MODE:
  i a           - Insert before/after cursor
  I A           - Insert at line start/end
  o O           - Open new line below/above
  Esc or jj     - Return to Normal mode
  Ctrl+n/Ctrl+p - Navigate autocomplete

VISUAL MODE:
  v             - Character-wise selection
  V             - Line-wise selection
  d y c         - Delete/yank/change selection

GERMAN INPUT (INSERT MODE):
  Alt+a         - ä
  Alt+o         - ö
  Alt+u         - ü
  Alt+s (twice) - ß (Alt+s inserts 's', second Alt+s replaces it with 'ß')
  Alt+Shift+a   - Ä
  Alt+Shift+o   - Ö
  Alt+Shift+u   - Ü
  Alt+Shift+s (twice) - ẞ
```

### History Navigation

1. Press `Ctrl+h` to open the history panel
2. Use `j`/`k` to navigate through entries
3. Press `Enter` to load an entry into the editor
4. Press `Ctrl+h` again to return to the editor

---

## 🏗️ Architecture & Design

### Technology Stack

- **GUI Framework**: CustomTkinter (modern, themed Tkinter)
- **Vim Engine**: Custom C++ implementation with pybind11 bindings
- **TTS Engines**:
  - Online: gTTS (Google Text-to-Speech)
  - Offline: Piper neural TTS, Kokoro ONNX, espeak-ng
- **ASR Engines**:
  - Online: Google Speech Recognition
  - Offline: Pocketsphinx
- **Autocomplete**: C-based Trie with frequency ranking
- **Build System**: Nix Flakes for reproducible builds
- **Testing**: unittest with 13 Vim engine tests + 4 UI tests

### Project Structure

```
aussprachetrainer/
├── src/aussprachetrainer/
│   ├── gui.py                 # Main application GUI
│   ├── backend.py             # TTS/ASR/IPA logic
│   ├── vim_editor.py          # Vim editor component
│   ├── autocomplete.py        # German word suggester
│   ├── database.py            # History persistence
│   ├── config.py              # Configuration manager
│   └── lib/
│       ├── zep_wrapper.cpp    # Vim engine (C++)
│       └── text_engine.c      # Text utilities (C)
├── tests/
│   ├── test_vim.py            # Vim engine tests
│   └── test_ui.py             # UI integration tests
├── flake.nix                  # Nix build configuration
└── README.md
```

### Design Philosophy

1. **Keyboard-First**: Every feature is accessible via keyboard shortcuts
2. **Offline-Capable**: Core functionality works without internet
3. **Privacy-Focused**: All data stored locally, no telemetry
4. **Vim-Native**: Not just Vim keybindings, but a real Vim engine
5. **Extensible**: Modular architecture for easy feature additions

---

## 🧪 Testing

Run the test suite:

```bash
# Comprehensive Test Suite (DB, Vim, Audio, Autocomplete)
nix develop --command python3 tests/test_comprehensive.py

# Vim engine tests (Legacy)
nix develop --command bash -c "export PYTHONPATH=\$PYTHONPATH:\$(pwd)/src && python3 tests/test_vim.py -v"

# UI integration tests (Legacy)
nix develop --command bash -c "export PYTHONPATH=\$PYTHONPATH:\$(pwd)/src && python3 tests/test_ui.py -v"

# Run all tests using unittest discovery
nix develop --command bash -c "export PYTHONPATH=\$PYTHONPATH:\$(pwd)/src && python3 -m unittest discover tests"
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/m-amir-gomaa/aussprachetrainer
cd aussprachetrainer

# Enter development environment
nix develop

# Make changes and test
python -m aussprachetrainer
```

---

## 📄 License

MIT License - Copyright (c) 2026 m-amir-gomaa

See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Zep** - Inspiration for the Vim engine architecture
- **CustomTkinter** - Modern themed Tkinter framework
- **Piper TTS** - High-quality neural TTS voices
- **espeak-ng** - Phonetic transcription and fallback TTS
- **Catppuccin** - Color scheme inspiration

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/m-amir-gomaa/aussprachetrainer/issues)
