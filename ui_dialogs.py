import tkinter as tk
from tkinter import ttk, messagebox
import glob
import os

def ask_select_device(root, devices):
    """Dialog ให้เลือก ADB device เมื่อมีหลายเครื่อง"""
    d = tk.Toplevel(root)
    d.title("เลือกอุปกรณ์ที่จะเชื่อมต่อ")
    d.geometry("420x300")
    d.transient(root)
    d.grab_set()
    d.resizable(False, False)

    result = {}

    tk.Label(d, text="พบอุปกรณ์หลายเครื่อง — เลือกเครื่องที่ต้องการเชื่อมต่อ:",
             font=("Helvetica", 10, "bold")).pack(pady=(15, 5))

    frame_lb = tk.Frame(d, bd=1, relief=tk.SUNKEN)
    frame_lb.pack(fill="both", expand=True, padx=20, pady=5)
    scrollbar = tk.Scrollbar(frame_lb, orient="vertical")
    listbox = tk.Listbox(frame_lb, yscrollcommand=scrollbar.set,
                         font=("Consolas", 10), selectmode=tk.SINGLE, activestyle="dotbox")
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill="y")
    listbox.pack(side=tk.LEFT, fill="both", expand=True)

    for dev in devices:
        try:
            state = dev.get_state() if hasattr(dev, 'get_state') else "device"
        except Exception:
            state = "device"
        listbox.insert(tk.END, f"  {dev.serial}  [{state}]")
    listbox.selection_set(0)

    def on_ok():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("Error", "กรุณาเลือกอุปกรณ์ก่อน!", parent=d)
            return
        result['index'] = sel[0]
        d.destroy()

    def on_cancel():
        d.destroy()

    listbox.bind("<Double-Button-1>", lambda e: on_ok())

    btn_frame = tk.Frame(d)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="เชื่อมต่อ", command=on_ok,
              bg="#C8E6C9", width=14, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="ยกเลิก", command=on_cancel,
              bg="#FFCDD2", width=10).pack(side=tk.LEFT, padx=5)

    root.wait_window(d)
    if 'index' in result:
        return result['index']
    return None

