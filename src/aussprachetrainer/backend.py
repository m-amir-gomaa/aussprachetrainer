import subprocess
import os
import tempfile
import pyttsx3
import shutil
import sqlite3
import threading
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from gtts import gTTS
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from aussprachetrainer.database import HistoryManager

class PronunciationBackend:
    def __init__(self):
        # Initialize offline TTS engine
        self.engine = pyttsx3.init()
        # History Manager
        self.db = HistoryManager()
        # Session audio dir
        self.session_dir = tempfile.mkdtemp(prefix="aussprachetrainer_")
        
        # Recording state
        self.recording = False
        self.recorded_frames = []
        self.fs = 16000 # 16kHz for ASR
        
    def __del__(self):
        if hasattr(self, 'session_dir') and os.path.exists(self.session_dir):
            shutil.rmtree(self.session_dir)

    def get_voices(self) -> List[Dict[str, str]]:
        voices = self.engine.getProperty('voices')
        voice_list = []
        for v in voices:
            is_german = 'german' in v.name.lower() or 'de' in v.languages or 'de-de' in v.id.lower()
            voice_list.append({'id': v.id, 'name': v.name, 'is_german': is_german})
        return voice_list

    def get_ipa(self, text: str) -> str:
        try:
            result = subprocess.run(
                ['espeak-ng', '-v', 'de', '-q', '--ipa', text],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except:
            return "[Error]"

    def generate_audio(self, text: str, online: bool = False, voice_id: str = None) -> str:
        filename = f"audio_{hash(text + str(online) + str(voice_id))}.mp3"
        filepath = os.path.join(self.session_dir, filename)
        if os.path.exists(filepath): return filepath

        if online: self._generate_online(text, filepath)
        else: self._generate_offline(text, filepath, voice_id)
        
        # Save to history automatically? The GUI will handle this to include IPA
        return filepath

    def _generate_offline(self, text: str, filepath: str, voice_id: str = None):
        wav_path = filepath.replace('.mp3', '.wav')
        cmd = ['espeak-ng', '-v', 'de', '-w', wav_path, text]
        subprocess.run(cmd, check=True)
        # Convert or just return wav_path? sd.play can play wav.
        # pyttsx3 save_to_file is better for voice_id support
        # but espeak-ng is safer for nix.
        return wav_path

    def _generate_online(self, text: str, filepath: str):
        gTTS(text=text, lang='de').save(filepath)

    def play_file(self, filepath: str):
        if not filepath or not os.path.exists(filepath): return
        cmd = ['aplay', '-q', filepath] if filepath.endswith('.wav') else ['mpg123', '-q', filepath]
        subprocess.run(cmd, check=False)

    # --- Recording & Assessment ---

    def start_recording(self):
        self.recording = True
        self.recorded_frames = []
        def callback(indata, frames, time, status):
            if self.recording:
                self.recorded_frames.append(indata.copy())
        
        self.stream = sd.InputStream(samplerate=self.fs, channels=1, callback=callback)
        self.stream.start()

    def stop_recording(self) -> str:
        self.recording = False
        self.stream.stop()
        self.stream.close()
        
        if not self.recorded_frames: return None
        
        audio_data = np.concatenate(self.recorded_frames, axis=0)
        temp_wav = os.path.join(self.session_dir, "recorded.wav")
        import wave
        with wave.open(temp_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.fs)
            wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
        return temp_wav

    def assess_pronunciation(self, target_text: str, audio_path: str, online: bool = True) -> Dict:
        if not audio_path: return {"error": "No audio"}
        
        recognized_text = ""
        if online:
            recognized_text = self._transcribe_online(audio_path)
        else:
            recognized_text = self._transcribe_offline(audio_path)
            
        if not recognized_text: return {"error": "Could not recognize speech"}
        
        score = SequenceMatcher(None, target_text.lower(), recognized_text.lower()).ratio()
        return {
            "target": target_text,
            "actual": recognized_text,
            "score": int(score * 100)
        }

    def _transcribe_online(self, audio_path: str) -> str:
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)
        try:
            return r.recognize_google(audio, language="de-DE")
        except:
            return ""

    def _transcribe_offline(self, audio_path: str) -> str:
        # Vosk implementation placeholder or use pocketsphinx
        # For a minimal app, we'll try to use SpeechRecognition's offline if available
        # or simplified fallback. Vosk is better but needs model.
        # Let's assume for now online is preferred and offline ASR is a "best effort".
        return "[Offline ASR needs Vosk Model]"
