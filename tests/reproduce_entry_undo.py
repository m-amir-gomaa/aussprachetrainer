
import tkinter as tk
import customtkinter as ctk

def test_undo():
    root = ctk.CTk()
    entry = ctk.CTkEntry(root)
    entry.pack()
    entry.insert(0, "first")
    root.update()
    entry.insert("end", " second")
    root.update()
    
    print(f"Before undo: '{entry.get()}'")
    entry.event_generate("<<Undo>>")
    root.update()
    print(f"After undo: '{entry.get()}'")
    
    if entry.get() == "first":
        print("Undo WORKED")
    else:
        print("Undo FAILED (as expected for tk.Entry)")
        
    root.after(100, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    test_undo()
