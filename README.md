# Aussprachetrainer 🇩🇪

A premium German pronunciation trainer specialized for dialects (**Germany**, **Austria**, **Switzerland**).

## ✨ Features

- **Specialized German Focus**: Support for regional dialects (de-DE, de-AT, de-CH).
- **Online & Offline Modes**: Integrated with Google TTS/ASR and `espeak-ng`/`pocketsphinx`.
- **Premium GUI**: Resizable panels, Dark Mode, and Fullscreen support (F11).
- **IPA Display**: Real-time phonetic transcription.
- **Autocomplete**: Popularity-based word suggestions that learn from your history.
- **Privacy First**: Local history buffer and optional offline processing.

## 🚀 Getting Started

### Using Nix (Recommended)

If you have [Nix](https://nixos.org/download.html) installed with flakes enabled:

```bash
# Run directly
nix run github:m-amir-gomaa/aussprachetrainer

# Development shell
nix develop github:m-amir-gomaa/aussprachetrainer
```

### Manual Installation (Python)

1. **System Dependencies**:
   - `espeak-ng`
   - `portaudio`
   - `pulseaudio` (or `alsa-utils`)
   - `mpg123`

2. **Clone and Install**:

```bash
git clone https://github.com/m-amir-gomaa/aussprachetrainer
cd aussprachetrainer
pip install .
```

3. **Run**:

```bash
aussprachetrainer
```

## ⌨️ Shortcuts

- **F5 / Ctrl+Enter**: Speak & Generate IPA
- **F11**: Toggle Fullscreen
- **Ctrl+A**: Select All in input box
- **Tab**: Cycle autocomplete suggestions
- **Esc**: Exit Fullscreen / Close suggestions

## 🛠 Tech Stack

- **GUI**: CustomTkinter
- **TTS**: pyttsx3, gTTS
- **ASR**: SpeechRecognition (Google/Pocketsphinx)
- **Environment**: Nix (Flakes)

## 📄 License

MIT License - Copyright (c) 2026 m-amir-gomaa
