#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <vector>

// Note: In a real implementation, we would include Zep headers here.
// Since Zep is a header-only library with many dependencies (like SDL/Qt for rendering),
// we will implement a slightly higher-level wrapper that manages the editor state
// and returns display data for the Canvas to render.

namespace py = pybind11;

class ZepVim {
public:
    ZepVim() {
        text = "";
        cursor_row = 0;
        cursor_col = 0;
        anchor_row = 0;
        anchor_col = 0;
        mode = "NORMAL";
        pending_operator = "";
        pending_count = 1;
        count_str = "";
        prev_key = ""; // Initialize prev_key
    }

    void handle_key(const std::string& key, int modifiers) {
        last_key = prev_key;
        prev_key = key;

        if (mode == "NORMAL") handle_normal_mode(key, modifiers);
        else if (mode == "INSERT") handle_insert_mode(key, modifiers);
        else if (mode == "VISUAL" || mode == "VISUAL_LINE") handle_visual_mode(key, modifiers);
        else if (mode == "REPLACE") handle_replace_mode(key, modifiers);
    }

    std::string get_text() const { return text; }
    void set_text(const std::string& new_text) { text = new_text; update_cursor_bounds(); }
    std::string get_mode() const { return mode; }
    std::pair<int, int> get_cursor() const { return {cursor_row, cursor_col}; }
    std::pair<int, int> get_anchor() const { return {anchor_row, anchor_col}; }

private:
    std::string text;
    std::string mode;
    std::string last_key;
    std::string prev_key;
    std::string pending_operator;
    int pending_count;
    std::string count_str;
    std::string clipboard;
    int cursor_row, cursor_col;
    int anchor_row, anchor_col;
    std::vector<std::string> undo_stack;
    std::vector<std::string> redo_stack;

    int get_count() {
        if (count_str.empty()) return 1;
        int c = std::stoi(count_str);
        count_str = "";
        return c;
    }

    void save_undo() {
        if (undo_stack.empty() || undo_stack.back() != text) {
            undo_stack.push_back(text);
            redo_stack.clear();
        }
    }

    // Helper for UTF-8 character length
    int get_utf8_len(unsigned char c) {
        if ((c & 0x80) == 0) return 1;
        if ((c & 0xE0) == 0xC0) return 2;
        if ((c & 0xF0) == 0xE0) return 3;
        if ((c & 0xF8) == 0xF0) return 4;
        return 1; // Invalid or fallback
    }

    void handle_insert_mode(const std::string& key, int modifiers) {
        if (key == "Escape" || (key == "j" && last_key == "j")) {
            if (key == "j") {
                // Fix jj bug: remove the first j precisely where it was inserted
                size_t pos = get_cursor_pos();
                if (pos > 0 && text[pos-1] == 'j') {
                    text.erase(pos - 1, 1);
                    cursor_col--;
                }
            } else if (key == "Escape") {
                // Standard Vim behavior: cursor moves back one character when exiting insert mode
                // Need to move back one UTF-8 char
                size_t pos = get_cursor_pos(); 
                if (pos > 0) {
                     move_cursor(0, -1);
                }
            }
            mode = "NORMAL";
            save_undo();
            return;
        }

        if (key == "Return") {
            insert_at_cursor("\n");
            cursor_row++;
            cursor_col = 0;
        } else if (key == "BackSpace") {
            delete_at_cursor(true);
        } else if (key == "Tab") {
            // Handled by GUI
        } else {
             // Allow single char or multi-byte keys (if not control key)
             // Control keys usually have length > 1 and start with ASCII text.
             // UTF-8 multibyte starts with > 127.
             if (key.length() == 1 || (key.length() > 1 && (unsigned char)key[0] > 127)) {
                insert_at_cursor(key);
                cursor_col += key.length();
             }
        }
    }

    void handle_replace_mode(const std::string& key, int modifiers) {
        if (key == "Escape") { mode = "NORMAL"; save_undo(); return; }
        if (key.length() == 1) {
            size_t pos = get_cursor_pos();
            if (pos < text.length() && text[pos] != '\n') {
                text[pos] = key[0];
                cursor_col++;
            } else {
                insert_at_cursor(key);
                cursor_col++;
            }
        }
    }

