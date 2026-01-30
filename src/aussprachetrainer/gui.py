import customtkinter as ctk
import threading
import os
from typing import List, Dict, Optional
from aussprachetrainer.backend import PronunciationBackend
from aussprachetrainer.autocomplete import WordSuggester

# Set appearance and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class HistoryItem(ctk.CTkFrame):
    def __init__(self, master, entry_id, text, ipa, audio_path, play_callback, delete_callback, font_size, **kwargs):
        super().__init__(master, **kwargs)
        self.entry_id = entry_id
        self.audio_path = audio_path
        
        # Text and IPA
        self.label = ctk.CTkLabel(self, text=f"\"{text}\" \n[{ipa}]", 
                                  anchor="w", justify="left",
                                  font=ctk.CTkFont(size=font_size-2))
        self.label.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        
        # Action Buttons Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="right", padx=5)

        # Play Button
        self.play_button = ctk.CTkButton(btn_frame, text="▶", width=30, 
                                         command=lambda: play_callback(self.audio_path))
        self.play_button.pack(side="left", padx=2)
        
        # Delete Button
        self.delete_button = ctk.CTkButton(btn_frame, text="🗑", width=30, fg_color="#AA4444", 
                                           hover_color="#CC6666",
                                           command=lambda: delete_callback(self.entry_id, self))
        self.delete_button.pack(side="left", padx=2)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # State
        self.font_size = 14
        self.backend = PronunciationBackend()
        self.suggester = WordSuggester()
        
        # Window Setup
        self.title("GermanPronun Advanced")
        self.geometry("1100x700")
        
        # Layout
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)
        
        self._create_sidebar()
        self._create_main_area()
        self._create_history_panel()
        
        # Autocomplete State
        self.suggestions = []
        self.suggestion_index = -1
        self.suggestion_window = None
        
        self._load_voices()
        self._refresh_history()
        
        # Global Bindings
        self.bind('<Control-Return>', lambda e: self.generate())
        self.bind('<F5>', lambda e: self.generate())

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="GermanPronun", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Settings Section
        ctk.CTkLabel(self.sidebar, text="--- SETTINGS ---", text_color="gray").grid(row=1, column=0, pady=(20, 5))
        
        # Font Size
        ctk.CTkLabel(self.sidebar, text="Font Size:", anchor="w").grid(row=2, column=0, padx=20, sticky="w")
        self.font_slider = ctk.CTkSlider(self.sidebar, from_=10, to_=30, number_of_steps=20, command=self._update_font_size)
        self.font_slider.set(self.font_size)
        self.font_slider.grid(row=3, column=0, padx=20, pady=(0, 10))
        
        # Mode Toggle
        ctk.CTkLabel(self.sidebar, text="Mode:", anchor="w").grid(row=4, column=0, padx=20, sticky="w")
        self.mode_switch = ctk.CTkOptionMenu(self.sidebar, values=["Online", "Offline"], dynamic_resizing=False)
        self.mode_switch.grid(row=5, column=0, padx=20, pady=(0, 10))
        
        # Voice Selection
        ctk.CTkLabel(self.sidebar, text="Voice (Offline):", anchor="w").grid(row=6, column=0, padx=20, sticky="w")
        self.voice_option = ctk.CTkOptionMenu(self.sidebar, values=["Loading..."], dynamic_resizing=False)
        self.voice_option.grid(row=7, column=0, padx=20, pady=(0, 10))
        
        # Transparency Info
        ctk.CTkLabel(self.sidebar, text="--- SYSTEM INFO ---", text_color="gray").grid(row=8, column=0, pady=(20, 5))
        self.model_info = ctk.CTkLabel(self.sidebar, text="TTS: gTTS / espeak\nASR: Google / Vosk", 
                                       font=ctk.CTkFont(size=10), justify="left")
        self.model_info.grid(row=9, column=0, padx=20, sticky="w")

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Input Section
        self.input_label = ctk.CTkLabel(self.main_frame, text="German Input:", font=ctk.CTkFont(size=14, weight="bold"))
        self.input_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.input_text = ctk.CTkTextbox(self.main_frame, height=150)
        self.input_text.grid(row=1, column=0, sticky="nsew", pady=10)
        self.input_text.focus_set()
        self.input_text.bind('<KeyRelease>', self._on_key_release)
        self.input_text.bind('<Tab>', self._on_tab_press)
        self.input_text.bind('<Return>', self._on_return_press)
        self.input_text.bind('<Escape>', self._close_suggestions)
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=10)
        btn_frame.grid_columnconfigure((0,1), weight=1)

        self.generate_button = ctk.CTkButton(btn_frame, text="Speak & IPA (F5)", 
                                            command=self.generate, height=40)
        self.generate_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.record_button = ctk.CTkButton(btn_frame, text="🎤 Start Recording", 
                                           command=self.toggle_recording, height=40, fg_color="#338833")
        self.record_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # IPA Output
        self.ipa_card = ctk.CTkFrame(self.main_frame)
        self.ipa_card.grid(row=3, column=0, sticky="ew", pady=10)
        self.ipa_display = ctk.CTkLabel(self.ipa_card, text="[ IPA ]", font=ctk.CTkFont(family="Courier", size=24))
        self.ipa_display.pack(padx=10, pady=20, fill="x")
        
        # Assessment Output
        self.assess_card = ctk.CTkFrame(self.main_frame, fg_color="#2A2A2A")
        self.assess_card.grid(row=4, column=0, sticky="ew", pady=10)
        self.assess_label = ctk.CTkLabel(self.assess_card, text="Pronunciation Score: --%", font=ctk.CTkFont(size=16, weight="bold"))
        self.assess_label.pack(padx=10, pady=10)
        self.transcription_label = ctk.CTkLabel(self.assess_card, text="You said: ...", text_color="gray")
        self.transcription_label.pack(padx=10, pady=(0, 10))
        
        # Status
        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.status_label.grid(row=5, column=0, sticky="w")

    def _create_history_panel(self):
        self.history_frame = ctk.CTkFrame(self, width=350)
        self.history_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 20), pady=20)
        self.history_frame.grid_rowconfigure(2, weight=1)
        
        self.history_label = ctk.CTkLabel(self.history_frame, text="History Buffer", font=ctk.CTkFont(size=16, weight="bold"))
        self.history_label.grid(row=0, column=0, padx=10, pady=10)
        
        # Search Bar
        self.search_entry = ctk.CTkEntry(self.history_frame, placeholder_text="Search history...")
        self.search_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.search_entry.bind('<KeyRelease>', lambda e: self._refresh_history())
        
        self.history_scroll = ctk.CTkScrollableFrame(self.history_frame)
        self.history_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

    # --- Logic ---

    def _load_voices(self):
        voices = self.backend.get_voices()
        self.voices_map = {v['name']: v['id'] for v in voices}
        de_voices = [v['name'] for v in voices if v['is_german']]
        other_voices = [v['name'] for v in voices if not v['is_german']]
        sorted_names = de_voices + other_voices
        self.voice_option.configure(values=sorted_names)
        if de_voices: self.voice_option.set(de_voices[0])

    def _update_font_size(self, val):
        self.font_size = int(val)
        new_font = ctk.CTkFont(size=self.font_size)
        self.input_text.configure(font=new_font)
        self.generate_button.configure(font=new_font)
        self.record_button.configure(font=new_font)
        self._refresh_history()

    def generate(self):
        text = self.input_text.get("1.0", "end-1c").strip()
        if not text: return
        is_online = self.mode_switch.get() == "Online"
        voice_id = self.voices_map.get(self.voice_option.get())
        
        self.status_label.configure(text="Generating...", text_color="blue")
        def work():
            ipa = self.backend.get_ipa(text)
            filepath = self.backend.generate_audio(text, online=is_online, voice_id=voice_id)
            self.backend.db.add_entry(text, ipa, filepath, self.mode_switch.get(), voice_id)
            self.after(0, lambda: self.ipa_display.configure(text=ipa))
            self.after(0, self._refresh_history)
            self.backend.play_file(filepath)
            self.after(0, lambda: self.status_label.configure(text="Ready", text_color="gray"))
        threading.Thread(target=work, daemon=True).start()

    def toggle_recording(self):
        if not self.backend.recording:
            self.backend.start_recording()
            self.record_button.configure(text="⏹ Stop Recording", fg_color="#AA4444")
            self.status_label.configure(text="Recording...", text_color="red")
        else:
            wav_path = self.backend.stop_recording()
            self.record_button.configure(text="🎤 Start Recording", fg_color="#338833")
            self.status_label.configure(text="Assessing...", text_color="blue")
            
            target = self.input_text.get("1.0", "end-1c").strip()
            online = self.mode_switch.get() == "Online"
            
            def assess():
                result = self.backend.assess_pronunciation(target, wav_path, online=online)
                self.after(0, lambda: self._show_assessment(result))
            threading.Thread(target=assess, daemon=True).start()

    def _show_assessment(self, result):
        if "error" in result:
            self.assess_label.configure(text=f"Error: {result['error']}", text_color="red")
        else:
            self.assess_label.configure(text=f"Score: {result['score']}%", 
                                        text_color="#44FF44" if result['score'] > 80 else "#FFFF44")
            self.transcription_label.configure(text=f"You said: {result['actual']}")
        self.status_label.configure(text="Ready", text_color="gray")

    def _refresh_history(self):
        query = self.search_entry.get()
        entries = self.backend.db.get_history(search_query=query if query else None)
        
        for w in self.history_scroll.winfo_children(): w.destroy()
        
        for e in entries:
            HistoryItem(self.history_scroll, e['id'], e['text'], e['ipa'], e['audio_path'],
                        self.backend.play_file, self._delete_entry, self.font_size).pack(fill="x", pady=2, padx=5)

    def _delete_entry(self, entry_id, widget):
        self.backend.db.delete_entry(entry_id)
        widget.destroy()

    # --- Autocomplete Hooks ---
    def _on_key_release(self, event):
        if event.keysym in ("Tab", "Return", "Escape"): return
        text = self.input_text.get("1.0", "insert").split()
        if not text: self._close_suggestions(); return
        self.suggestions = self.suggester.get_suggestions(text[-1])
        if self.suggestions: self._show_suggestions()
        else: self._close_suggestions()

    def _show_suggestions(self):
        if not self.suggestion_window or not self.suggestion_window.winfo_exists():
            self.suggestion_window = ctk.CTkToplevel(self)
            self.suggestion_window.overrideredirect(True)
            self.suggestion_window.attributes("-topmost", True)
            self.suggestion_frame = ctk.CTkFrame(self.suggestion_window, border_width=1)
            self.suggestion_frame.pack(fill="both", expand=True)

        for w in self.suggestion_frame.winfo_children(): w.destroy()
        self.suggestion_labels = []
        for i, s in enumerate(self.suggestions):
            lbl = ctk.CTkLabel(self.suggestion_frame, text=s, anchor="w", padx=10)
            lbl.pack(fill="x")
            self.suggestion_labels.append(lbl)
        self.suggestion_index = -1
        self._position_suggestions()

    def _position_suggestions(self):
        x = self.input_text.winfo_rootx() + 10
        y = self.input_text.winfo_rooty() + self.input_text.winfo_height() - 20
        self.suggestion_window.geometry(f"+{x}+{y}")
        self.suggestion_window.deiconify()

    def _on_tab_press(self, event):
        if not self.suggestions: return
        self.suggestion_index = (self.suggestion_index + 1) % len(self.suggestions)
        for i, lbl in enumerate(self.suggestion_labels):
            lbl.configure(fg_color=("gray75", "gray25") if i == self.suggestion_index else "transparent")
        return "break"

    def _on_return_press(self, event):
        if self.suggestion_window and self.suggestion_window.winfo_viewable() and self.suggestion_index >= 0:
            word = self.suggestions[self.suggestion_index]
            content = self.input_text.get("1.0", "insert").split()
            content[-1] = word
            self.input_text.delete("1.0", "insert")
            self.input_text.insert("1.0", " ".join(content) + " ")
            self._close_suggestions()
            return "break"

    def _close_suggestions(self, event=None):
        if self.suggestion_window: self.suggestion_window.withdraw()
        self.suggestions = []

if __name__ == "__main__":
    app = App()
    app.mainloop()
