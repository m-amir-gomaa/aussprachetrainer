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
                if (cursor_col > 0) cursor_col--;
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
        } else if (key.length() == 1) {
            insert_at_cursor(key);
            cursor_col++;
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
        cursor_row = std::max(0, std::min((int)get_line_count() - 1, cursor_row + dr));
        cursor_col = std::max(0, std::min(get_line_length(cursor_row), cursor_col + dc));
    }

    void move_word(int dir) {
        size_t pos = get_cursor_pos();
        if (dir > 0) {
            bool found_space = false;
            while (pos < text.length()) {
                if (isspace(text[pos])) found_space = true;
                else if (found_space) break;
                pos++;
            }
        } else {
            if (pos > 0) pos--;
            while (pos > 0 && isspace(text[pos])) pos--;
            while (pos > 0 && !isspace(text[pos-1])) pos--;
        }
        set_cursor_from_pos(pos);
    }

    void move_word_end() {
        size_t pos = get_cursor_pos();
        if (pos < text.length()) pos++;
        while (pos < text.length() && isspace(text[pos])) pos++;
        while (pos < text.length()) {
            if (pos + 1 >= text.length() || isspace(text[pos + 1])) break;
            pos++;
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
            text.erase(pos - 1, 1);
            if (cursor_col > 0) cursor_col--;
            else if (cursor_row > 0) {
                cursor_row--;
                cursor_col = get_line_length(cursor_row);
            }
        } else if (!back && pos < text.length()) {
            text.erase(pos, 1);
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