    void handle_normal_mode(const std::string& key, int modifiers) {
        // Multipliers
        if (isdigit(key[0]) && (key[0] != '0' || !count_str.empty())) {
            count_str += key;
            return;
        }

        int count = get_count();

        // Replacement handling for 'r'
        if (pending_operator == "r") {
            if (key.length() == 1) {
                save_undo();
                for (int i=0; i<pending_count; ++i) {
                    size_t pos = get_cursor_pos();
                    if (pos < text.length() && text[pos] != '\n') {
                        text[pos] = key[0];
                        if (i < pending_count - 1) move_cursor(0, 1);
                    }
                }
            }
            pending_operator = "";
            pending_count = 1;
            update_cursor_bounds();
            return;
        }

        // Operators that wait for motion
        if (key == "d" || key == "c" || key == "y") {
            if (pending_operator == key) { // dd, cc, yy
                int final_count = pending_count * count;
                for (int i=0; i<final_count; ++i) handle_line_operation(key);
                pending_operator = "";
                pending_count = 1;
            } else {
                pending_operator = key;
                pending_count = count;
            }
            return;
        }

        // Check for Operator + Motion execution
        // We define a lambda for the motion to handle "count" repetitions
        std::function<void(ZepVim*)> motion_func = nullptr;
        
        bool is_motion = true;
        
        if (key == "h") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_cursor(0, -1); };
        else if (key == "j") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_cursor(1, 0); };
        else if (key == "k") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_cursor(-1, 0); };
        else if (key == "l") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_cursor(0, 1); };
        else if (key == "w") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_word(1); };
        else if (key == "b") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_word(-1); };
        else if (key == "e") motion_func = [count](ZepVim* v) { for(int i=0; i<count; ++i) v->move_word_end(); };
        else if (key == "0" || key == "asciitilde") motion_func = [](ZepVim* v) { v->cursor_col = 0; };
        else if (key == "dollar" || key == "$") motion_func = [](ZepVim* v) { 
            int len = v->get_line_length(v->cursor_row);
            v->cursor_col = len > 0 ? len - 1 : 0; 
        };
        else if (key == "G") motion_func = [](ZepVim* v) { v->cursor_row = v->get_line_count() - 1; v->cursor_col = 0; };
        else if (key == "g" && last_key == "g") motion_func = [](ZepVim* v) { v->cursor_row = 0; v->cursor_col = 0; };
        else is_motion = false;

        if (is_motion && motion_func) {
             int final_count = pending_count; // Motion key's count is already baked into motion_func
             // But valid vim allows d2w or 2dw -> deleting 2 words.
             // Here we baked 'count' into motion_func. 'pending_count' is from operator.
             // Actually, usually it's product.
             // If I type `2d3w`, pending_count=2, count=3. motion_func moves 3 words.
             
             if (pending_operator != "") {
                 save_undo();
                 // Repeat the motion_func 'pending_count' times?
                 // Standard vim: 2d3w means delete 6 words.
                 // We will just execute motion_func once, assuming it handles its own count, 
                 // and we loop pending_count.
                 
                 auto combined_motion = [motion_func, final_count](ZepVim* v) {
                     for(int i=0; i<final_count; ++i) motion_func(v);
                 };

                 if (pending_operator == "y") yank_to_motion(combined_motion);
                 else delete_to_motion(combined_motion, pending_operator == "c");
                 
                 pending_operator = "";
                 pending_count = 1;
             } else {
                 motion_func(this);
             }
             return;
        }

        // Single character operations that don't take standard motions or are immediate
        int final_count = pending_count * count;
        
        if (key == "x") { save_undo(); for(int i=0; i<final_count; ++i) { yank_at_cursor(); delete_at_cursor(false); } }
        else if (key == "X") { save_undo(); for(int i=0; i<final_count; ++i) { yank_at_cursor(true); delete_at_cursor(true); } }
        else if (key == "r" && !(modifiers & 0x4)) { 
            pending_operator = "r";
            pending_count = count;
            // Wait for char
        }
        else if (key == "p") { save_undo(); for(int i=0; i<final_count; ++i) put_after(); }
        else if (key == "P") { save_undo(); for(int i=0; i<final_count; ++i) put_before(); }
        else if (key == "J") { save_undo(); for(int i=0; i<final_count; ++i) join_lines(); }
        else if (key == "D") { save_undo(); delete_to_end_of_line(); }
        
        // Substitute
        else if (key == "s") { save_undo(); yank_at_cursor(); delete_at_cursor(false); mode = "INSERT"; }
        
        // Mode switches
        else if (key == "i") { mode = "INSERT"; save_undo(); }
        else if (key == "I") { cursor_col = 0; mode = "INSERT"; save_undo(); }
        else if (key == "a") { mode = "INSERT"; move_cursor(0, 1); save_undo(); }
        else if (key == "A") { cursor_col = get_line_length(cursor_row); mode = "INSERT"; save_undo(); }
        else if (key == "o") handle_o_command(true);
        else if (key == "O") handle_o_command(false);
        else if (key == "v") { mode = "VISUAL"; anchor_row = cursor_row; anchor_col = cursor_col; }
        else if (key == "V") { mode = "VISUAL_LINE"; anchor_row = cursor_row; anchor_col = 0; }
        else if (key == "R") { mode = "REPLACE"; save_undo(); }
        
        // Undo/Redo
        else if (key == "u") perform_undo();
        else if (key == "r" && (modifiers & 0x4)) perform_redo();

        // Reset pending_count if motion was processed or invalid key
        if (pending_operator == "") pending_count = 1;
        
        // If we have a pending operator but the key wasn't a motion or operator, cancel it
        if (pending_operator != "" && !is_operator(key)) {
            pending_operator = "";
        }
    }

    void handle_visual_mode(const std::string& key, int modifiers) {
        if (key == "Escape") mode = "NORMAL";
        else if (key == "h") move_cursor(0, -1);
        else if (key == "j") move_cursor(1, 0);
        else if (key == "k") move_cursor(-1, 0);
        else if (key == "l") move_cursor(0, 1);
        else if (key == "w") move_word(1);
        else if (key == "b") move_word(-1);
        else if (key == "e") move_word_end();
        else if (key == "0") cursor_col = 0;
        else if (key == "dollar") cursor_col = get_line_length(cursor_row);
        else if (key == "G") { cursor_row = get_line_count() - 1; cursor_col = 0; }
        else if (key == "g" && last_key == "g") { cursor_row = 0; cursor_col = 0; }
        
        else if (key == "d" || key == "x") { yank_selection(); delete_selection(); mode = "NORMAL"; }
        else if (key == "c") { yank_selection(); delete_selection(); mode = "INSERT"; }
        else if (key == "y") { yank_selection(); mode = "NORMAL"; }
    }

    bool is_operator(const std::string& k) { return k == "d" || k == "c" || k == "y" || k == "r"; }

    void move_cursor(int dr, int dc) {
        // Row movement is simple row index change
        cursor_row = std::max(0, std::min((int)get_line_count() - 1, cursor_row + dr));
        
        // Column movement needs to respect UTF-8 boundaries
        // Get current line
        size_t line_start = get_pos_from_row(cursor_row);
        size_t next_nl = text.find('\n', line_start);
        size_t line_end = (next_nl == std::string::npos) ? text.length() : next_nl;
        
        // Current logical column is byte offset from line_start
        size_t current_offset = cursor_col;
        
        // If row changed, cursor_col might be invalid, clamp it first? 
        // Vim remembers 'visual column', but here we simplified.
        // We should clamp to valid UTF-8 boundary if we jumped rows.
        // But for now, let's just handle horizontal motion 'dc'
        
        if (dc != 0) {
            // We want to move 'dc' characters.
            // Scan text from current position.
            if (dc > 0) {
                 for (int i=0; i<dc; ++i) {
                     if (line_start + current_offset >= line_end) break;
                     unsigned char c = (unsigned char)text[line_start + current_offset];
                     int len = get_utf8_len(c);
                     current_offset += len;
                 }
            } else { // dc < 0
                 for (int i=0; i<-dc; ++i) {
                     if (current_offset == 0) break;
                     // Scan backwards to find start of char
                     // In valid UTF-8, continuation bytes start with 10xxxxxx (0x80..0xBF)
                     // Start bytes are 0xxxxxxx or 11xxxxxx.
                     // So we decrement until we find a byte that is NOT 10xxxxxx
                     current_offset--;
                     while (current_offset > 0 && ((unsigned char)text[line_start + current_offset] & 0xC0) == 0x80) {
                         current_offset--;
                     }
                 }
            }
        }
        
        // Re-clamp to line bounds
        if (line_start + current_offset > line_end) current_offset = line_end - line_start;
        cursor_col = current_offset;
    }

    void move_word(int dir) {
        // Simplified word movement that skips bytes
        size_t pos = get_cursor_pos();
        if (dir > 0) {
            bool found_space = false;
            while (pos < text.length()) {
                unsigned char c = (unsigned char)text[pos];
                int len = get_utf8_len(c);
                // Check if current char is space (only ASCII space support for now)
                if (len == 1 && isspace(text[pos])) found_space = true;
                else if (found_space) break;
                pos += len;
            }
        } else {
            // Backward
             if (pos > 0) {
                // Move back one char
                 pos--;
                 while (pos > 0 && ((unsigned char)text[pos] & 0xC0) == 0x80) pos--;
             }
            // Skip spaces
            while (pos > 0) {
                 unsigned char c = (unsigned char)text[pos];
                 // Check if space. Need to read char at pos.
                 // But wait, to check space we need to check char AT pos.
                 // If pos points to start of char.
                 if (get_utf8_len(c) == 1 && isspace(c)) {
                     // Move back one char
                     pos--;
                     while (pos > 0 && ((unsigned char)text[pos] & 0xC0) == 0x80) pos--;
                 } else {
                     break;
                 }
            }
            // Skip non-spaces
             while (pos > 0) {
                 // Look at previous char
                 size_t prev_pos = pos - 1;
                 while (prev_pos > 0 && ((unsigned char)text[prev_pos] & 0xC0) == 0x80) prev_pos--;
                 
                 unsigned char c = (unsigned char)text[prev_pos];
                 if (get_utf8_len(c) == 1 && isspace(c)) break;
                 pos = prev_pos;
            }
        }
        set_cursor_from_pos(pos);
    }

    void move_word_end() {
        // Simplified
        size_t pos = get_cursor_pos();
        if (pos < text.length()) {
             unsigned char c = (unsigned char)text[pos];
             pos += get_utf8_len(c);
        }
        while (pos < text.length()) {
             unsigned char c = (unsigned char)text[pos];
             if (get_utf8_len(c) == 1 && isspace(c)) pos++;
             else break;
        }
         while (pos < text.length()) {
            size_t next_pos = pos;
            unsigned char c = (unsigned char)text[pos];
            next_pos += get_utf8_len(c);
            
            if (next_pos >= text.length()) { pos = text.length()-1; break; } // End of text
            
            unsigned char next_c = (unsigned char)text[next_pos];
            if (get_utf8_len(next_c) == 1 && isspace(next_c)) break;
            pos = next_pos;
        }
        set_cursor_from_pos(pos);
    }

    void delete_to_motion(std::function<void(ZepVim*)> motion, bool change) {
        size_t start = get_cursor_pos();
        motion(this);
        size_t end = get_cursor_pos();
        if (start < end) {
            clipboard = text.substr(start, end - start);
            text.erase(start, end - start);
        } else {
            clipboard = text.substr(end, start - end);
            text.erase(end, start - end);
        }
        set_cursor_from_pos(std::min(start, end));
        if (change) mode = "INSERT";
    }

    void yank_to_motion(std::function<void(ZepVim*)> motion) {
        size_t start = get_cursor_pos();
        motion(this);
        size_t end = get_cursor_pos();
        size_t min_pos = std::min(start, end);
        size_t len = (start < end) ? (end - start) : (start - end);
        
        if (len > 0) {
            clipboard = text.substr(min_pos, len);
        }
        set_cursor_from_pos(start); // Return to start
    }

    void yank_at_cursor(bool before = false) {
        size_t pos = get_cursor_pos();
        if (before) { if(pos > 0) clipboard = text.substr(pos-1, 1); }
        else { if (pos < text.length()) clipboard = text.substr(pos, 1); }
    }

    void delete_to_end_of_line() {
        size_t start = get_cursor_pos();
        size_t end = start;
        while (end < text.length() && text[end] != '\n') end++;
        clipboard = text.substr(start, end - start);
        text.erase(start, end - start);
    }

    void get_selection_range(size_t& start, size_t& end) {
        if (mode == "VISUAL_LINE") {
            int r1 = std::min(anchor_row, cursor_row);
            int r2 = std::max(anchor_row, cursor_row);
            start = get_pos_from_row(r1);
            size_t next_start = get_pos_from_row(r2 + 1);
            end = std::min(next_start, text.length());
        } else {
            start = get_pos_from_coords(anchor_row, anchor_col);
            end = get_cursor_pos();
            if (start > end) std::swap(start, end);
            end++; // include the character at cursor
        }
    }

    void delete_selection() {
        save_undo();
        size_t start, end;
        get_selection_range(start, end);
        if (start < text.length()) {
            text.erase(start, end - start);
        }
        set_cursor_from_pos(start);
        update_cursor_bounds();
    }

    void yank_selection() {
        size_t start, end;
        get_selection_range(start, end);
        if (start < text.length()) {
            clipboard = text.substr(start, end - start);
        } else {
            clipboard = "";
        }
    }

    size_t get_pos_from_coords(int r, int c) const {
        size_t line_start = get_pos_from_row(r);
        size_t next_nl = text.find('\n', line_start);
        size_t line_end = (next_nl == std::string::npos) ? text.length() : next_nl;
        size_t pos = line_start + c;
        return std::min(pos, line_end);
    }

    void set_cursor_from_pos(size_t pos) {
        cursor_row = 0;
        cursor_col = 0;
        size_t current = 0;
        std::vector<std::string> lines = get_lines();
        for (size_t i = 0; i < lines.size(); ++i) {
            if (current + lines[i].length() >= pos) {
                cursor_row = i;
                cursor_col = pos - current;
                return;
            }
            current += lines[i].length() + 1;
        }
        cursor_row = lines.size() - 1;
        cursor_col = lines.back().length();
    }

    void handle_line_operation(const std::string& op) {
        save_undo();
        std::vector<std::string> lines = get_lines();
        if (cursor_row < lines.size()) {
            if (op == "y") {
                clipboard = lines[cursor_row] + "\n";
            } else {
                clipboard = lines[cursor_row] + "\n";
                lines.erase(lines.begin() + cursor_row);
                rebuild_text(lines);
                if (op == "c") mode = "INSERT";
            }
        }
    }

    void put_after() {
        if (clipboard.empty()) return;
        std::vector<std::string> lines = get_lines();
        if (clipboard.back() == '\n') { // Line put
            if (cursor_row < lines.size()) lines.insert(lines.begin() + cursor_row + 1, clipboard.substr(0, clipboard.length()-1));
            else lines.push_back(clipboard.substr(0, clipboard.length()-1));
            rebuild_text(lines);
            cursor_row++;
        } else { // Char put
            move_cursor(0, 1);
            insert_at_cursor(clipboard);
        }
    }

    void put_before() {
        if (clipboard.empty()) return;
        std::vector<std::string> lines = get_lines();
        if (clipboard.back() == '\n') { // Line put
            lines.insert(lines.begin() + cursor_row, clipboard.substr(0, clipboard.length()-1));
            rebuild_text(lines);
        } else {
            insert_at_cursor(clipboard);
        }
    }

    void join_lines() {
        std::vector<std::string> lines = get_lines();
        if (cursor_row < lines.size() - 1) {
            lines[cursor_row] += " " + lines[cursor_row+1];
            lines.erase(lines.begin() + cursor_row + 1);
            rebuild_text(lines);
        }
    }

    void rebuild_text(const std::vector<std::string>& lines) {
        text = "";
        for (size_t i = 0; i < lines.size(); ++i) {
            text += lines[i];
            if (i < lines.size() - 1) text += "\n";
        }
        update_cursor_bounds();
    }

    void perform_undo() {
        if (!undo_stack.empty()) {
            redo_stack.push_back(text);
            text = undo_stack.back();
            undo_stack.pop_back();
            update_cursor_bounds();
        }
    }

    void perform_redo() {
        if (!redo_stack.empty()) {
            undo_stack.push_back(text);
            text = redo_stack.back();
            redo_stack.pop_back();
            update_cursor_bounds();
        }
    }

    void insert_at_cursor(const std::string& s) {
        size_t pos = get_cursor_pos();
        text.insert(pos, s);
    }

    void delete_at_cursor(bool back) {
        size_t pos = get_cursor_pos();
        if (back && pos > 0) {
            // BACKSPACE: Delete char BEFORE cursor
            // Find start of previous char
            size_t prev_pos = pos - 1;
            while (prev_pos > 0 && ((unsigned char)text[prev_pos] & 0xC0) == 0x80) prev_pos--;
            
            size_t char_len = pos - prev_pos;
            text.erase(prev_pos, char_len);
            
            // Adjust cursor_col
            cursor_col -= char_len;
            
            // If we wrapped across lines (not possible with pure delete_at_cursor logic in single line usually? 
            // Wait, get_cursor_pos calculates linear pos. 
            // But if backspace merges lines, we handle that in handle_insert_mode or assume backspace deletes \n?
            // The original logic just did text.erase(pos-1, 1).
            // If pos-1 was \n, it merged lines.
            // Our logic handles \n (1 byte) correctly as char_len=1.
            // But cursor_col adjustment is tricky if line wrap.
            // Simplified: recompute cursor_col if row changed.
            // But usually backspace on char keeps row same.
            
        } else if (!back && pos < text.length()) {
            // Delete char AT cursor (x)
             unsigned char c = (unsigned char)text[pos];
             int len = get_utf8_len(c);
             text.erase(pos, len);
             // Cursor stays at pos, but if we deleted last char, it might be out of bounds.
             update_cursor_bounds();
        }
    }

    size_t safe_pos(size_t p) const {
        return std::min(p, text.length());
    }

    size_t get_pos_from_row(int row) const {
        size_t pos = 0;
        size_t len = text.length();
        for (int i = 0; i < row && pos < len; ++i) {
            size_t next_nl = text.find('\n', pos);
            if (next_nl == std::string::npos) return len;
            pos = next_nl + 1;
        }
        return std::min(pos, len);
    }

    size_t get_cursor_pos() const {
        size_t line_start = get_pos_from_row(cursor_row);
        size_t next_nl = text.find('\n', line_start);
        size_t line_end = (next_nl == std::string::npos) ? text.length() : next_nl;
        
        size_t pos = line_start + cursor_col;
        return std::min(pos, line_end);
    }

    void handle_o_command(bool below) {
        save_undo();
        if (below) {
            size_t line_start = get_pos_from_row(cursor_row);
            size_t next_nl = text.find('\n', line_start);
            if (next_nl == std::string::npos) {
                text += "\n";
                cursor_row++;
            } else {
                text.insert(next_nl, "\n");
                cursor_row++;
            }
        } else {
            size_t line_start = get_pos_from_row(cursor_row);
            text.insert(line_start, "\n");
        }
        cursor_col = 0;
        mode = "INSERT";
    }

    int get_line_length(int row) const {
        size_t line_start = get_pos_from_row(row);
        if (line_start >= text.length()) return 0;
        size_t next_nl = text.find('\n', line_start);
        if (next_nl == std::string::npos) return text.length() - line_start;
        return next_nl - line_start;
    }

    size_t get_line_count() const {
        if (text.empty()) return 1;
        size_t count = 1;
        size_t pos = 0;
        while ((pos = text.find('\n', pos)) != std::string::npos) {
            count++;
            pos++;
        }
        return count;
    }

    std::vector<std::string> get_lines() const {
        std::vector<std::string> lines;
        size_t start = 0;
        size_t end = text.find('\n');
        while (end != std::string::npos) {
            lines.push_back(text.substr(start, end - start));
            start = end + 1;
            end = text.find('\n', start);
        }
        lines.push_back(text.substr(start));
        return lines;
    }

    void update_cursor_bounds() {
        int count = (int)get_line_count();
        cursor_row = std::max(0, std::min(count - 1, cursor_row));
        int len = get_line_length(cursor_row);
        cursor_col = std::max(0, std::min(len, cursor_col));
    }

public:
    void replace_current_word(const std::string& new_word) {
        save_undo();
        size_t pos = get_cursor_pos();
        size_t start = pos;
        while (start > 0 && start <= text.length() && !isspace(text[start - 1])) start--;
        size_t end = pos;
        while (end < text.length() && !isspace(text[end])) end++;
        
        if (start <= text.length()) {
            text.replace(start, end - start, new_word);
            cursor_col = start - get_pos_from_row(cursor_row) + new_word.length();
        }
        update_cursor_bounds();
    }
};

PYBIND11_MODULE(zep_vim, m) {
    py::class_<ZepVim>(m, "ZepVim")
        .def(py::init<>())
        .def("handle_key", &ZepVim::handle_key)
        .def("get_text", &ZepVim::get_text)
        .def("set_text", &ZepVim::set_text)
        .def("get_mode", &ZepVim::get_mode)
        .def("get_cursor", &ZepVim::get_cursor)
        .def("get_anchor", &ZepVim::get_anchor)
        .def("replace_current_word", &ZepVim::replace_current_word);
}