def ask_spam_wait_details(root, available_templates):
    d = tk.Toplevel(root)
    d.title("ตั้งค่า Spam & Wait")
    d.geometry("340x480")
    d.transient(root)
    d.grab_set()
    
    result = {}
    
    tk.Label(d, text="1. เลือกรูปปุ่มที่จะสแปมกด:", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    templates = [f for f in available_templates if not f.startswith("-- ")]
    combo = ttk.Combobox(d, values=templates, state="readonly", width=25)
    combo.pack(pady=5)
    if templates:
        if "Jump.png" in templates:
            combo.current(templates.index("Jump.png"))
        else:
            combo.current(0)
    
    tk.Label(d, text="หรือ พิมพ์พิกัด X,Y เอง (เช่น 150,850):").pack(pady=(5,0))
    entry_xy = tk.Entry(d, width=15)
    entry_xy.pack(pady=5)
    
    tk.Label(d, text="2. ความถี่ในการกด (มิลลิวินาที):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    entry_ms = tk.Entry(d, width=15)
    entry_ms.insert(0, "550")
    entry_ms.pack(pady=5)
    
    tk.Label(d, text="3. สุ่มหน่วงเวลาเพิ่ม (มิลลิวินาที 0 - X):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    entry_random_ms = tk.Entry(d, width=15)
    entry_random_ms.insert(0, "50")
    entry_random_ms.pack(pady=5)
    
    tk.Label(d, text="4. เลือกภาพที่รอ (เลือกได้ 1-3 ภาพ):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
    tk.Label(d, text="(กด Ctrl+Click เพื่อเลือกหลายภาพ)", fg="gray").pack()
    
    frame_lb = tk.Frame(d)
    frame_lb.pack(pady=4, padx=20, fill="both")
    scrollbar_lb = tk.Scrollbar(frame_lb, orient="vertical")
    wait_listbox = tk.Listbox(frame_lb, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar_lb.set, height=5, exportselection=False)
    scrollbar_lb.config(command=wait_listbox.yview)
    scrollbar_lb.pack(side=tk.RIGHT, fill="y")
    wait_listbox.pack(side=tk.LEFT, fill="both", expand=True)
    for t in templates:
        wait_listbox.insert(tk.END, t)
    
    def on_ok():
        target = entry_xy.get().strip()
        if not target:
            target = combo.get()
        
        ms_val = entry_ms.get().strip()
        if not ms_val.isdigit():
            messagebox.showwarning("Error", "ความถี่ต้องเป็นตัวเลขเท่านั้น!", parent=d)
            return
            
        rand_val = entry_random_ms.get().strip()
        if not rand_val.isdigit():
            messagebox.showwarning("Error", "ค่าสุ่มหน่วงเวลาต้องเป็นตัวเลขเท่านั้น!", parent=d)
            return
        
        selected_indices = wait_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Error", "กรุณาเลือกภาพที่รออย่างน้อย 1 ภาพ!", parent=d)
            return
        if len(selected_indices) > 3:
            messagebox.showwarning("Error", "เลือกได้สูงสุด 3 ภาพเท่านั้น!", parent=d)
            return
        
        wait_targets = [wait_listbox.get(i) for i in selected_indices]
            
        result['target'] = target
        result['delay'] = int(ms_val)
        result['random_delay'] = int(rand_val)
        result['wait_targets'] = wait_targets
        d.destroy()
        
    tk.Button(d, text="ตกลง", command=on_ok, bg="#4CAF50", fg="white", width=15).pack(pady=12)
    
    root.wait_window(d)
    if 'target' in result:
        return result['target'], result['delay'], result['random_delay'], result['wait_targets']
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

def ask_type_text_details(root):
    """Dialog สำหรับตั้งค่าคำสั่ง พิมพ์ข้อความ (Type Text)"""
    d = tk.Toplevel(root)
    d.title("ตั้งค่าคำสั่ง พิมพ์ข้อความ (Type Text)")
    d.geometry("360x200")
    d.transient(root)
    d.grab_set()
    d.resizable(False, False)

    result = {}

    tk.Label(d, text="พิมพ์ข้อความที่ต้องการส่งไปยังเกม:", font=("Helvetica", 10, "bold")).pack(pady=(15, 0))
    tk.Label(d, text="(ใช้ adb shell input text — รองรับตัวอักษร/ตัวเลข)", fg="gray").pack()

    entry_text = tk.Entry(d, width=35, font=("Helvetica", 11))
    entry_text.pack(pady=10, padx=20)
    entry_text.focus_set()

    def on_ok():
        text_val = entry_text.get()
        if not text_val:
            messagebox.showwarning("Error", "กรุณาใส่ข้อความที่ต้องการพิมพ์!", parent=d)
            return
        result['text'] = text_val
        d.destroy()

    def on_cancel():
        d.destroy()

    entry_text.bind("<Return>", lambda e: on_ok())

    btn_frame = tk.Frame(d)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="ตกลง (OK)", command=on_ok, bg="#C8E6C9", width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="ยกเลิก", command=on_cancel, bg="#FFCDD2", width=12).pack(side=tk.LEFT, padx=5)

    root.wait_window(d)
    if 'text' in result:
        return result['text']
    return None


def ask_loop_control_details(root):
    d = tk.Toplevel(root)
    d.title("ตั้งค่าคำสั่ง วนลูป (Loop)")
    d.geometry("340x320")
    d.transient(root)
    d.grab_set()

    result = {}

    tk.Label(d, text="1. จำนวนสเต็ปที่จะย้อนกลับไปทำซ้ำ:", font=("Helvetica", 10, "bold")).pack(pady=(12, 0))
    tk.Label(d, text="(เช่น ใส่ 2 เพื่อย้อนกลับไปทำ 2 คำสั่งล่าสุดซ้ำ)", fg="gray").pack()
    entry_steps = tk.Entry(d, width=15)
    entry_steps.insert(0, "2")
    entry_steps.pack(pady=5)

    # --- โหมด ---
    tk.Label(d, text="2. เงื่อนไขการวนลูป:", font=("Helvetica", 10, "bold")).pack(pady=(8, 0))
    mode_var = tk.StringVar(value="duration")

    mode_frame = tk.Frame(d)
    mode_frame.pack()
    rb_dur = tk.Radiobutton(mode_frame, text="ตามเวลา (ms)", variable=mode_var, value="duration",
                            command=lambda: _on_mode_change())
    rb_dur.pack(side=tk.LEFT, padx=8)
    rb_cnt = tk.Radiobutton(mode_frame, text="ตามจำนวนรอบ", variable=mode_var, value="count",
                            command=lambda: _on_mode_change())
    rb_cnt.pack(side=tk.LEFT, padx=8)

    # ฟิลด์ Duration
    frame_dur = tk.Frame(d)
    frame_dur.pack(pady=4)
    tk.Label(frame_dur, text="ระยะเวลา (ms):").pack(side=tk.LEFT)
    entry_sec = tk.Entry(frame_dur, width=8)
    entry_sec.insert(0, "30000")
    entry_sec.pack(side=tk.LEFT, padx=5)

    # ฟิลด์ Count
    frame_cnt = tk.Frame(d)
    tk.Label(frame_cnt, text="จำนวนรอบ:").pack(side=tk.LEFT)
    entry_cnt = tk.Entry(frame_cnt, width=8)
    entry_cnt.insert(0, "5")
    entry_cnt.pack(side=tk.LEFT, padx=5)

    def _on_mode_change():
        if mode_var.get() == "duration":
            frame_cnt.pack_forget()
            frame_dur.pack(pady=4)
        else:
            frame_dur.pack_forget()
            frame_cnt.pack(pady=4)

    def on_ok():
        steps_val = entry_steps.get().strip()
        if not steps_val.isdigit() or int(steps_val) < 1:
            messagebox.showwarning("Error", "จำนวนสเต็ปต้องเป็นตัวเลขจำนวนเต็มตั้งแต่ 1 ขึ้นไป!", parent=d)
            return

        if mode_var.get() == "duration":
            sec_val = entry_sec.get().strip()
            if not sec_val.isdigit() or int(sec_val) < 1:
                messagebox.showwarning("Error", "ระยะเวลามิลลิวินาทีต้องเป็นตัวเลขจำนวนเต็มตั้งแต่ 1 ขึ้นไป!", parent=d)
                return
            result['steps'] = int(steps_val)
            result['mode'] = 'duration'
            result['value'] = int(sec_val)
        else:
            cnt_val = entry_cnt.get().strip()
            if not cnt_val.isdigit() or int(cnt_val) < 1:
                messagebox.showwarning("Error", "จำนวนรอบต้องเป็นตัวเลขจำนวนเต็มตั้งแต่ 1 ขึ้นไป!", parent=d)
                return
            result['steps'] = int(steps_val)
            result['mode'] = 'count'
            result['value'] = int(cnt_val)
        d.destroy()

    def on_cancel():
        d.destroy()

    btn_frame = tk.Frame(d)
    btn_frame.pack(pady=12)
    tk.Button(btn_frame, text="ตกลง (OK)", command=on_ok, bg="#C8E6C9", width=12).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="ยกเลิก", command=on_cancel, bg="#FFCDD2", width=12).pack(side=tk.LEFT, padx=5)

    root.wait_window(d)
    if 'steps' in result:
        return result['steps'], result['mode'], result['value']
    return None

def ask_multi_templates(root, available_templates, initial_template=None):
    d = tk.Toplevel(root)
    d.title("เลือกหลายภาพ (Multi-Select)")
    d.geometry("320x350")
    d.transient(root)
    d.grab_set()

    result = []

    tk.Label(d, text="เลือกภาพที่ต้องการรอ (เลือกได้มากกว่า 1 ภาพ):", font=("Helvetica", 10, "bold")).pack(pady=(12, 0))
    tk.Label(d, text="(กด Ctrl+Click เพื่อเลือกหลายภาพ)", fg="gray").pack()

    frame_lb = tk.Frame(d)
    frame_lb.pack(pady=5, padx=20, fill="both", expand=True)
    scrollbar_lb = tk.Scrollbar(frame_lb, orient="vertical")
    listbox = tk.Listbox(frame_lb, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar_lb.set, exportselection=False)
    scrollbar_lb.config(command=listbox.yview)
    scrollbar_lb.pack(side=tk.RIGHT, fill="y")
    listbox.pack(side=tk.LEFT, fill="both", expand=True)

    templates = [f for f in available_templates if not f.startswith("-- ")]
    for t in templates:
        listbox.insert(tk.END, t)

    # Pre-select initial_template
    if initial_template and initial_template in templates:
        idx = templates.index(initial_template)
        listbox.selection_set(idx)
        listbox.see(idx)

    def on_ok():
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Error", "กรุณาเลือกภาพอย่างน้อย 1 ภาพ!", parent=d)
            return
        result.extend([listbox.get(i) for i in selected_indices])
        d.destroy()

    tk.Button(d, text="ตกลง (OK)", command=on_ok, bg="#C8E6C9", width=15).pack(pady=10)
    root.wait_window(d)
    return result

def ask_swipe_details(root, available_templates):
    d = tk.Toplevel(root)
    d.title("ตั้งค่าการลากหน้าจอ (Swipe)")
    d.geometry("340x350")
    d.transient(root)
    d.grab_set()

    result = {}

    nb = ttk.Notebook(d)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # --- Tab 1: Coordinates ---
    f_coord = tk.Frame(nb)
    nb.add(f_coord, text="ระบุพิกัด X,Y")

    tk.Label(f_coord, text="จุดเริ่มต้น X,Y (เช่น 960,800):", font=("Helvetica", 9, "bold")).pack(pady=(10, 0))
    entry_start = tk.Entry(f_coord, width=20)
    entry_start.insert(0, "960,800")
    entry_start.pack(pady=5)

    tk.Label(f_coord, text="จุดสิ้นสุด X,Y (เช่น 960,300):", font=("Helvetica", 9, "bold")).pack(pady=(8, 0))
    entry_end = tk.Entry(f_coord, width=20)
    entry_end.insert(0, "960,300")
    entry_end.pack(pady=5)

    # --- Tab 2: Template ---
    f_temp = tk.Frame(nb)
    nb.add(f_temp, text="เลือกรูปภาพ")

    tk.Label(f_temp, text="เลือกรูปภาพขอบเขตลาก:", font=("Helvetica", 9, "bold")).pack(pady=(10, 0))
    templates = [f for f in available_templates if not f.startswith("-- ")]
    combo_img = ttk.Combobox(f_temp, values=templates, state="readonly", width=25)
    combo_img.pack(pady=5)
    if templates:
        combo_img.current(0)

    tk.Label(f_temp, text="ทิศทางการลาก:", font=("Helvetica", 9, "bold")).pack(pady=(8, 0))
    combo_dir = ttk.Combobox(f_temp, values=[
        "บนลงล่าง (Top-to-Bottom)",
        "ล่างขึ้นบน (Bottom-to-Top)",
        "ซ้ายไปขวา (Left-to-Right)",
        "ขวาไปซ้าย (Right-to-Left)"
    ], state="readonly", width=25)
    combo_dir.pack(pady=5)
    combo_dir.current(0)

    # --- Shared Duration ---
    f_bottom = tk.Frame(d)
    f_bottom.pack(fill="x", padx=15, pady=(0, 10))
    tk.Label(f_bottom, text="ระยะเวลาลาก (ms):", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
    entry_dur = tk.Entry(f_bottom, width=10)
    entry_dur.insert(0, "500")
    entry_dur.pack(side=tk.LEFT)

    def on_ok():
        mode = nb.index(nb.select()) # 0 = coord, 1 = temp
        dur_val = entry_dur.get().strip()
        if not dur_val.isdigit() or int(dur_val) < 50:
            messagebox.showwarning("Error", "ระยะเวลาลากต้องเป็นตัวเลข ms (อย่างน้อย 50ms)!", parent=d)
            return

        if mode == 0:
            start_val = entry_start.get().strip()
            end_val = entry_end.get().strip()
            if "," not in start_val or "," not in end_val:
                messagebox.showwarning("Error", "กรุณากรอกพิกัดในรูปแบบ X,Y เช่น 960,800!", parent=d)
                return
            result['type'] = 'coord'
            result['start'] = start_val
            result['end'] = end_val
            result['duration'] = int(dur_val)
        else:
            img_val = combo_img.get()
            if not img_val:
                messagebox.showwarning("Error", "กรุณาเลือกรูปภาพต้นแบบ!", parent=d)
                return
            dir_text = combo_dir.get()
            dir_key = "Top-to-Bottom"
            if "Bottom-to-Top" in dir_text:
                dir_key = "Bottom-to-Top"
            elif "Left-to-Right" in dir_text:
                dir_key = "Left-to-Right"
            elif "Right-to-Left" in dir_text:
                dir_key = "Right-to-Left"
                
            result['type'] = 'temp'
            result['img'] = img_val
            result['dir'] = dir_key
            result['duration'] = int(dur_val)
        d.destroy()

    tk.Button(d, text="ตกลง (OK)", command=on_ok, bg="#C8E6C9", width=15).pack(pady=(0, 10))
    root.wait_window(d)
    if 'type' in result:
        if result['type'] == 'coord':
            return 'coord', (result['start'], result['end'], result['duration'])
        else:
            return 'temp', (result['img'], result['dir'], result['duration'])
    return None
