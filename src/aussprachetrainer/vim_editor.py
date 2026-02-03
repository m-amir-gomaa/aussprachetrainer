import customtkinter as ctk
import tkinter as tk
import os
import sys

# Attempt to import the compiled Zep module
try:
    from . import zep_vim
except ImportError:
    try:
        import zep_vim
    except ImportError:
        # Fallback/Mock for development if not compiled yet
        class MockZep:
            def __init__(self):
                self.text = ""
                self.mode = "NORMAL"
            def handle_key(self, key, mods):
                if self.mode == "INSERT":
                    if key == "Escape": self.mode = "NORMAL"
                    elif key == "Return": self.text += "\n"
                    elif key == "BackSpace": self.text = self.text[:-1]
                    elif len(key) == 1: self.text += key
                else:
                    if key == "i": self.mode = "INSERT"
            def get_text(self): return self.text
            def set_text(self, t): self.text = t
            def get_mode(self): return self.mode
            def get_cursor(self): return (0, 0)
        
        class zep_vim:
            ZepVim = MockZep

class VimEditor(ctk.CTkFrame):
    def __init__(self, master, on_submit=None, on_key_release=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_submit = on_submit
        self.on_key_release = on_key_release
        
        self.zep = zep_vim.ZepVim()
        
        # Use a canvas for rendering
        # Use a canvas for rendering
        self.canvas = tk.Canvas(self, bg="#151515", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<FocusIn>", self._on_focus_in)
        
        self.font = ("Roboto Mono", 16)
        self.cursor_visible = True
        self._blink_cursor()
        self._render_vimbuffer()

    def _blink_cursor(self):
        if self.zep.get_mode() == "INSERT":
            self.cursor_visible = not self.cursor_visible
        else:
            self.cursor_visible = True
        self._render_vimbuffer()
        self.after(500, self._blink_cursor)


    def _sync_from_system_clipboard(self):
        try:
            sys_clip = self.clipboard_get()
            if sys_clip:
                self.zep.set_clipboard(sys_clip)
        except:
            pass

    def _sync_to_system_clipboard(self):
        new_clip = self.zep.get_clipboard()
        try:
            # We use a try-except to handle cases where clipboard might be locked
            # but we also check if we actually need to update to avoid infinite loops if it were bidirectional
            # For now, we trust Zep's internal state as the source of truth after a command.
            if new_clip:
                self.clipboard_clear()
                self.clipboard_append(new_clip)
                self.update() # Force processing of clipboard events
        except:
            pass

    def _on_focus_in(self, event):
        self._sync_from_system_clipboard()
        self._render_vimbuffer()

    def _on_key_press(self, event):
        app = self.winfo_toplevel()
        key = event.keysym
        # Handle Submit (Ctrl+Enter)
        if key == "Return" and (event.state & 0x4):
            if self.on_submit:
                self.on_submit()
            return "break"
            
        # Handle Alt+Key for German Umlauts in Insert Mode
        is_alt = bool(event.state & (0x8 | 0x80 | 0x20000))
        if self.zep.get_mode() == "INSERT" and is_alt:
            # ... (umlaut logic remains same)
            if key in ("s", "S"):
                text = self.zep.get_text()
                row, col = self.zep.get_cursor()
                lines = text.split("\n")
                if row < len(lines):
                    line_bytes = lines[row].encode("utf-8")
                    if col > 0 and line_bytes[col-1:col] == key.encode("utf-8"):
                        self.zep.handle_key("BackSpace", 0)
                        self.zep.handle_key("ß" if key == "s" else "ẞ", 0)
                        self._render_vimbuffer()
                        return "break"
                self.zep.handle_key(key, 0)
                self._render_vimbuffer()
                return "break"

            umlaut_map = {"a": "ä", "A": "Ä", "o": "ö", "O": "Ö", "u": "ü", "U": "Ü"}
            if key in umlaut_map:
                self.zep.handle_key(umlaut_map[key], 0)
                self._render_vimbuffer()
                return "break"

        # Map some common keys
        key_map = {
            "comma": ",", "period": ".", "semicolon": ":", "colon": ":",
            "slash": "/", "question": "?", "backslash": "\\",
            "bracketleft": "[", "bracketright": "]", "braceleft": "{", "braceright": "}",
            "minus": "-", "equal": "=", "plus": "+", "underscore": "_",
            "space": " ", "quotedbl": '"', "quoteright": "'",
            "Left": "h", "Right": "l", "Up": "k", "Down": "j", "dollar": "$",
        }
        mapped_key = key_map.get(key, key)
        
        if self.on_key_release and (event.state & 0x4) and key in ("n", "p"):
            return 
            
        is_ctrl = bool(event.state & 0x4)
        is_alt = bool(event.state & (0x8 | 0x80 | 0x20000))
        
        if is_alt and key == "r":
            return
            
        # GUI Shortcuts (Ctrl+C, V, X, A, Z, Y)
        if is_ctrl:
            if key == "a":
                self.zep.select_all()
                self._render_vimbuffer()
                return "break"
            elif key == "c":
                self.zep.yank_selection()
                self._sync_to_system_clipboard()
                self._render_vimbuffer()
                return "break"
            elif key == "v":
                self._sync_from_system_clipboard()
                sys_clip = self.zep.get_clipboard()
                if sys_clip:
                    self.zep.paste_at_cursor(sys_clip)
                self._render_vimbuffer()
                return "break"
            elif key == "x":
                self.zep.delete_selection()
                self._sync_to_system_clipboard()
                self._render_vimbuffer()
                return "break"
            elif key == "z":
                self.zep.undo()
                self._render_vimbuffer()
                return "break"
            elif key == "Z": # Ctrl+Shift+Z
                self.zep.redo()
                self._render_vimbuffer()
                return "break"
            elif key == "y":
                self.zep.redo()
                self._render_vimbuffer()
                return "break"

        if is_ctrl and key in ("h", "p", "Return", "n"):
            if key == "n" and not getattr(app, "suggestions", None):
                pass 
            else:
                return 
            
        if key == "Return" and getattr(app, "suggestions", None):
            return "break"

        # Normal mode paste (p, P) syncs FROM system first
        if not is_ctrl and mapped_key in ("p", "P"):
            self._sync_from_system_clipboard()

        # Process key in Zep
        self.zep.handle_key(mapped_key, event.state)
        
        # After any key, if it might have changed clipboard, sync TO system
        # (Actually we can just always check if Zep's clipboard changed)
        # But to be safe and robust, we sync any time Zep's internal clipboard is updated.
        self._sync_to_system_clipboard()

        self._render_vimbuffer()
        return "break"
        
    def _on_key_release(self, event):
        # Allow Tab to pass through for focus navigation
        if event.keysym in ("Tab", "ISO_Left_Tab"):
            return
        if self.on_key_release:
            self.on_key_release(event)

    def _render_vimbuffer(self):
        self.canvas.delete("all")
        text = self.zep.get_text()
        mode = self.zep.get_mode()
        cursor_pos = self.zep.get_cursor() # (row, col)
        
        import tkinter.font as tkfont
        f = tkfont.Font(family="Roboto Mono", size=16)
        char_w = f.measure("m")
        line_h = f.metrics("linespace")

        # Render text
        # Render text
        self.canvas.create_text(10, 10, anchor="nw", text=text, fill="#E1E1E1", font=self.font)
        
        # Render Status Line
        h = self.winfo_height()
        if h < 20: h = 200
        
        status_color = "#7E97AB" if mode == "INSERT" else "#BAD7FF"
        self.canvas.create_rectangle(0, h-25, self.winfo_width(), h, fill="#171717", outline="")
        self.canvas.create_text(10, h-22, anchor="nw", text=f"-- {mode} --", fill=status_color, font=("Roboto Mono", 10, "bold"))

        # Render Cursor
        lines = text.split("\n")
        cur_row, cur_col = cursor_pos
        
        # Calculate precise X by measuring prefix of current line
        prefix = ""
        if cur_row < len(lines):
            line_str = lines[cur_row]
            # Convert python string to utf-8 bytes to match C++ cursor_col (which is byte offset)
            line_bytes = line_str.encode("utf-8")
            if cur_col <= len(line_bytes):
                # Slice bytes then decode back to string to measure partial width
                prefix_bytes = line_bytes[:cur_col]
                prefix = prefix_bytes.decode("utf-8", "ignore")
            else:
                 prefix = line_str
        
        cur_x = 10 + f.measure(prefix)
        cur_y = 10 + cur_row * line_h
        
        if mode in ("VISUAL", "VISUAL_LINE"):
            anchor_pos = self.zep.get_anchor()
            start_row, start_col = anchor_pos
            end_row, end_col = cursor_pos
            if (start_row, start_col) > (end_row, end_col):
                (start_row, start_col), (end_row, end_col) = (end_row, end_col), (start_row, start_col)
            
            # Opaque selection rendering with visible text
            for r in range(start_row, min(end_row + 1, len(lines))):
                r_text = lines[r]
                if mode == "VISUAL_LINE":
                    c_start = 0
                    c_end = len(r_text)
                else:
                    c_start = start_col if r == start_row else 0
                    c_end = end_col if r == end_row else len(r_text)
                
                x_start = 10 + f.measure(r_text[:c_start])
                x_end = 10 + f.measure(r_text[:c_end + 1])
                y = 10 + r * line_h
                # Opaque background
                self.canvas.create_rectangle(x_start, y, x_end, y + line_h, fill="#373737", outline="")
                # Re-render selected text on top in white for visibility
                selected_text = r_text[c_start:c_end + 1] if c_end < len(r_text) else r_text[c_start:]
                if selected_text:
                    self.canvas.create_text(x_start, y, anchor="nw", text=selected_text, 
                                          fill="#E1E1E1", font=self.font)

        if mode == "INSERT":
            if self.cursor_visible:
                # Slimmer bar (1 pixel)
                self.canvas.create_rectangle(cur_x, cur_y, cur_x+1, cur_y+line_h, fill="#E1E1E1", outline="")
        else: # NORMAL / VISUAL
            # Fully opaque block cursor WITH character underneath
            char_under_cursor = " "
            if cur_row < len(lines) and cur_col < len(lines[cur_row]):
                 char_under_cursor = lines[cur_row][cur_col]
            
            # Measure specific character width
            if char_under_cursor == "\t":
                # Tab handling is tricky without expanding, but let's approximate or just use a space width for cursor
                # In Tkinter text, tabs are usually 8 spaces, but here we just render raw strings? 
                # Tkinter canvas text handles tabs, but measuring single char '\t' might return 0 or weird.
                # Let's assume standard width for now or just 'm' width if it's a control char
                block_w = f.measure("    ") # Approximate tab as 4 spaces? Or just 'm'? 
                # Actually, standard visual cursor on tab highlights the whole tab width.
                # For now, let's stick to 'm' width for non-printable/tabs to be safe, or measure space.
                block_w = f.measure(" ") * 4 
            else:
                block_w = f.measure(char_under_cursor)
                if block_w == 0: block_w = f.measure("m") # Fallback for zero-width chars
            
            # Draw cursor block
            self.canvas.create_rectangle(cur_x, cur_y, cur_x+block_w, cur_y+line_h, fill="#D0D0D0", outline="")
            
            # Draw character on top of cursor in background color (reverse video effect)
            if char_under_cursor.strip(): # Only draw if it's visible char
                self.canvas.create_text(cur_x, cur_y, anchor="nw", text=char_under_cursor, fill="#151515", font=self.font)

    def get_text(self):
        return self.zep.get_text()

    def set_text(self, text):
        self.zep.set_text(text)
        self._render_vimbuffer()

    def replace_current_word(self, word):
        self.zep.replace_current_word(word)
        self._render_vimbuffer()

    def focus_set(self):
        self.canvas.focus_set()
