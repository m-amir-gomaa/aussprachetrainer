# GermanPronun Advanced

A comprehensive German pronunciation trainer for Linux desktop.

## Features
- **Premium UI**: Modern dark-mode interface built with `CustomTkinter`.
- **Searchable History**: Persistent SQLite-backed history with search and deletion.
- **Pronunciation Assessment**: Record your voice and get instant transcription and accuracy scores.
- **100k Word Autocomplete**: Fast, smart suggestions using a massive German word list and your own history.
- **Customizable Settings**: Adjust font size and view system/model information.
- **Offline & Online Modes**: Toggle between local (espeak-ng/vosk) and cloud (gTTS/Google) engines.

## Requirements
- Nix with flake support enabled.

## Installation & Running

1. **Enter the dev environment**:
   ```bash
   nix develop
   ```
2. **Run directly**:
   ```bash
   nix run
   ```

## Usage
1. **Train**: Type a word, press `F5` to hear it and see the IPA.
2. **Practice**: Click "Record", say the word, and let the AI assess your accuracy.
3. **Review**: Search your history in the sidebar to re-play or delete previous attempts.
4. **Customize**: Adjust the font size in the sidebar to your preference.

