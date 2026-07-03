import json
import os
from tkinter import filedialog, messagebox
import tkinter as tk

def save_macro(macro_listbox, recovery_listbox, timeout_var, package_var):
    steps = list(macro_listbox.get(0, tk.END))
    if not steps:
        messagebox.showwarning("Warning", "ไม่มีสเต็ปในคิวให้เซฟครับ")
        return
        
    os.makedirs("macros", exist_ok=True)
    filepath = filedialog.asksaveasfilename(
        initialdir=os.path.join(os.getcwd(), "macros"),
        title="Save Macro",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")]
    )
    if filepath:
        try:
            data = {
                "steps": steps,
                "recovery_steps": list(recovery_listbox.get(0, tk.END)),
                "timeout_mins": int(timeout_var.get()),
                "package_name": package_var.get().strip()
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Success", "บันทึกคิวมาโครสำเร็จ!")
        except Exception as e:
            messagebox.showerror("Error", f"บันทึกไม่สำเร็จ: {e}")

def load_macro(macro_listbox, recovery_listbox, timeout_var, package_var):
    os.makedirs("macros", exist_ok=True)
    filepath = filedialog.askopenfilename(
        initialdir=os.path.join(os.getcwd(), "macros"),
        title="Load Macro",
        filetypes=[("JSON files", "*.json")]
    )
    if filepath:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            macro_listbox.delete(0, tk.END)
            if isinstance(data, list):
                for step in data:
                    macro_listbox.insert(tk.END, step)
            elif isinstance(data, dict):
                steps = data.get("steps", [])
                for step in steps:
                    macro_listbox.insert(tk.END, step)
                
                timeout_var.set(str(data.get("timeout_mins", 5)))
                package_var.set(data.get("package_name", "com.devsisters.crg"))
                
                recovery_listbox.delete(0, tk.END)
                recovery_steps = data.get("recovery_steps", [])
                if recovery_steps:
                    for step in recovery_steps:
                        recovery_listbox.insert(tk.END, step)
                
            messagebox.showinfo("Success", "โหลดคิวมาโครสำเร็จ!")
        except Exception as e:
            messagebox.showerror("Error", f"โหลดไม่สำเร็จ: {e}")
