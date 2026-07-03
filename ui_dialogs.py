import tkinter as tk
from tkinter import ttk, messagebox
import glob
import os

def ask_spam_wait_details(root, available_templates):
    d = tk.Toplevel(root)
    d.title("ตั้งค่า Spam & Wait")
    d.geometry("320x280")
    d.transient(root)
    d.grab_set()
    
    result = {}
    
    tk.Label(d, text="1. เลือกรูปปุ่มที่จะสแปมกด:", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    templates = [f for f in available_templates if not f.startswith("-- ")]
    combo = ttk.Combobox(d, values=templates, state="readonly", width=25)
    combo.pack(pady=5)
    if templates: combo.current(0)
    
    tk.Label(d, text="หรือ พิมพ์พิกัด X,Y เอง (เช่น 150,850):").pack(pady=(5,0))
    entry_xy = tk.Entry(d, width=15)
    entry_xy.pack(pady=5)
    
    tk.Label(d, text="2. ความถี่ในการกด (มิลลิวินาที):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    entry_ms = tk.Entry(d, width=15)
    entry_ms.insert(0, "600")
    entry_ms.pack(pady=5)
    
    def on_ok():
        target = entry_xy.get().strip()
        if not target:
            target = combo.get()
        
        ms_val = entry_ms.get().strip()
        if not ms_val.isdigit():
            messagebox.showwarning("Error", "ความถี่ต้องเป็นตัวเลขเท่านั้น!", parent=d)
            return
            
        result['target'] = target
        result['delay'] = int(ms_val)
        d.destroy()
        
    tk.Button(d, text="ตกลง", command=on_ok, bg="#4CAF50", fg="white", width=15).pack(pady=15)
    
    root.wait_window(d)
    if 'target' in result:
        return result['target'], result['delay']
    return None

def ask_multi_loop_details(root):
    d = tk.Toplevel(root)
    d.title("ตั้งค่า Loop หลายปุ่ม (Loop Multi-Buttons)")
    d.geometry("350x400")
    d.transient(root)
    d.grab_set()
    
    result = {}
    
    tk.Label(d, text="1. เลือกปุ่มทั้งหมดที่จะคลิกวนลูป (เลือกได้มากกว่า 1 ปุ่ม):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    
    frame = tk.Frame(d)
    frame.pack(pady=5, fill="both", expand=True, padx=20)
    
    scrollbar = tk.Scrollbar(frame, orient="vertical")
    listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set, height=8)
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill="y")
    listbox.pack(side=tk.LEFT, fill="both", expand=True)
    
    files = glob.glob("templates/*.png")
    names = [os.path.basename(f) for f in files]
    for name in names:
        listbox.insert(tk.END, name)
        
    tk.Label(d, text="2. หน่วงเวลาระหว่างคลิก (มิลลิวินาที ms):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    entry_ms = tk.Entry(d, width=15)
    entry_ms.insert(0, "500")
    entry_ms.pack(pady=5)
    
    def on_ok():
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Error", "กรุณาเลือกอย่างน้อย 1 ปุ่ม!", parent=d)
            return
            
        selected_templates = [listbox.get(i) for i in selected_indices]
        
        ms_val = entry_ms.get().strip()
        if not ms_val.isdigit():
            messagebox.showwarning("Error", "ความถี่หน่วงเวลาต้องเป็นตัวเลขเท่านั้น!", parent=d)
            return
            
        result['templates'] = selected_templates
        result['delay'] = int(ms_val)
        d.destroy()
        
    def on_cancel():
        d.destroy()
        
    btn_frame = tk.Frame(d)
    btn_frame.pack(pady=15)
    tk.Button(btn_frame, text="ตกลง (OK)", command=on_ok, bg="#C8E6C9", width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="ยกเลิก", command=on_cancel, bg="#FFCDD2", width=12).pack(side=tk.LEFT, padx=5)
    
    root.wait_window(d)
    if 'templates' in result:
        return result['templates'], result['delay']
    return None

def ask_loop_control_details(root):
    d = tk.Toplevel(root)
    d.title("ตั้งค่าคำสั่ง วนลูป (Loop)")
    d.geometry("320x240")
    d.transient(root)
    d.grab_set()
    
    result = {}
    
    tk.Label(d, text="1. จำนวนสเต็ปที่จะย้อนกลับไปทำซ้ำ:", font=("Helvetica", 10, "bold")).pack(pady=(15,0))
    tk.Label(d, text="(เช่น ใส่ 2 เพื่อย้อนกลับไปทำ 2 คำสั่งล่าสุดซ้ำ)", fg="gray").pack()
    entry_steps = tk.Entry(d, width=15)
    entry_steps.insert(0, "2")
    entry_steps.pack(pady=5)
    
    tk.Label(d, text="2. ระยะเวลาที่จะให้วนลูปทำงาน (วินาที):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    entry_sec = tk.Entry(d, width=15)
    entry_sec.insert(0, "30")
    entry_sec.pack(pady=5)
    
    def on_ok():
        steps_val = entry_steps.get().strip()
        sec_val = entry_sec.get().strip()
        
        if not steps_val.isdigit() or int(steps_val) < 1:
            messagebox.showwarning("Error", "จำนวนสเต็ปต้องเป็นตัวเลขจำนวนเต็มตั้งแต่ 1 ขึ้นไป!", parent=d)
            return
            
        if not sec_val.isdigit() or int(sec_val) < 1:
            messagebox.showwarning("Error", "ระยะเวลาวินาทีต้องเป็นตัวเลขจำนวนเต็มตั้งแต่ 1 ขึ้นไป!", parent=d)
            return
            
        result['steps'] = int(steps_val)
        result['duration'] = int(sec_val)
        d.destroy()
        
    def on_cancel():
        d.destroy()
        
    btn_frame = tk.Frame(d)
    btn_frame.pack(pady=15)
    tk.Button(btn_frame, text="ตกลง (OK)", command=on_ok, bg="#C8E6C9", width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="ยกเลิก", command=on_cancel, bg="#FFCDD2", width=12).pack(side=tk.LEFT, padx=5)
    
    root.wait_window(d)
    if 'steps' in result:
        return result['steps'], result['duration']
    return None
