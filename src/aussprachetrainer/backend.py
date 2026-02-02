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
import socket
from gtts import gTTS
try:
    from kokoro_onnx import Kokoro
except ImportError:
    Kokoro = None
import re
from typing import List, Dict, Optional
from rapidfuzz import distance
from aussprachetrainer.database import HistoryManager

class PronunciationBackend:
    def __init__(self):
        # Initialize offline TTS engine
        self.engine = pyttsx3.init()
        # History Manager
        self.db = HistoryManager()
        
        # Persistent audio directory
        self.audio_dir = os.path.expanduser("~/.local/share/aussprachetrainer/audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Session audio dir (temporary)
        self.session_dir = tempfile.mkdtemp(prefix="aussprachetrainer_")
        
        # Piper models directory
        self.models_dir = os.path.expanduser("~/.local/share/aussprachetrainer/models")
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Dialect state
        self.dialect = "de-DE" # Standard German, de-AT, de-CH
        
        # Recording state
        self.recording = False
        self.recorded_frames = []
        self.fs = 44100 # Change to 44.1kHz for better compatibility
        self.last_audio_path = None

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

    def check_internet(self) -> bool:
        """Check if internet connection is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def get_online_voices(self) -> List[Dict[str, str]]:
        """Get available gTTS voices/accents for German"""
        return [
            {'id': 'de', 'name': 'German (Standard)'},
            {'id': 'de-at', 'name': 'German (Austria)'},
            {'id': 'de-ch', 'name': 'German (Switzerland)'},
        ]

    def get_offline_voices(self) -> List[Dict[str, str]]:
        """Get available Kokoro, Piper and espeak-ng voices for German"""
        voices = [
            # Kokoro Neural Voices (Highest Quality)
            {'id': 'kokoro:de_male', 'name': 'Kokoro German (Male)'},
            {'id': 'kokoro:de_female', 'name': 'Kokoro German (Female)'},
            # Piper Neural Voices (High Quality)
            {'id': 'piper:de_DE-thorsten-high', 'name': 'Piper Thorsten (High)'},
            {'id': 'piper:de_DE-thorsten-medium', 'name': 'Piper Thorsten (Medium)'},
            {'id': 'piper:de_DE-karlsson-low', 'name': 'Piper Karlsson (Low)'},
            # Espeak-ng fallback voices
            {'id': 'de', 'name': 'espeak German (Standard)'},
            {'id': 'de+m3', 'name': 'espeak German (Male 3)'},
            {'id': 'de+f2', 'name': 'espeak German (Female 2)'},
        ]
        return voices

class GermanIPAProcessor:
    @staticmethod
    def process(ipa: str, text: str = "") -> str:
        if not ipa:
            return ""
            
        # 0. Formatting Refinement
        ipa = ipa.replace("'", "ˈ").replace(",", "ˌ").replace(":", "ː")
            
        vowels = 'aeiouyøɛœɔɪʊɑɐə'
        v_reg = f'[{vowels}]'
        # 1. R Allophones
        # Onset R: r or ɾ followed by a vowel or stress mark + vowel
        ipa = re.sub(r'[rɾ]([ˈˌ]?' + v_reg + ')', r'ʁ\1', ipa)
        # Coda R: r or ɾ not followed by a vowel pattern
        ipa = re.sub(r'[rɾ](?![ˈˌ]?' + v_reg + ')', r'ɐ̯', ipa)
        # Final -er
        ipa = ipa.replace('ɜ', 'ɐ')
        
        # 2. Glottal Stop [ʔ]
        ipa = re.sub(r'(^|\s)(' + v_reg + ')', r'\1ʔ\2', ipa)
        ipa = re.sub(r'(^|\s|' + v_reg + ')([ˈˌ])(' + v_reg + ')', r'\1\2ʔ\3', ipa)
        
        # 3. Aspiration [ʰ]
        ipa = re.sub(r'(?<![sʃ])ˈ([ptk])', r'ˈ\1ʰ', ipa)
        ipa = re.sub(r'(?<![sʃ])(^|\s)([ptk])(ˈ?)', r'\1\2ʰ\3', ipa)
        
        # 4. Syllabic Consonants [n̩, l̩]
        ipa = re.sub(r'əl($|\s|' + v_reg + '|[^' + vowels + '])', r'l̩\1', ipa)
        ipa = re.sub(r'ən($|\s|' + v_reg + '|[^' + vowels + '])', r'n̩\1', ipa)
        
        # 5. Voiceless Lenis [b̥, d̥, g̊, v̥, z̥, ʒ̊]
        ipa = ipa.replace('dʒ', 'ʒ') # Loanwords like Ingenieur
        if text:
            clean_text = re.sub(r'[^\w\s]', ' ', text).lower().split()
            ipa_words = ipa.split()
            processed_words = []
            
            for p_word, t_word in zip(ipa_words, clean_text):
                # Final devoicing mapping
                if t_word.endswith('b') and p_word.endswith('p'):
                    p_word = p_word[:-1] + 'b̥'
                elif t_word.endswith('d') and p_word.endswith('t'):
                    p_word = p_word[:-1] + 'd̥'
                elif t_word.endswith('g') and p_word.endswith('k'):
                    p_word = p_word[:-1] + 'g̊'
                elif t_word.endswith('v') and (p_word.endswith('f') or p_word.endswith('v')):
                    p_word = p_word[:-1] + 'v̥'
                elif t_word.endswith('s') and p_word.endswith('s'):
                    if 'ː' in p_word or 'aɪ̯' in p_word or 'aʊ̯' in p_word or 'ɔʏ̯' in p_word:
                        p_word = p_word[:-1] + 'z̥'
                elif (t_word.endswith('e') and t_word.endswith('ge') and p_word.endswith('ə')) or (t_word == "garage" and p_word.endswith('ə')):
                     if 'ɡ' in p_word:
                         p_word = p_word.replace('ɡə', 'ʒ̊ə')
                processed_words.append(p_word)
            
            if len(processed_words) == len(ipa_words):
                ipa = " ".join(processed_words)

        # 6. Diphthongs & Glides
        # Static diphthong mapping
        ipa = ipa.replace("aɪ", "aɪ̯").replace("aʊ", "aʊ̯").replace("ɔø", "ɔʏ̯").replace("ɔʏ", "ɔʏ̯")
        
        # Heuristic for glides [i̯, o̯, u̯]
        # Rule A: High vowel following another vowel (and not already marked)
        ipa = re.sub(r'(' + v_reg + '[ː]?|[ˈˌ]?' + v_reg + ')([iɪuʊo])(?!̯|ː)', r'\1\2̯', ipa)
        # Rule B: High vowel preceding another vowel (e.g. Familie)
        ipa = re.sub(r'([iɪuʊo])(?=' + v_reg + ')', r'\1̯', ipa)
        
        # 7. Clean up
        ipa = ipa.replace('̯̯', '̯') # Fix any duplicates
        ipa = ipa.replace('ɪ̯', 'i̯').replace('ʊ̯', 'u̯').replace('ɑ', 'a') # Normalize symbols
        ipa = ipa.replace('ʔʔ', 'ʔ')
        ipa = ipa.replace('ʁɐ̯', 'ɐ̯') # simplify combined R allophones
        # Ensure all R's are captured if any missed
        ipa = ipa.replace('r', 'ʁ').replace('ʀ', 'ʀ')
        
        return ipa.strip()

class PronunciationBackend:
    def __init__(self):
        # Initialize offline TTS engine
        self.engine = pyttsx3.init()
        # History Manager
        self.db = HistoryManager()
        
        # Persistent audio directory
        self.audio_dir = os.path.expanduser("~/.local/share/aussprachetrainer/audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Session audio dir (temporary)
        self.session_dir = tempfile.mkdtemp(prefix="aussprachetrainer_")
        
        # Piper models directory
        self.models_dir = os.path.expanduser("~/.local/share/aussprachetrainer/models")
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Dialect state
        self.dialect = "de-DE" # Standard German, de-AT, de-CH
        
        # Recording state
        self.recording = False
        self.recorded_frames = []
        self.fs = 44100 # Change to 44.1kHz for better compatibility
        self.last_audio_path = None

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

    def check_internet(self) -> bool:
        """Check if internet connection is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def get_online_voices(self) -> List[Dict[str, str]]:
        """Get available gTTS voices/accents for German"""
        return [
            {'id': 'de', 'name': 'German (Standard)'},
            {'id': 'de-at', 'name': 'German (Austria)'},
            {'id': 'de-ch', 'name': 'German (Switzerland)'},
        ]

    def get_offline_voices(self) -> List[Dict[str, str]]:
        """Get available Kokoro, Piper and espeak-ng voices for German"""
        voices = [
            # Kokoro Neural Voices (Highest Quality)
            {'id': 'kokoro:de_male', 'name': 'Kokoro German (Male)'},
            {'id': 'kokoro:de_female', 'name': 'Kokoro German (Female)'},
            # Piper Neural Voices (High Quality)
            {'id': 'piper:de_DE-thorsten-high', 'name': 'Piper Thorsten (High)'},
            {'id': 'piper:de_DE-thorsten-medium', 'name': 'Piper Thorsten (Medium)'},
            {'id': 'piper:de_DE-karlsson-low', 'name': 'Piper Karlsson (Low)'},
            # Espeak-ng fallback voices
            {'id': 'de', 'name': 'espeak German (Standard)'},
            {'id': 'de+m3', 'name': 'espeak German (Male 3)'},
            {'id': 'de+f2', 'name': 'espeak German (Female 2)'},
        ]
        return voices

    def get_ipa(self, text: str) -> str:
        try:
            voice = self._get_espeak_voice()
            result = subprocess.run(
                ['espeak-ng', '-v', voice, '-q', '--ipa', text],
                capture_output=True, text=True, check=True
            )
            raw_ipa = result.stdout.strip()
            return GermanIPAProcessor.process(raw_ipa, text)
        except Exception as e:
            print(f"DEBUG: get_ipa failed: {e}")
            return ""

    def generate_audio(self, text: str, online: bool = False, voice_id: str = None, online_voice: str = None) -> str:
        print(f"DEBUG: Generating audio for '{text}', online={online}, voice_id={voice_id}")
        ext = ".mp3" if online else ".wav"
        # Include voice in hash for caching
        cache_key = f"{text}_{online}_{voice_id}_{online_voice}"
        filename = f"audio_{hash(cache_key)}{ext}"
        filepath = os.path.join(self.session_dir, filename)
        
        if os.path.exists(filepath):
            return filepath

        try:
            if online: 
                self._generate_online(text, filepath, online_voice)
            else: 
                if voice_id and voice_id.startswith("kokoro:"):
                    filepath = self._generate_kokoro(text, filepath, voice_id)
                elif voice_id and voice_id.startswith("piper:"):
                    filepath = self._generate_piper(text, filepath, voice_id.split(":")[1])
                else:
                    filepath = self._generate_offline(text, filepath, voice_id)
            print(f"DEBUG: Audio generated at {filepath}")
        except Exception as e:
            print(f"DEBUG: Audio generation failed: {e}")
            return None
        
        self.last_audio_path = filepath
        return filepath

    def copy_to_persistent(self, session_audio_path: str) -> str:
        """Copy audio file from session directory to persistent storage.
        Returns the persistent path, or None if copy fails."""
        if not session_audio_path or not os.path.exists(session_audio_path):
            return None
        
        try:
            filename = os.path.basename(session_audio_path)
            persistent_path = os.path.join(self.audio_dir, filename)
            
            # Copy file to persistent storage
            import shutil
            shutil.copy2(session_audio_path, persistent_path)
            
            print(f"DEBUG: Copied audio to persistent storage: {persistent_path}")
            return persistent_path
        except Exception as e:
            print(f"DEBUG: Failed to copy audio to persistent storage: {e}")
            return None

    def is_piper_available(self) -> bool:
        """Check if any Piper models are present."""
        if not os.path.exists(self.models_dir): return False
        return any(f.endswith(".onnx") for f in os.listdir(self.models_dir))

    def get_missing_models(self) -> List[str]:
        """Return list of supported models that are not downloaded."""
        piper_supported = ["de_DE-thorsten-high", "de_DE-thorsten-medium", "de_DE-karlsson-low"]
        missing = []
        for m in piper_supported:
            if not os.path.exists(os.path.join(self.models_dir, f"{m}.onnx")):
                missing.append(f"piper:{m}")
        
        # Kokoro
        if not os.path.exists(os.path.join(self.models_dir, "kokoro-v0_19.onnx")):
            missing.append("kokoro:model")
        if not os.path.exists(os.path.join(self.models_dir, "voices.json")):
            missing.append("kokoro:voices")
            
        return missing

    def download_kokoro_model(self, progress_callback=None):
        """Download Kokoro ONNX model and voices.json."""
        # Note: These URLs need to be valid. Kokoro-82M on HuggingFace is common.
        # This is a placeholder for actual Kokoro model URLs.
        files = {
            "kokoro-v0_19.onnx": "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v0_19.onnx",
            "voices.json": "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices.json"
        }
        
        for f, url in files.items():
            dest = os.path.join(self.models_dir, f)
            if not os.path.exists(dest):
                print(f"DEBUG: Downloading {url} to {dest}")
                if progress_callback: progress_callback(f"Downloading {f}...")
                try:
                    subprocess.run(['curl', '-L', '-o', dest, url], check=True)
                except Exception as e:
                    print(f"DEBUG: Failed to download {f}: {e}")
                    if progress_callback: progress_callback(f"Failed: {f}")
                    return False
        if progress_callback: progress_callback("Kokoro ready!")
        return True

    def download_piper_model(self, model_name: str, progress_callback=None):
        """Download a piper model and its config."""
        base_url = "https://github.com/rhasspy/piper-voices/releases/download/v1.0.0/"
        files = [f"{model_name}.onnx", f"{model_name}.onnx.json"]
        
        for f in files:
            url = base_url + f
            dest = os.path.join(self.models_dir, f)
            if not os.path.exists(dest):
                print(f"DEBUG: Downloading {url} to {dest}")
                if progress_callback: progress_callback(f"Downloading {f}...")
                try:
                    subprocess.run(['curl', '-L', '-o', dest, url], check=True)
                except Exception as e:
                    print(f"DEBUG: Failed to download {f}: {e}")
                    if progress_callback: progress_callback(f"Failed: {f}")
                    return False
        if progress_callback: progress_callback("Voice ready!")
        return True

    def _generate_kokoro(self, text: str, filepath: str, voice_id: str) -> str:
        """Generate audio using Kokoro neural TTS."""
        if Kokoro is None:
            print("DEBUG: kokoro-onnx not installed")
            return self._generate_piper(text, filepath, "de_DE-thorsten-medium")
            
        model_path = os.path.join(self.models_dir, "kokoro-v0_19.onnx")
        voice_path = os.path.join(self.models_dir, "voices.json")
        
        if not os.path.exists(model_path):
            print(f"DEBUG: Kokoro model not found at {model_path}")
            return self._generate_piper(text, filepath, "de_DE-thorsten-medium")

        try:
            kokoro = Kokoro(model_path, voice_path)
            # Kokoro voice IDs are like 'de_male' or 'de_female'
            # We map our voice_id to kokoro's
            v_map = {
                "kokoro:de_male": "de_male",
                "kokoro:de_female": "de_female"
            }
            v = v_map.get(voice_id, "de_male")
            samples, sample_rate = kokoro.create(text, voice=v, speed=1.0, lang="de")
            
            import soundfile as sf
            sf.write(filepath, samples, sample_rate)
        except Exception as e:
            print(f"DEBUG: Kokoro failed: {e}")
            return self._generate_piper(text, filepath, "de_DE-thorsten-medium")
            
        return filepath

    def _generate_piper(self, text: str, filepath: str, model_name: str) -> str:
        """Generate audio using Piper neural TTS."""
        model_path = os.path.join(self.models_dir, f"{model_name}.onnx")
        if not os.path.exists(model_path):
            print(f"DEBUG: Piper model {model_name} not found, falling back to espeak")
            return self._generate_offline(text, filepath)
        
        cmd = ['piper', '-m', model_path, '-f', filepath]
        print(f"DEBUG: Running Piper TTS: {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.communicate(input=text.encode('utf-8'))
            if proc.returncode != 0:
                raise Exception(f"Piper failed with return code {proc.returncode}")
        except Exception as e:
            print(f"DEBUG: Piper failed: {e}, falling back to espeak")
            return self._generate_offline(text, filepath)
        
        return filepath

    def _generate_offline(self, text: str, filepath: str, voice_id: str = None):
        # espeak-ng only does wav natively with -w
        if not filepath.endswith('.wav'): filepath = filepath.replace('.mp3', '.wav')
        # Use voice_id if provided, else dialect-based default with male variant
        v = voice_id if voice_id else self._get_espeak_voice() + "+m3"  # m3 is a male variant
        # Improved parameters for better quality:
        # -s 150: slightly slower speed for clarity
        # -p 50: normal pitch
        # -a 100: normal amplitude
        cmd = ['espeak-ng', '-v', v, '-s', '150', '-p', '50', '-a', '100', '-w', filepath, text]
        print(f"DEBUG: Running offline TTS: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"DEBUG: espeak-ng failed: {result.stderr}")
            raise Exception(f"espeak-ng failed: {result.stderr}")
        return filepath

    def _generate_online(self, text: str, filepath: str, voice_accent: str = None):
        print(f"DEBUG: Running online TTS (gTTS) with accent={voice_accent}")
        # Use specified accent/tld or default to 'de'
        tld = voice_accent if voice_accent else 'de'
        # gTTS uses tld parameter for different accents
        if tld == 'de-at':
            gTTS(text=text, lang='de', tld='at').save(filepath)
        elif tld == 'de-ch':
            gTTS(text=text, lang='de', tld='ch').save(filepath)
        else:
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
            
        if not recognized_text or recognized_text.startswith("["): 
            return {"error": recognized_text if recognized_text else "Could not recognize speech"}
        
        # Calculate scores
        # 1. Text-based score (fuzzy match)
        text_score = distance.Levenshtein.normalized_similarity(target_text.lower(), recognized_text.lower())
        
        # 2. Phoneme-based score (IPA distance)
        target_ipa = self.get_ipa(target_text)
        actual_ipa = self.get_ipa(recognized_text)
        
        if target_ipa and actual_ipa:
            # We use normalized Levenshtein on IPA strings for stricter phonetic assessment
            ipa_score = distance.Levenshtein.normalized_similarity(target_ipa, actual_ipa)
            # Weighted combine: IPA counts more for "strictness"
            combined_score = (0.3 * text_score) + (0.7 * ipa_score)
        else:
            combined_score = text_score

        return {
            "target": target_text,
            "actual": recognized_text,
            "score": int(combined_score * 100),
            "target_ipa": target_ipa,
            "actual_ipa": actual_ipa
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
            lang = self.dialect.split('-')[0]
            return r.recognize_pocketsphinx(audio, language=lang)
        except sr.UnknownValueError:
            return "[Offline ASR: No speech detected or not understood]"
        except sr.RequestError as e:
            return f"[Offline ASR: Pocketsphinx error (missing {self.dialect} model?)]"
        except Exception as e:
            return f"[Offline ASR failed: {str(e)}]"
