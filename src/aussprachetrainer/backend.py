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
        
        # Dialect state
        self.dialect = "de-DE" # Standard German, de-AT, de-CH
        
        # Recording state
        self.recording = False
        self.recorded_frames = []
        self.fs = 44100 # Change to 44.1kHz for better compatibility

    def set_dialect(self, code: str):
        self.dialect = code

    def _get_espeak_voice(self) -> str:
        mapping = {"de-DE": "de", "de-AT": "de-at", "de-CH": "de-ch"}
        return mapping.get(self.dialect, "de")
        
    def __del__(self):
        if hasattr(self, 'session_dir') and os.path.exists(self.session_dir):
            try: shutil.rmtree(self.session_dir)
            except: pass

    def get_voices(self) -> List[Dict[str, str]]:
        try:
            voices = self.engine.getProperty('voices')
            voice_list = []
            for v in voices:
                is_german = 'german' in v.name.lower() or 'de' in v.languages or 'de-de' in v.id.lower() or 'de-at' in v.id.lower() or 'de-ch' in v.id.lower()
                if is_german:
                    voice_list.append({'id': v.id, 'name': v.name})
            return voice_list
        except: return []

    def get_ipa(self, text: str) -> str:
        try:
            result = subprocess.run(
                ['espeak-ng', '-v', self._get_espeak_voice(), '-q', '--ipa', text],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except:
            return ""

    def generate_audio(self, text: str, online: bool = False, voice_id: str = None) -> str:
        print(f"DEBUG: Generating audio for '{text}', online={online}")
        ext = ".mp3" if online else ".wav"
        filename = f"audio_{hash(text + str(online) + str(voice_id))}{ext}"
        filepath = os.path.join(self.session_dir, filename)
        
        if os.path.exists(filepath):
            print(f"DEBUG: Using cached audio at {filepath}")
            return filepath

        try:
            if online: self._generate_online(text, filepath)
            else: filepath = self._generate_offline(text, filepath, voice_id)
            print(f"DEBUG: Audio generated at {filepath}")
        except Exception as e:
            print(f"DEBUG: Audio generation failed: {e}")
            return None
        
        return filepath

    def _generate_offline(self, text: str, filepath: str, voice_id: str = None):
        # espeak-ng only does wav natively with -w
        if not filepath.endswith('.wav'): filepath = filepath.replace('.mp3', '.wav')
        # Use voice_id if provided, else dialect-based default
        v = voice_id if voice_id else self._get_espeak_voice()
        cmd = ['espeak-ng', '-v', v, '-w', filepath, text]
        print(f"DEBUG: Running offline TTS: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"DEBUG: espeak-ng failed: {result.stderr}")
            raise Exception(f"espeak-ng failed: {result.stderr}")
        return filepath

    def _generate_online(self, text: str, filepath: str):
        print(f"DEBUG: Running online TTS (gTTS)")
        gTTS(text=text, lang='de').save(filepath)

    def play_file(self, filepath: str):
        if not filepath or not os.path.exists(filepath):
            print(f"DEBUG: Cannot play file, path invalid or not found: {filepath}")
            return
        
        # Try both ffplay/paplay if aplay fails or for better compatibility
        if filepath.endswith('.wav'):
            # Some systems might prefer paplay or play (sox)
            cmd = ['paplay', filepath] if shutil.which('paplay') else ['aplay', '-q', filepath]
        else:
            cmd = ['mpg123', '-q', filepath]
            
        print(f"DEBUG: Playing audio: {' '.join(cmd)}")
        try:
            # We don't use capture_output=True here because we want the audio to actually play
            # and potentially block the background thread normally.
            subprocess.run(cmd, check=False)
        except Exception as e:
            print(f"DEBUG: Playback exception: {e}")

    # --- Recording & Assessment ---

    def start_recording(self):
        self.recording = True
        self.recorded_frames = []
        def callback(indata, frames, time, status):
            if status:
                print(f"DEBUG: Recording status: {status}")
            if self.recording:
                self.recorded_frames.append(indata.copy())
        
        try:
            # Open stream
            self.stream = sd.InputStream(samplerate=self.fs, channels=1, callback=callback)
            self.stream.start()
        except Exception as e:
            print(f"DEBUG: Failed to start recording stream: {e}")
            self.recording = False
            raise e

    def stop_recording(self) -> str:
        self.recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        if not self.recorded_frames:
            print("DEBUG: No frames recorded")
            return None
        
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
        try:
            if online: recognized_text = self._transcribe_online(audio_path)
            else: recognized_text = self._transcribe_offline(audio_path)
        except Exception as e:
            return {"error": f"ASR failed: {e}"}
            
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
            return r.recognize_google(audio, language=self.dialect)
        except:
            return ""

    def _transcribe_offline(self, audio_path: str) -> str:
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)
        try:
            # SpeechRecognition has built-in support for pocketsphinx
            return r.recognize_pocketsphinx(audio, language=self.dialect)
        except sr.UnknownValueError:
            return "[Could not understand audio]"
        except sr.RequestError as e:
            return f"[Pocketsphinx error: {e}]"
        except:
            # Fallback if specific dialect model is missing
            try:
                return r.recognize_pocketsphinx(audio)
            except:
                return "[Offline ASR failed]"
