import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from tkinter import ttk
from ppadb.client import Client as AdbClient
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
import sys
import traceback
import logging
import urllib.request
import zipfile
import subprocess
import glob
import json
import threading
import time

# Setup global logging
logging.basicConfig(filename='bot_error.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def global_exception_handler(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error("Unhandled exception: \n" + error_msg)
    try:
        messagebox.showerror("Critical Error", f"เกิดข้อผิดพลาดที่ไม่ได้คาดคิด (Crash)\n\nระบบได้บันทึกข้อผิดพลาดไว้ในไฟล์ bot_error.log แล้ว\n\nสาเหตุเบื้องต้น:\n{exc_value}")
    except:
        pass
    sys.exit(1)

sys.excepthook = global_exception_handler

def ensure_adb_server():
    try:
        subprocess.run(["adb", "start-server"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except FileNotFoundError:
        pass
    if not os.path.exists("platform-tools/adb.exe"):
        try:
            url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
            urllib.request.urlretrieve(url, "platform-tools.zip")
            with zipfile.ZipFile("platform-tools.zip", 'r') as zip_ref:
                zip_ref.extractall(".")
            os.remove("platform-tools.zip")
        except Exception as e:
            logging.error(f"Failed to download ADB: {e}")
            raise Exception(f"ไม่สามารถดาวน์โหลด ADB อัตโนมัติได้ กรุณาต่อเน็ต: {e}")
            
    try:
        subprocess.run(["platform-tools\\adb.exe", "start-server"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logging.error(f"Failed to start local ADB: {e}")
        raise Exception(f"ไม่สามารถเปิดการทำงานของ ADB ได้: {e}")

class CropWindow(tk.Toplevel):
    def __init__(self, master, image_array, callback):
        super().__init__(master)
        self.title("Crop Template (ลากเมาส์เพื่อครอบภาพ)")
        self.callback = callback
        
        self.original_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        self.rgb_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2RGB)
        
        self.h, self.w = self.rgb_img.shape[:2]
        self.display_w = min(1000, self.w)
        self.scale = self.display_w / self.w
        self.display_h = int(self.h * self.scale)
        
        resized = cv2.resize(self.rgb_img, (self.display_w, self.display_h))
        self.pil_img = Image.fromarray(resized)
        self.tk_img = ImageTk.PhotoImage(self.pil_img)
        
        self.canvas = tk.Canvas(self, width=self.display_w, height=self.display_h, cursor="cross")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.rect = None
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
        tk.Label(self, text=" ลากเมาส์คลุมบริเวณที่ต้องการทำเป็น Template (ปล่อยเมาส์เพื่อยืนยัน) ", bg="yellow", fg="black", font=("Helvetica", 12)).place(x=10, y=10)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=3)

    def on_move_press(self, event):
        cur_x, cur_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = (event.x, event.y)
        x1 = int(min(self.start_x, end_x) / self.scale)
        x2 = int(max(self.start_x, end_x) / self.scale)
        y1 = int(min(self.start_y, end_y) / self.scale)
        y2 = int(max(self.start_y, end_y) / self.scale)
        
        if x2 - x1 > 5 and y2 - y1 > 5:
            cropped_bgr = self.original_img[y1:y2, x1:x2]
            name = simpledialog.askstring("Save Template", "ตั้งชื่อไฟล์ภาพ (ภาษาไทยได้):", parent=self)
            if name:
                if not name.endswith('.png'):
                    name += '.png'
                self.callback(name, cropped_bgr, x1, y1, x2, y2)
        
        self.destroy()

class CookieRunBotUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CookieRun Bot - Macro Builder")
        self.root.geometry("500x650")
        
        self.device = None
        self.macro_running = False
        self.test_restart_running = False
        os.makedirs("templates", exist_ok=True)
        
        # --- Top Info ---
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(top_frame, text="CookieRun ADB Bot & Macro", font=("Helvetica", 14, "bold")).pack(pady=5)
        
        self.status_label = tk.Label(top_frame, text="Status: Disconnected", fg="red", font=("Helvetica", 10, "bold"))
        self.status_label.pack()
        
        self.connect_btn = tk.Button(top_frame, text="1. Connect to MuMu Player", command=self.connect_adb, bg="#FFC107", font=("Helvetica", 10, "bold"))
        self.connect_btn.pack(fill="x", pady=5)
        
        self.restart_btn = tk.Button(top_frame, text="🔄 Restart App (รีสตาร์ทโปรแกรม)", command=self.restart_app, bg="#E0E0E0")
        self.restart_btn.pack(fill="x", pady=(0, 5))
        
        # --- Notebook Tabs ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)
        
        self.tab_templates = tk.Frame(self.notebook)
        self.notebook.add(self.tab_templates, text="🛠️ จัดการภาพต้นแบบ (Templates)")
        
        self.tab_macro = tk.Frame(self.notebook)
        self.notebook.add(self.tab_macro, text="🚀 สร้างบอทมารโคร (Macro)")
        
        self.tab_recovery = tk.Frame(self.notebook)
        self.notebook.add(self.tab_recovery, text="🔄 กู้คืนเกม (Recovery)")
        
        self.setup_template_tab()
        self.setup_macro_tab()
        self.setup_recovery_tab()

    def setup_template_tab(self):
        # Create Template
        f_create = tk.LabelFrame(self.tab_templates, text="2. สร้างภาพปุ่มใหม่ (ลากครอบเอง)")
        f_create.pack(fill="x", padx=10, pady=10)
        self.create_template_btn = tk.Button(f_create, text="Capture & Crop New Template...", command=self.create_template, state=tk.DISABLED)
        self.create_template_btn.pack(fill="x", padx=10, pady=10)
        
        # Test Template
        f_test = tk.LabelFrame(self.tab_templates, text="3. จัดการภาพที่เซฟไว้")
        f_test.pack(fill="x", padx=10, pady=10)
        
        top_test = tk.Frame(f_test)
        top_test.pack(fill="x", padx=10, pady=5)
        
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(top_test, textvariable=self.template_var, state="readonly")
        self.template_combo.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        
        self.rename_btn = tk.Button(top_test, text="✏️ เปลี่ยนชื่อ", command=self.rename_template, state=tk.DISABLED)
        self.rename_btn.pack(side=tk.LEFT)
        
        self.delete_btn = tk.Button(top_test, text="🗑️ ลบภาพ", command=self.delete_template, state=tk.DISABLED, bg="#FFCDD2", fg="#C62828")
        self.delete_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        b_frame = tk.Frame(f_test)
        b_frame.pack(pady=5)
        self.test_find_btn = tk.Button(b_frame, text="Test Find (แค่หาเฉยๆ)", command=self.test_find, width=20, state=tk.DISABLED, bg="#2196F3", fg="white")
        self.test_find_btn.pack(side=tk.LEFT, padx=5)
        self.play_btn = tk.Button(b_frame, text="Find & Click (กดจริง)", command=self.find_and_click, width=20, state=tk.DISABLED, bg="#4CAF50", fg="white")
        self.play_btn.pack(side=tk.LEFT, padx=5)

    def setup_macro_tab(self):
        # Macro Builder
        f_add = tk.Frame(self.tab_macro)
        f_add.pack(fill="x", padx=10, pady=10)
        tk.Label(f_add, text="เลือกปุ่มที่เซฟไว้:").pack(side=tk.LEFT)
        
        self.macro_template_var = tk.StringVar()
        self.macro_combo = ttk.Combobox(f_add, textvariable=self.macro_template_var, state="readonly", width=20)
        self.macro_combo.pack(side=tk.LEFT, padx=5)
        self.macro_combo.bind("<<ComboboxSelected>>", self.on_macro_combo_selected)
        
        # Sub-frame container for Action label and combobox so they can be hidden/shown together
        self.action_frame = tk.Frame(f_add)
        self.action_frame.pack(side=tk.LEFT)
        
        tk.Label(self.action_frame, text="Action:").pack(side=tk.LEFT, padx=(5, 0))
        self.macro_action_var = tk.StringVar(value="[Click]")
        self.macro_action_combo = ttk.Combobox(self.action_frame, textvariable=self.macro_action_var, state="readonly", width=12)
        self.macro_action_combo['values'] = ["[Click]", "[Wait]", "[Spam-Wait]", "[Spam-Click]", "[Skip-If]", "[Skip-IfNot]", "[Break]"]
        self.macro_action_combo.pack(side=tk.LEFT, padx=5)
        
        self.add_step_btn = tk.Button(f_add, text="เพิ่มสเต็ป", command=self.add_macro_step, bg="#E0E0E0")
        self.add_step_btn.pack(side=tk.LEFT, padx=5)
        
        # Listbox
        tk.Label(self.tab_macro, text="ลำดับการกดของบอท (จะรอจนกว่าจะเจอภาพ ถึงจะกด):").pack(anchor=tk.W, padx=10)
        self.macro_listbox = tk.Listbox(self.tab_macro, height=8, font=("Helvetica", 10))
        self.macro_listbox.pack(fill="both", expand=True, padx=10, pady=2)
        
        # ผูก Event สำหรับลาก Listbox (Drag & Drop)
        self.macro_listbox.bind('<Button-1>', self.on_drag_start)
        self.macro_listbox.bind('<B1-Motion>', self.on_drag_motion)
        
        # Listbox Controls
        f_ctrl = tk.Frame(self.tab_macro)
        f_ctrl.pack(fill="x", padx=10, pady=2)
        tk.Button(f_ctrl, text="⬆️", command=self.move_step_up).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="⬇️", command=self.move_step_down).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="✏️ แก้ไข", command=self.edit_macro_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="🗑️ ลบ", command=self.remove_macro_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="ล้างทั้งหมด", command=lambda: self.macro_listbox.delete(0, tk.END)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(f_ctrl, text="💾 Save", command=self.save_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)
        tk.Button(f_ctrl, text="📂 Load", command=self.load_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)
        

        
        # Start/Stop
        f_run = tk.Frame(self.tab_macro)
        f_run.pack(pady=10)
        self.start_macro_btn = tk.Button(f_run, text="▶ START MACRO", command=self.start_macro, bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"), width=15, state=tk.DISABLED)
        self.start_macro_btn.grid(row=0, column=0, padx=5)
        self.stop_macro_btn = tk.Button(f_run, text="⏹ STOP MACRO", command=self.stop_macro, bg="#F44336", fg="white", font=("Helvetica", 12, "bold"), width=15, state=tk.DISABLED)
        self.stop_macro_btn.grid(row=0, column=1, padx=5)

    def setup_recovery_tab(self):
        # Anti-Stuck Settings
        f_stuck = tk.LabelFrame(self.tab_recovery, text="🛡️ ระบบกันค้าง (Anti-Stuck Settings)")
        f_stuck.pack(fill="x", padx=10, pady=5)
        
        # Row 1: Timeout and package name
        r1 = tk.Frame(f_stuck)
        r1.pack(fill="x", padx=5, pady=2)
        tk.Label(r1, text="เวลารอสูงสุด:").pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value="5")
        self.timeout_spin = tk.Spinbox(r1, from_=1, to=120, textvariable=self.timeout_var, width=5)
        self.timeout_spin.pack(side=tk.LEFT, padx=2)
        tk.Label(r1, text="นาที").pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(r1, text="ชื่อแพ็กเกจเกม:").pack(side=tk.LEFT)
        self.package_var = tk.StringVar(value="com.devsisters.crg")
        self.package_entry = tk.Entry(r1, textvariable=self.package_var, width=18)
        self.package_entry.pack(side=tk.LEFT, padx=2)
        
        self.detect_pkg_btn = tk.Button(r1, text="🔍 ดึงจากจอ", command=self.detect_current_package, bg="#E3F2FD", state=tk.DISABLED)
        self.detect_pkg_btn.pack(side=tk.LEFT, padx=5)

        # Row 3: Test actions
        r3 = tk.Frame(f_stuck)
        r3.pack(fill="x", padx=5, pady=2)
        
        self.restart_test_btn = tk.Button(r3, text="🔄 ทดสอบรีสตาร์ทเกม & เริ่มใหม่", command=self.test_restart_game, bg="#EFEBE9", fg="#4E342E", state=tk.DISABLED)
        self.restart_test_btn.pack(side=tk.LEFT, padx=5)

        # Recovery Macro Builder
        f_add = tk.Frame(self.tab_recovery)
        f_add.pack(fill="x", padx=10, pady=10)
        tk.Label(f_add, text="เลือกปุ่มที่เซฟไว้:").pack(side=tk.LEFT)
        
        self.recovery_template_var = tk.StringVar()
        self.recovery_combo = ttk.Combobox(f_add, textvariable=self.recovery_template_var, state="readonly", width=20)
        self.recovery_combo.pack(side=tk.LEFT, padx=5)
        self.recovery_combo.bind("<<ComboboxSelected>>", self.on_recovery_combo_selected)
        
        # Sub-frame container for Action label and combobox so they can be hidden/shown together
        self.rec_action_frame = tk.Frame(f_add)
        self.rec_action_frame.pack(side=tk.LEFT)
        
        tk.Label(self.rec_action_frame, text="Action:").pack(side=tk.LEFT, padx=(5, 0))
        self.recovery_action_var = tk.StringVar(value="[Click]")
        self.recovery_action_combo = ttk.Combobox(self.rec_action_frame, textvariable=self.recovery_action_var, state="readonly", width=12)
        self.recovery_action_combo['values'] = ["[Click]", "[Wait]", "[Spam-Wait]", "[Spam-Click]", "[Skip-If]", "[Skip-IfNot]", "[Break]"]
        self.recovery_action_combo.pack(side=tk.LEFT, padx=5)
        
        self.rec_add_step_btn = tk.Button(f_add, text="เพิ่มสเต็ป", command=self.add_recovery_step, bg="#E0E0E0")
        self.rec_add_step_btn.pack(side=tk.LEFT, padx=5)
        
        # Listbox
        tk.Label(self.tab_recovery, text="ลำดับคำสั่งที่จะทำเมื่อระบบค้าง/กู้คืนเกม (Restart Macro):").pack(anchor=tk.W, padx=10)
        self.recovery_listbox = tk.Listbox(self.tab_recovery, height=8, font=("Helvetica", 10))
        self.recovery_listbox.pack(fill="both", expand=True, padx=10, pady=2)
        
        # ผูก Event สำหรับลาก Listbox (Drag & Drop)
        self.recovery_listbox.bind('<Button-1>', self.on_drag_start_recovery)
        self.recovery_listbox.bind('<B1-Motion>', self.on_drag_motion_recovery)
        
        # Listbox Controls
        f_ctrl = tk.Frame(self.tab_recovery)
        f_ctrl.pack(fill="x", padx=10, pady=2)
        tk.Button(f_ctrl, text="⬆️", command=self.move_recovery_step_up).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="⬇️", command=self.move_recovery_step_down).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="✏️ แก้ไข", command=self.edit_recovery_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="🗑️ ลบ", command=self.remove_recovery_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="ล้างทั้งหมด", command=lambda: self.recovery_listbox.delete(0, tk.END)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(f_ctrl, text="💾 Save", command=self.save_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)
        tk.Button(f_ctrl, text="📂 Load", command=self.load_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)


    def on_recovery_combo_selected(self, event=None):
        val = self.recovery_template_var.get()
        if val in ["-- เพิ่มเวลาหน่วง (Delay) --", "-- แก้ไขมินิเกม (Solve Minigame) --", "-- วนลูป (Loop) --", "-- ปิดแอปเกม (Force Stop) --", "-- เปิดแอปเกม (Launch Game) --", "-- ตรวจสอบหน้าล็อบบี้ (Check Lobby) --"]:
            self.rec_action_frame.pack_forget()
        else:
            self.rec_action_frame.pack(side=tk.LEFT)
            self.rec_add_step_btn.pack_forget()
            self.rec_add_step_btn.pack(side=tk.LEFT, padx=5)

    def add_recovery_step(self):
        val = self.recovery_template_var.get()
        act = self.recovery_action_var.get()
        
        if act == "[Loop-Multi]":
            multi_info = self.ask_multi_loop_details()
            if not multi_info: return
            templates, delay_ms = multi_info
            templates_str = ",".join(templates)
            self.recovery_listbox.insert(tk.END, f"[Loop-Multi:{delay_ms}] {templates_str}")
            return
            
        if val == "-- เพิ่มเวลาหน่วง (Delay) --":
            delay_ms = simpledialog.askinteger("Delay Time", "ใส่เวลาที่ต้องการหน่วง\n(หน่วยเป็นมิลลิวินาที เช่น 1000 = 1 วินาที):", parent=self.root, minvalue=1, maxvalue=600000)
            if delay_ms:
                self.recovery_listbox.insert(tk.END, f"[Delay-Only] {delay_ms}ms")
            return
            
        if val == "-- แก้ไขมินิเกม (Solve Minigame) --":
            detect_img = simpledialog.askstring("Detect Template", "ใส่ชื่อรูปภาพที่ใช้ตรวจจับมินิเกม (เช่น Bot check.png):", initialvalue="Bot check.png", parent=self.root)
            if detect_img:
                if not detect_img.endswith(".png"):
                    detect_img += ".png"
                self.recovery_listbox.insert(tk.END, f"[Solve-Minigame] {detect_img}")
            return
            
        if val == "-- วนลูป (Loop) --":
            loop_info = self.ask_loop_control_details()
            if loop_info:
                steps_count, loop_sec = loop_info
                self.recovery_listbox.insert(tk.END, f"[Loop-Control:{steps_count}] Duration:{loop_sec}s")
            return
            
        if val == "-- ปิดแอปเกม (Force Stop) --":
            self.recovery_listbox.insert(tk.END, "[Force-Stop-Game]")
            return
            
        if val == "-- เปิดแอปเกม (Launch Game) --":
            self.recovery_listbox.insert(tk.END, "[Launch-Game]")
            return
            
        if val == "-- ตรวจสอบหน้าล็อบบี้ (Check Lobby) --":
            self.recovery_listbox.insert(tk.END, "[Check-Lobby]")
            return
            
        if val:
            if act in ["[Spam-Wait]", "[Spam-Click]"]:
                spam_info = self.ask_spam_wait_details()
                if not spam_info or not spam_info[0]: return
                spam_img, spam_delay = spam_info
                if not spam_img.endswith(".png") and "," not in spam_img: 
                    spam_img += ".png"
                self.recovery_listbox.insert(tk.END, f"{act} [{spam_img}] [S:{spam_delay}] {val}")
            elif act == "[Skip-If]":
                skip_count = simpledialog.askinteger("Skip Count", "ถ้าเจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)", parent=self.root, minvalue=1, maxvalue=50)
                if skip_count:
                    self.recovery_listbox.insert(tk.END, f"[Skip:{skip_count}] {val}")
            elif act == "[Skip-IfNot]":
                skip_count = simpledialog.askinteger("Skip Count", "ถ้าไม่เจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)", parent=self.root, minvalue=1, maxvalue=50)
                if skip_count:
                    self.recovery_listbox.insert(tk.END, f"[SkipNot:{skip_count}] {val}")
            else:
                self.recovery_listbox.insert(tk.END, f"{act} {val}")

    def remove_recovery_step(self):
        sel = self.recovery_listbox.curselection()
        if sel:
            self.recovery_listbox.delete(sel[0])

    def move_recovery_step_up(self):
        sel = self.recovery_listbox.curselection()
        if not sel: return
        i = sel[0]
        if i == 0: return
        val = self.recovery_listbox.get(i)
        self.recovery_listbox.delete(i)
        self.recovery_listbox.insert(i-1, val)
        self.recovery_listbox.selection_set(i-1)

    def move_recovery_step_down(self):
        sel = self.recovery_listbox.curselection()
        if not sel: return
        i = sel[0]
        if i == self.recovery_listbox.size() - 1: return
        val = self.recovery_listbox.get(i)
        self.recovery_listbox.delete(i)
        self.recovery_listbox.insert(i+1, val)
        self.recovery_listbox.selection_set(i+1)

    def edit_recovery_step(self):
        sel = self.recovery_listbox.curselection()
        if not sel: return
        i = sel[0]
        old_val = self.recovery_listbox.get(i)
        new_val = simpledialog.askstring("Edit Step", "แก้ไขคำสั่ง (กู้คืน):", initialvalue=old_val, parent=self.root)
        if new_val and new_val != old_val:
            self.recovery_listbox.delete(i)
            self.recovery_listbox.insert(i, new_val)
            self.recovery_listbox.selection_set(i)

    def on_drag_start_recovery(self, event):
        self._drag_start_index_rec = self.recovery_listbox.nearest(event.y)

    def on_drag_motion_recovery(self, event):
        i = self.recovery_listbox.nearest(event.y)
        if i < 0 or i >= self.recovery_listbox.size():
            return
        if i != self._drag_start_index_rec:
            val = self.recovery_listbox.get(self._drag_start_index_rec)
            self.recovery_listbox.delete(self._drag_start_index_rec)
            self.recovery_listbox.insert(i, val)
            self._drag_start_index_rec = i



    def refresh_templates(self):
        files = glob.glob("templates/*.png")
        names = [os.path.basename(f) for f in files]
        self.template_combo['values'] = names
        # เพิ่มเมนูพิเศษสำหรับ Macro
        macro_opts = [
            "-- เพิ่มเวลาหน่วง (Delay) --", 
            "-- แก้ไขมินิเกม (Solve Minigame) --", 
            "-- วนลูป (Loop) --",
            "-- ปิดแอปเกม (Force Stop) --",
            "-- เปิดแอปเกม (Launch Game) --",
            "-- ตรวจสอบหน้าล็อบบี้ (Check Lobby) --"
        ] + names
        self.macro_combo['values'] = macro_opts
        if hasattr(self, 'recovery_combo'):
            self.recovery_combo['values'] = macro_opts
        
        if names:
            self.template_combo.current(0)
            if hasattr(self, 'rename_btn'): self.rename_btn.config(state=tk.NORMAL)
            if hasattr(self, 'delete_btn'): self.delete_btn.config(state=tk.NORMAL)
        else:
            if hasattr(self, 'rename_btn'): self.rename_btn.config(state=tk.DISABLED)
            if hasattr(self, 'delete_btn'): self.delete_btn.config(state=tk.DISABLED)
            
        if macro_opts:
            self.macro_combo.current(0)
            self.on_macro_combo_selected()
            if hasattr(self, 'recovery_combo'):
                self.recovery_combo.current(0)
                self.on_recovery_combo_selected()

    def on_macro_combo_selected(self, event=None):
        val = self.macro_template_var.get()
        if val in ["-- เพิ่มเวลาหน่วง (Delay) --", "-- แก้ไขมินิเกม (Solve Minigame) --", "-- วนลูป (Loop) --", "-- ปิดแอปเกม (Force Stop) --", "-- เปิดแอปเกม (Launch Game) --", "-- ตรวจสอบหน้าล็อบบี้ (Check Lobby) --"]:
            self.action_frame.pack_forget()
        else:
            self.action_frame.pack(side=tk.LEFT)
            self.add_step_btn.pack_forget()
            self.add_step_btn.pack(side=tk.LEFT, padx=5)

    def restart_app(self):
        self.macro_running = False
        self.root.destroy()
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)

    def add_macro_step(self):
        val = self.macro_template_var.get()
        act = self.macro_action_var.get()
        
        if act == "[Loop-Multi]":
            multi_info = self.ask_multi_loop_details()
            if not multi_info: return
            templates, delay_ms = multi_info
            templates_str = ",".join(templates)
            self.macro_listbox.insert(tk.END, f"[Loop-Multi:{delay_ms}] {templates_str}")
            return
            
        if val == "-- เพิ่มเวลาหน่วง (Delay) --":
            delay_ms = simpledialog.askinteger("Delay Time", "ใส่เวลาที่ต้องการหน่วง\n(หน่วยเป็นมิลลิวินาที เช่น 1000 = 1 วินาที):", parent=self.root, minvalue=1, maxvalue=600000)
            if delay_ms:
                self.macro_listbox.insert(tk.END, f"[Delay-Only] {delay_ms}ms")
            return
            
        if val == "-- แก้ไขมินิเกม (Solve Minigame) --":
            detect_img = simpledialog.askstring("Detect Template", "ใส่ชื่อรูปภาพที่ใช้ตรวจจับมินิเกม (เช่น Bot check.png):", initialvalue="Bot check.png", parent=self.root)
            if detect_img:
                if not detect_img.endswith(".png"):
                    detect_img += ".png"
                self.macro_listbox.insert(tk.END, f"[Solve-Minigame] {detect_img}")
            return
            
        if val == "-- วนลูป (Loop) --":
            loop_info = self.ask_loop_control_details()
            if loop_info:
                steps_count, loop_sec = loop_info
                self.macro_listbox.insert(tk.END, f"[Loop-Control:{steps_count}] Duration:{loop_sec}s")
            return
            
        if val == "-- ปิดแอปเกม (Force Stop) --":
            self.macro_listbox.insert(tk.END, "[Force-Stop-Game]")
            return
            
        if val == "-- เปิดแอปเกม (Launch Game) --":
            self.macro_listbox.insert(tk.END, "[Launch-Game]")
            return
            
        if val == "-- ตรวจสอบหน้าล็อบบี้ (Check Lobby) --":
            self.macro_listbox.insert(tk.END, "[Check-Lobby]")
            return
            
        if val:
            if act in ["[Spam-Wait]", "[Spam-Click]"]:
                spam_info = self.ask_spam_wait_details()
                if not spam_info or not spam_info[0]: return
                spam_img, spam_delay = spam_info
                if not spam_img.endswith(".png") and "," not in spam_img: 
                    spam_img += ".png"
                self.macro_listbox.insert(tk.END, f"{act} [{spam_img}] [S:{spam_delay}] {val}")
            elif act == "[Skip-If]":
                skip_count = simpledialog.askinteger("Skip Count", "ถ้าเจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)", parent=self.root, minvalue=1, maxvalue=50)
                if skip_count:
                    self.macro_listbox.insert(tk.END, f"[Skip:{skip_count}] {val}")
            elif act == "[Skip-IfNot]":
                skip_count = simpledialog.askinteger("Skip Count", "ถ้าไม่เจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)", parent=self.root, minvalue=1, maxvalue=50)
                if skip_count:
                    self.macro_listbox.insert(tk.END, f"[SkipNot:{skip_count}] {val}")
            elif act == "[Loop]":
                loop_ms = simpledialog.askinteger("Loop Interval", "ใส่เวลาหน่วงระหว่างคลิกวนลูป (มิลลิวินาที):\n(เช่น 500 = คลิกปุ่มเดิมซ้ำทุกๆ 0.5 วินาทีจนกว่าจะหายไป)", parent=self.root, minvalue=50, maxvalue=10000, initialvalue=500)
                if loop_ms:
                    self.macro_listbox.insert(tk.END, f"[Loop:{loop_ms}] {val}")
            else:
                self.macro_listbox.insert(tk.END, f"{act} {val}")
            
    def remove_macro_step(self):
        sel = self.macro_listbox.curselection()
        if sel:
            self.macro_listbox.delete(sel[0])

    def move_step_up(self):
        sel = self.macro_listbox.curselection()
        if not sel: return
        i = sel[0]
        if i == 0: return
        val = self.macro_listbox.get(i)
        self.macro_listbox.delete(i)
        self.macro_listbox.insert(i-1, val)
        self.macro_listbox.selection_set(i-1)

    def move_step_down(self):
        sel = self.macro_listbox.curselection()
        if not sel: return
        i = sel[0]
        if i == self.macro_listbox.size() - 1: return
        val = self.macro_listbox.get(i)
        self.macro_listbox.delete(i)
        self.macro_listbox.insert(i+1, val)
        self.macro_listbox.selection_set(i+1)

    def edit_macro_step(self):
        sel = self.macro_listbox.curselection()
        if not sel: return
        i = sel[0]
        old_val = self.macro_listbox.get(i)
        new_val = simpledialog.askstring("Edit Step", "แก้ไขคำสั่ง:", initialvalue=old_val, parent=self.root)
        if new_val and new_val != old_val:
            self.macro_listbox.delete(i)
            self.macro_listbox.insert(i, new_val)
            self.macro_listbox.selection_set(i)

    def on_drag_start(self, event):
        self._drag_start_index = self.macro_listbox.nearest(event.y)

    def on_drag_motion(self, event):
        i = self.macro_listbox.nearest(event.y)
        if i < 0 or i >= self.macro_listbox.size():
            return
        if i != self._drag_start_index:
            val = self.macro_listbox.get(self._drag_start_index)
            self.macro_listbox.delete(self._drag_start_index)
            self.macro_listbox.insert(i, val)
            self._drag_start_index = i

    def ask_spam_wait_details(self):
        d = tk.Toplevel(self.root)
        d.title("ตั้งค่า Spam & Wait")
        d.geometry("320x280")
        d.transient(self.root)
        d.grab_set()
        
        result = {}
        
        tk.Label(d, text="1. เลือกรูปปุ่มที่จะสแปมกด:", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
        templates = [f for f in self.macro_combo['values'] if not f.startswith("-- ")]
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
        
        self.root.wait_window(d)
        if 'target' in result:
            return result['target'], result['delay']
        return None

    def ask_multi_loop_details(self):
        d = tk.Toplevel(self.root)
        d.title("ตั้งค่า Loop หลายปุ่ม (Loop Multi-Buttons)")
        d.geometry("350x400")
        d.transient(self.root)
        d.grab_set()
        
        result = {}
        
        tk.Label(d, text="1. เลือกปุ่มทั้งหมดที่จะคลิกวนลูป (เลือกได้มากกว่า 1 ปุ่ม):", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
        
        # Listbox with multiple selection
        frame = tk.Frame(d)
        frame.pack(pady=5, fill="both", expand=True, padx=20)
        
        scrollbar = tk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set, height=8)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        # Populate templates list
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
        
        self.root.wait_window(d)
        if 'templates' in result:
            return result['templates'], result['delay']
        return None

    def ask_loop_control_details(self):
        d = tk.Toplevel(self.root)
        d.title("ตั้งค่าคำสั่ง วนลูป (Loop)")
        d.geometry("320x240")
        d.transient(self.root)
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
        
        self.root.wait_window(d)
        if 'steps' in result:
            return result['steps'], result['duration']
        return None

    def save_macro(self):
        steps = list(self.macro_listbox.get(0, tk.END))
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
                    "recovery_steps": list(self.recovery_listbox.get(0, tk.END)),
                    "timeout_mins": int(self.timeout_var.get()),
                    "package_name": self.package_var.get().strip()
                }
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("Success", "บันทึกคิวมาโครสำเร็จ!")
            except Exception as e:
                messagebox.showerror("Error", f"บันทึกไม่สำเร็จ: {e}")

    def load_macro(self):
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
                
                self.macro_listbox.delete(0, tk.END)
                if isinstance(data, list):
                    for step in data:
                        self.macro_listbox.insert(tk.END, step)
                elif isinstance(data, dict):
                    steps = data.get("steps", [])
                    for step in steps:
                        self.macro_listbox.insert(tk.END, step)
                    
                    self.timeout_var.set(str(data.get("timeout_mins", 5)))
                    self.package_var.set(data.get("package_name", "com.devsisters.crg"))
                    
                    # โหลดคิวกู้คืน
                    self.recovery_listbox.delete(0, tk.END)
                    recovery_steps = data.get("recovery_steps", [])
                    if recovery_steps:
                        for step in recovery_steps:
                            self.recovery_listbox.insert(tk.END, step)
                    
                messagebox.showinfo("Success", "โหลดคิวมาโครสำเร็จ!")
            except Exception as e:
                messagebox.showerror("Error", f"โหลดไม่สำเร็จ: {e}")



    def run_recovery_sequence(self, package_name, loop_count, is_test=False):
        # ดึงสถานะเช็คการทำงาน (ถ้าเป็นทดสอบให้ใช้ test_restart_running, ถ้าไม่ใช่ให้ใช้ macro_running)
        def is_running():
            return self.test_restart_running if is_test else self.macro_running
            
        def set_status(text, color):
            self.root.after(0, lambda: self.status_label.config(text=text, fg=color))
            
        def log_act(msg):
            prefix = "[Test-Restart]" if is_test else "[Anti-Stuck]"
            self.log_bot_activity(f"{prefix} {msg}")
            
        recovery_steps = list(self.recovery_listbox.get(0, tk.END))
        if not recovery_steps:
            log_act("ไม่มีขั้นตอนกู้คืนในคิว (คิวว่าง) ยกเลิกการกู้คืน")
            return False
            
        log_act(f"เริ่มรันขั้นตอนกู้คืนคัสตอม (ทั้งหมด {len(recovery_steps)} ขั้นตอน)")
        
        rec_idx = 0
        recovery_failed = False
        recovery_start = time.time()
        rec_loop_start_times = {}
        
        while rec_idx < len(recovery_steps) and is_running():
            rec_step = recovery_steps[rec_idx]
            
            # -- ปิดเกม --
            if rec_step.startswith("[Force-Stop-Game]"):
                set_status("กู้คืน: สั่งปิดเกม (Force-Stop)...", "orange")
                if self.device and package_name:
                    self.device.shell(f"am force-stop {package_name}")
                time.sleep(1.0)
                rec_idx += 1
                continue
                
            # -- เปิดเกม --
            if rec_step.startswith("[Launch-Game]"):
                set_status("กู้คืน: สั่งเปิดเกมใหม่...", "orange")
                if self.device and package_name:
                    self.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
                time.sleep(1.0)
                rec_idx += 1
                continue
                
            # -- หน่วงเวลา --
            if rec_step.startswith("[Delay-Only]"):
                try:
                    ms = int(rec_step.split(" ")[1].replace("ms", ""))
                    delay_start = time.time()
                    while time.time() - delay_start < (ms / 1000.0) and is_running():
                        elapsed_delay = time.time() - delay_start
                        set_status(f"กู้คืน: กำลังโหลด/หน่วงเวลา... ({elapsed_delay:.1f} วินาที)", "orange")
                        time.sleep(0.2)
                except:
                    time.sleep(1.0)
                rec_idx += 1
                continue
                
            # -- เช็คหน้าล็อบบี้ --
            if rec_step.startswith("[Check-Lobby]"):
                set_status("กู้คืน: ตรวจสอบหน้าล็อบบี้...", "orange")
                lobby_start = time.time()
                lobby_found = False
                while time.time() - lobby_start < 45.0 and is_running():
                    elapsed_rec = time.time() - lobby_start
                    set_status(f"กู้คืน: รอหน้าล็อบบี้... ({elapsed_rec:.1f} วินาที)", "orange")
                    if self.check_lobby_reached():
                        set_status(f"กู้คืน: ถึงหน้าล็อบบี้แล้ว! ({elapsed_rec:.1f} วิ)", "green")
                        time.sleep(1.0)
                        lobby_found = True
                        break
                    time.sleep(0.5)
                if not lobby_found:
                    recovery_failed = True
                rec_idx += 1
                continue
                
            # -- แก้ไขมินิเกม --
            if rec_step.startswith("[Solve-Minigame]"):
                detect_img = "Bot check.png"
                parts = rec_step.split(" ", 1)
                if len(parts) == 2:
                    detect_img = parts[1].strip()
                try:
                    max_val, pos = self.do_template_match_by_name(detect_img)
                    if max_val is not None and max_val >= 0.8:
                        log_act(f"ช่วงกู้คืน: ตรวจพบมินิเกม '{detect_img}' กำลังแก้ไข...")
                        success = self.solve_minigame_action(detect_img)
                        if success:
                            log_act("ช่วงกู้คืน: แก้ไขมินิเกมสำเร็จ!")
                        else:
                            log_act("ช่วงกู้คืน: แก้ไขมินิเกมล้มเหลว")
                except Exception as ex:
                    log_act(f"ช่วงกู้คืน: แก้ไขมินิเกมล้มเหลว: {ex}")
                rec_idx += 1
                continue

            # -- Loop-Control --
            if rec_step.startswith("[Loop-Control:"):
                try:
                    steps_to_jump = int(rec_step.split(":")[1].split("]")[0])
                    duration_sec = int(rec_step.split("Duration:")[1].replace("s", ""))
                    
                    if rec_idx not in rec_loop_start_times:
                        rec_loop_start_times[rec_idx] = time.time()
                        
                    elapsed_loop = time.time() - rec_loop_start_times[rec_idx]
                    if elapsed_loop < duration_sec:
                        remaining = duration_sec - elapsed_loop
                        set_status(f"กู้คืน: วนลูปย้อนกลับ {steps_to_jump} สเต็ป (เหลือ {remaining:.1f} วิ)...", "blue")
                        time.sleep(0.05) # หน่วงนิดเดียวเพื่อไม่ให้กิน CPU หนักเกิน
                        target_idx = max(0, rec_idx - steps_to_jump)
                        rec_idx = target_idx
                        continue
                    else:
                        set_status("กู้คืน: หมดเวลาวนลูป ไปต่อ...", "green")
                        del rec_loop_start_times[rec_idx]
                except Exception as e:
                    logging.error(f"Recovery loop control failed: {e}")
                rec_idx += 1
                continue

            # -- Skip / SkipNot --
            if rec_step.startswith("[Skip:") or rec_step.startswith("[SkipNot:"):
                try:
                    is_skip_if = rec_step.startswith("[Skip:")
                    skip_count = int(rec_step.split(":")[1].split("]")[0])
                    target_name = rec_step.split("]")[1].strip()
                    
                    set_status(f"กู้คืน: ตรวจสอบภาพ '{target_name}' เพื่อข้ามสเต็ป...", "blue")
                    
                    max_val, pos = self.do_template_match_by_name(target_name)
                    found = (max_val is not None and max_val >= 0.8)
                    
                    if (is_skip_if and found) or (not is_skip_if and not found):
                        set_status(f"กู้คืน: เงื่อนไขตรง! ข้าม {skip_count} ขั้นตอนถัดไป", "green")
                        rec_idx += skip_count + 1
                        time.sleep(0.2)
                        continue
                except Exception as e:
                    logging.error(f"Recovery skip parser failed: {e}")
                rec_idx += 1
                continue

            # -- สเต็ปอื่นๆ แบบรวบรัด (Click, Wait) --
            parts = rec_step.split(" ", 1)
            if len(parts) == 2:
                action_type, target_name = parts[0], parts[1]
                if target_name.startswith("[D:"):
                    end_idx = target_name.find("]")
                    if end_idx != -1:
                        target_name = target_name[end_idx+1:].strip()
                
                set_status(f"กู้คืน: {action_type} รอรูป '{target_name}'...", "blue")
                
                step_start = time.time()
                while time.time() - step_start < 10.0 and is_running():
                    max_val, pos = self.do_template_match_by_name(target_name)
                    if max_val is not None and max_val >= 0.8:
                        if action_type == "[Click]":
                            self.device.shell(f"input tap {pos[0]} {pos[1]}")
                        time.sleep(1.0)
                        break
                    time.sleep(0.5)
                    
            rec_idx += 1
            
        if recovery_failed:
            log_act("การกู้คืนล้มเหลว (ไม่พบหน้าล็อบบี้)")
            return False
        else:
            log_act("สิ้นสุดการทำงานขั้นตอนกู้คืนเรียบร้อย")
            return True

    def test_restart_game(self):
        if not self.device:
            messagebox.showwarning("Warning", "กรุณาเชื่อมต่อกับ MuMu Player ก่อนทดสอบครับ")
            return
            
        package_name = self.package_var.get().strip()
        if not package_name:
            messagebox.showwarning("Warning", "กรุณากรอกชื่อแพ็กเกจของเกมก่อนครับ")
            return
            
        if self.macro_running:
            messagebox.showwarning("Warning", "ไม่สามารถรันการทดสอบนี้ขณะมาโครกำลังทำงานอยู่ได้ครับ")
            return

        confirm = messagebox.askyesno("ยืนยัน", "ระบบจะทำการปิดเกม, เปิดใหม่ และทดสอบการกู้คืน (เช็คมินิเกม/สแปมข้ามป๊อปอัปเข้าล็อบบี้)\n\nคุณต้องการเริ่มการทดสอบหรือไม่?")
        if not confirm:
            return

        # Start testing in a background thread to prevent GUI freezing
        import threading
        self.test_restart_running = True
        t = threading.Thread(target=self._run_test_restart_game_thread, args=(package_name,), daemon=True)
        t.start()

    def _run_test_restart_game_thread(self, package_name):
        # Disable buttons temporarily
        self.root.after(0, lambda: self.start_macro_btn.config(state=tk.DISABLED))
        if hasattr(self, 'kill_test_btn'): self.root.after(0, lambda: self.kill_test_btn.config(state=tk.DISABLED))
        if hasattr(self, 'launch_test_btn'): self.root.after(0, lambda: self.launch_test_btn.config(state=tk.DISABLED))
        if hasattr(self, 'restart_test_btn'): self.root.after(0, lambda: self.restart_test_btn.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.stop_macro_btn.config(state=tk.NORMAL))
        
        try:
            success = self.run_recovery_sequence(package_name, loop_count=1, is_test=True)
            
            if self.test_restart_running:
                if not success:
                    self.root.after(0, lambda: self.status_label.config(
                        text="ทดสอบกู้คืน: ล้มเหลว! ไม่พบหน้าล็อบบี้", fg="red"
                    ))
                    self.root.after(0, lambda: messagebox.showwarning("Warning", "ทดสอบกู้คืนล้มเหลว: ค้นหาหน้าล็อบบี้ไม่พบ"))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("Success", "ทดสอบการรีสตาร์ทเกม & กู้คืนสำเร็จ!"))
                    
        except Exception as e:
            logging.error(f"Test recovery thread error: {e}")
            self.root.after(0, lambda err=e: messagebox.showerror("Error", f"การทดสอบล้มเหลว: {err}"))
        finally:
            # Re-enable buttons
            self.root.after(0, lambda: self.start_macro_btn.config(state=tk.NORMAL))
            if hasattr(self, 'kill_test_btn'): self.root.after(0, lambda: self.kill_test_btn.config(state=tk.NORMAL))
            if hasattr(self, 'launch_test_btn'): self.root.after(0, lambda: self.launch_test_btn.config(state=tk.NORMAL))
            if hasattr(self, 'restart_test_btn'): self.root.after(0, lambda: self.restart_test_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_macro_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_label.config(text="Status: Connected", fg="green"))
            self.test_restart_running = False

    def detect_current_package(self):
        if not self.device:
            messagebox.showwarning("Warning", "กรุณาเชื่อมต่อกับ MuMu Player ก่อนครับ")
            return
            
        try:
            # Method 1: dumpsys window
            focus_out = self.device.shell("dumpsys window | grep mCurrentFocus")
            package = self.parse_package_from_string(focus_out)
            
            # Method 2 fallback: dumpsys activity
            if not package:
                resume_out = self.device.shell("dumpsys activity activities | grep mResumedActivity")
                package = self.parse_package_from_string(resume_out)
                
            if package:
                self.package_var.set(package)
                self.status_label.config(text=f"Macro: ดึงชื่อแพ็กเกจ '{package}' สำเร็จ!", fg="green")
                messagebox.showinfo("Success", f"ดึงชื่อแพ็กเกจแอปที่เปิดอยู่สำเร็จ!\n\nชื่อแพ็กเกจ: {package}")
            else:
                messagebox.showwarning("Warning", "ไม่พบแอปที่เปิดอยู่ หรือตรวจหาไม่พบ\nกรุณาเปิดเกม CookieRun ทิ้งไว้บนหน้าจอมือถือจำลองแล้วลองกดใหม่ครับ")
        except Exception as e:
            messagebox.showerror("Error", f"ดึงชื่อแพ็กเกจล้มเหลว: {e}")

    def parse_package_from_string(self, text):
        if not text: return None
        import re
        # Look for com.xxx.yyy/zzz or com.xxx.yyy/.zzz
        match = re.search(r'([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)', text)
        if match:
            return match.group(1)
        return None

    def connect_adb(self):
        try:
            self.status_label.config(text="Status: Starting ADB...", fg="orange")
            self.root.update()
            ensure_adb_server()
            
            client = AdbClient(host="127.0.0.1", port=5037)
            client.remote_connect("127.0.0.1", 7555)
            client.remote_connect("127.0.0.1", 16384)
            
            devices = client.devices()
            if len(devices) == 0:
                self.status_label.config(text="Status: No device found", fg="red")
                return
            
            self.device = devices[0]
            serial = self.device.serial
            
            try:
                wm_size = self.device.shell("wm size")
                if "1920x1080" not in wm_size and "1080x1920" not in wm_size:
                    messagebox.showwarning("เตือนขนาดจอ", "ความละเอียดไม่ใช่ 1080p (1920x1080)\nกรุณาตั้งค่า MuMu เป็น 1080p")
            except Exception:
                pass
            
            self.status_label.config(text=f"Status: Connected ({serial})", fg="green")
            self.create_template_btn.config(state=tk.NORMAL)
            self.test_find_btn.config(state=tk.NORMAL)
            self.play_btn.config(state=tk.NORMAL)
            self.start_macro_btn.config(state=tk.NORMAL)
            if hasattr(self, 'kill_test_btn'): self.kill_test_btn.config(state=tk.NORMAL)
            if hasattr(self, 'launch_test_btn'): self.launch_test_btn.config(state=tk.NORMAL)
            if hasattr(self, 'restart_test_btn'): self.restart_test_btn.config(state=tk.NORMAL)
            if hasattr(self, 'detect_pkg_btn'): self.detect_pkg_btn.config(state=tk.NORMAL)
            self.refresh_templates()
            
        except Exception as e:
            logging.error(traceback.format_exc())
            self.status_label.config(text="Status: Connection Error", fg="red")
            messagebox.showerror("Error", f"เชื่อมต่อไม่สำเร็จ:\n{e}")

    def create_template(self):
        if not self.device: return
        try:
            self.status_label.config(text="Status: Capturing screen...", fg="orange")
            self.root.update()
            screencap = self.device.screencap()
            image_array = np.frombuffer(screencap, np.uint8)
            self.status_label.config(text="Status: Connected", fg="green")
            CropWindow(self.root, image_array, self.save_template_callback)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture screen: {e}")
            
    def save_template_callback(self, name, bgr_image, x1, y1, x2, y2):
        filepath = os.path.join("templates", name)
        is_success, im_buf_arr = cv2.imencode(".png", bgr_image)
        im_buf_arr.tofile(filepath)
        
        config_path = os.path.join("templates", "config.json")
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
        config_data[name] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
            
        messagebox.showinfo("Success", f"บันทึกเทมเพลต '{name}' สำเร็จ!\nระบบจำพิกัดตำแหน่งให้แล้วด้วยครับ")
        self.refresh_templates()

    def rename_template(self):
        old_name = self.template_var.get()
        if not old_name: return
        
        new_name = simpledialog.askstring("Rename", f"เปลี่ยนชื่อ '{old_name}' เป็น:", parent=self.root)
        if not new_name: return
        
        if not new_name.endswith(".png"):
            new_name += ".png"
            
        old_path = os.path.join("templates", old_name)
        new_path = os.path.join("templates", new_name)
        
        if os.path.exists(new_path):
            messagebox.showerror("Error", "ชื่อไฟล์นี้มีอยู่แล้วครับ")
            return
            
        try:
            os.rename(old_path, new_path)
            
            config_path = os.path.join("templates", "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                if old_name in config_data:
                    config_data[new_name] = config_data.pop(old_name)
                    
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("Success", "เปลี่ยนชื่อสำเร็จ!")
            self.refresh_templates()
            self.template_var.set(new_name)
            
            # ถ้าชื่อเก่ามีอยู่ใน Macro Listbox ให้ทำการอัปเดตด้วย (Optional แต่เพื่อความเนียน)
            steps = list(self.macro_listbox.get(0, tk.END))
            for i, step in enumerate(steps):
                parts = step.split(" ", 1)
                if len(parts) == 2 and parts[1] == old_name:
                    self.macro_listbox.delete(i)
                    self.macro_listbox.insert(i, f"{parts[0]} {new_name}")
                    
        except Exception as e:
            messagebox.showerror("Error", f"เปลี่ยนชื่อไม่สำเร็จ: {e}")

    def delete_template(self):
        name = self.template_var.get()
        if not name: return
        
        confirm = messagebox.askyesno("Delete Template", f"คุณต้องการลบภาพต้นแบบ '{name}' ใช่หรือไม่?\n(การกระทำนี้ไม่สามารถย้อนกลับได้)", parent=self.root)
        if not confirm: return
        
        path = os.path.join("templates", name)
        try:
            if os.path.exists(path):
                os.remove(path)
                
            config_path = os.path.join("templates", "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    if name in config_data:
                        config_data.pop(name)
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, ensure_ascii=False, indent=4)
                except Exception as ex:
                    logging.error(f"Error updating config during delete: {ex}")
            
            messagebox.showinfo("Success", f"ลบภาพต้นแบบ '{name}' สำเร็จแล้วครับ!")
            self.refresh_templates()
            # Clear or select new template
            files = glob.glob("templates/*.png")
            if files:
                first_name = os.path.basename(files[0])
                self.template_var.set(first_name)
            else:
                self.template_var.set("")
        except Exception as e:
            messagebox.showerror("Error", f"ลบภาพไม่สำเร็จ: {e}")

    def log_bot_activity(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        print(log_line, end="")
        try:
            with open("bot_run.log", "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logging.error(f"Failed to write to bot_run.log: {e}")

    def check_lobby_reached(self):
        # Find all templates starting with "Lobby" (e.g. Lobby 1.png, Lobby 3.png, Lobby 4.png)
        lobby_files = glob.glob("templates/Lobby*.png")
        if not lobby_files:
            # Fallback if no files start with Lobby
            val, pos = self.do_template_match_by_name("Lobby.png")
            return val is not None and val >= 0.8
            
        for file_path in lobby_files:
            name = os.path.basename(file_path)
            val, pos = self.do_template_match_by_name(name)
            if val is not None and val >= 0.8:
                self.log_bot_activity(f"[Lobby Check] ตรวจพบหน้าล็อบบี้สำเร็จจากรูป '{name}' (ความแม่นยำ: {val*100:.1f}%)")
                return True
        return False

    def do_template_match_by_name(self, template_name):
        if not self.device: return None, None
        template_path = os.path.join("templates", template_name)
        if not os.path.exists(template_path):
            return None, None
            
        screencap = self.device.screencap()
        image_array = np.frombuffer(screencap, np.uint8)
        screen_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        template_array = np.fromfile(template_path, np.uint8)
        template_img = cv2.imdecode(template_array, cv2.IMREAD_COLOR)
        
        config_path = os.path.join("templates", "config.json")
        search_roi = None
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                if template_name in config_data:
                    c = config_data[template_name]
                    pad = 20
                    h_screen, w_screen = screen_img.shape[:2]
                    x1, y1 = max(0, c["x1"] - pad), max(0, c["y1"] - pad)
                    x2, y2 = min(w_screen, c["x2"] + pad), min(h_screen, c["y2"] + pad)
                    search_roi = (x1, y1, x2, y2)
        
        if search_roi:
            x1, y1, x2, y2 = search_roi
            roi_img = screen_img[y1:y2, x1:x2]
            result = cv2.matchTemplate(roi_img, template_img, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            h, w = template_img.shape[:2]
            center_x = max_loc[0] + x1 + w // 2
            center_y = max_loc[1] + y1 + h // 2
        else:
            result = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            h, w = template_img.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
        return max_val, (center_x, center_y)

    def solve_minigame_action(self, detect_img="Bot check.png"):
        if not self.device: return False
        
        attempt = 1
        max_attempts = 10
        
        while attempt <= max_attempts and (self.macro_running or self.test_restart_running):
            # Check if the minigame is still active
            max_val, _ = self.do_template_match_by_name(detect_img)
            if max_val is None or max_val < 0.8:
                self.root.after(0, lambda: self.status_label.config(
                    text="Macro: มินิเกมหายไปแล้ว (ผ่านสำเร็จ)!", fg="green"
                ))
                return True
                
            self.root.after(0, lambda att=attempt: self.status_label.config(
                text=f"Macro: แก้ไขมินิเกม รอบที่ {att}...", fg="orange"
            ))
            
            screencap = self.device.screencap()
            image_array = np.frombuffer(screencap, np.uint8)
            screen_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if screen_img is None:
                return False
                
            orig_h, orig_w = screen_img.shape[:2]
            
            # Resize screen_img to 1920x1080 for processing coordinates
            if orig_w != 1920 or orig_h != 1080:
                proc_img = cv2.resize(screen_img, (1920, 1080))
            else:
                proc_img = screen_img
                
            centers = [
                (655, 449),  # Card 1
                (949, 449),  # Card 2
                (1243, 449), # Card 3
                (655, 834),  # Card 4
                (949, 834),  # Card 5
                (1243, 834)  # Card 6
            ]
            
            crops = []
            for cx, cy in centers:
                crop = proc_img[cy-100:cy+100, cx-80:cx+80]
                crops.append(crop)
                
            grays = [cv2.cvtColor(c, cv2.COLOR_BGR2GRAY) for c in crops]
            
            diff_scores = []
            for i in range(6):
                total_diff = 0
                for j in range(6):
                    if i == j: continue
                    err = np.sum((grays[i].astype("float") - grays[j].astype("float")) ** 2)
                    err /= float(grays[i].shape[0] * grays[i].shape[1])
                    total_diff += err
                diff_scores.append((i, total_diff))
                
            sorted_by_diff = sorted(diff_scores, key=lambda x: x[1], reverse=True)
            
            click1_idx = sorted_by_diff[0][0]
            click2_idx = sorted_by_diff[1][0]
            
            c1_x, c1_y = centers[click1_idx]
            c2_x, c2_y = centers[click2_idx]
            
            # Scale coordinates if needed
            if orig_w != 1920 or orig_h != 1080:
                scale_x = orig_w / 1920.0
                scale_y = orig_h / 1080.0
                tap1_x, tap1_y = int(c1_x * scale_x), int(c1_y * scale_y)
                tap2_x, tap2_y = int(c2_x * scale_x), int(c2_y * scale_y)
            else:
                tap1_x, tap1_y = c1_x, c1_y
                tap2_x, tap2_y = c2_x, c2_y
                
            # Click the two different cards (short delay between clicks)
            self.device.shell(f"input tap {tap1_x} {tap1_y}")
            time.sleep(0.5)
            self.device.shell(f"input tap {tap2_x} {tap2_y}")
            
            # Wait for animation/shuffle before checking again
            time.sleep(1.0)
            attempt += 1
            
        return False

    def test_find(self):
        name = self.template_var.get()
        if not name: return
        self.status_label.config(text=f"Status: Searching for {name}...", fg="orange")
        self.root.update()
        max_val, pos = self.do_template_match_by_name(name)
        self.status_label.config(text="Status: Connected", fg="green")
        if max_val is None: return
        
        if max_val >= 0.8:
            messagebox.showinfo("เจอภาพ!", f"✅ ความมั่นใจ: {max_val*100:.1f}%\nพิกัด: {pos}")
        else:
            messagebox.showwarning("ไม่เจอภาพ", f"❌ ความมั่นใจต่ำเกินไป ({max_val*100:.1f}%)")

    def find_and_click(self):
        name = self.template_var.get()
        if not name: return
        self.status_label.config(text=f"Status: Searching for {name}...", fg="orange")
        self.root.update()
        max_val, pos = self.do_template_match_by_name(name)
        self.status_label.config(text="Status: Connected", fg="green")
        if max_val is None: return
        
        if max_val >= 0.8:
            self.device.shell(f"input tap {pos[0]} {pos[1]}")
            messagebox.showinfo("คลิกแล้ว!", f"สั่งคลิกพิกัด {pos} สำเร็จ!\n(มั่นใจ {max_val*100:.1f}%)")
        else:
            messagebox.showwarning("ไม่คลิก", f"ความมั่นใจแค่ {max_val*100:.1f}%")

    # --- MACRO ENGINE ---
    def start_macro(self):
        steps = self.macro_listbox.get(0, tk.END)
        if not steps:
            messagebox.showwarning("เตือน", "กรุณาเพิ่มสเต็ปลงใน Macro ก่อนครับ")
            return
            
        self.macro_running = True
        self.start_macro_btn.config(state=tk.DISABLED)
        self.stop_macro_btn.config(state=tk.NORMAL)
        self.create_template_btn.config(state=tk.DISABLED)
        
        # รันใน Thread เพื่อไม่ให้ UI ค้าง
        threading.Thread(target=self.macro_worker, args=(steps,), daemon=True).start()

    def stop_macro(self):
        self.macro_running = False
        self.test_restart_running = False
        self.status_label.config(text="Status: Stopping...", fg="red")

    def macro_worker(self, steps):
        try:
            loop_count = 1
            self.loop_start_times = {} # เก็บเวลาเริ่มรันของสเต็ปวนลูปแต่ละดัชนี
            while self.macro_running: # ลูปทำงานแบบ Infinite จนกว่าจะกด Stop
                i = 0
                while i < len(steps) and self.macro_running:
                    step_item = steps[i]
                    
                    # -- จัดการโหมด Standalone Delay --
                    if step_item.startswith("[Delay-Only]"):
                        try:
                            ms = int(step_item.split(" ")[1].replace("ms", ""))
                            self.root.after(0, lambda lc=loop_count, m=ms: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: หน่วงเวลา (Delay) {m} ms...", fg="blue"
                            ))
                            time.sleep(ms / 1000.0)
                        except:
                            pass
                        i += 1
                        continue
                        
                    # -- จัดการโหมด วนลูปย้อนกลับตามระยะเวลา (Loop Control by Duration) --
                    if step_item.startswith("[Loop-Control:"):
                        try:
                            # รูปแบบคำสั่ง: [Loop-Control:2] Duration:30s
                            steps_to_jump = int(step_item.split(":")[1].split("]")[0])
                            duration_sec = int(step_item.split("Duration:")[1].replace("s", ""))
                            
                            # บันทึกเวลาเริ่มต้นของสเต็ปนี้ หากเป็นการเข้าถึงครั้งแรก
                            if i not in self.loop_start_times:
                                self.loop_start_times[i] = time.time()
                                
                            elapsed_loop = time.time() - self.loop_start_times[i]
                            if elapsed_loop < duration_sec:
                                remaining = duration_sec - elapsed_loop
                                self.root.after(0, lambda lc=loop_count, s=steps_to_jump, el=elapsed_loop, rem=remaining: self.status_label.config(
                                    text=f"Macro [รอบ {lc}]: วนลูปย้อนกลับ {s} สเต็ป (รันแล้ว {el:.1f}/{duration_sec} วิ, เหลือ {rem:.1f} วิ)...", fg="blue"
                                ))
                                time.sleep(0.05) # ลดการหน่วงเวลาเพื่อให้ลูปทำงานเร็วขึ้น
                                target_idx = max(0, i - steps_to_jump)
                                i = target_idx - 1
                            else:
                                # เลยกำหนดระยะเวลาวนลูปแล้ว ให้ข้ามการวนลูปไปขั้นตอนต่อไป
                                self.root.after(0, lambda lc=loop_count: self.status_label.config(
                                    text=f"Macro [รอบ {lc}]: หมดระยะเวลาวนลูปแล้ว ไปต่อ...", fg="green"
                                ))
                                del self.loop_start_times[i] # ลบเวลาเริ่มต้นเพื่อให้รอบการรันหลักใหม่เริ่มนับหนึ่งใหม่
                        except Exception as e:
                            logging.error(f"Loop control parser failed: {e}")
                        i += 1
                        continue
                    
                    # -- จัดการโหมด ปิดแอปเกม --
                    if step_item.startswith("[Force-Stop-Game]"):
                        package_name = self.package_var.get().strip()
                        self.root.after(0, lambda lc=loop_count, pkg=package_name: self.status_label.config(
                            text=f"Macro [รอบ {lc}]: สั่งปิดเกม ({pkg})...", fg="orange"
                        ))
                        if self.device and package_name:
                            self.device.shell(f"am force-stop {package_name}")
                        time.sleep(1.0)
                        i += 1
                        continue
                        
                    # -- จัดการโหมด เปิดแอปเกม --
                    if step_item.startswith("[Launch-Game]"):
                        package_name = self.package_var.get().strip()
                        self.root.after(0, lambda lc=loop_count, pkg=package_name: self.status_label.config(
                            text=f"Macro [รอบ {lc}]: สั่งเปิดเกม ({pkg})...", fg="orange"
                        ))
                        if self.device and package_name:
                            self.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
                        time.sleep(1.0)
                        i += 1
                        continue
                        
                    # -- จัดการโหมด ตรวจสอบหน้าล็อบบี้ --
                    if step_item.startswith("[Check-Lobby]"):
                        self.root.after(0, lambda lc=loop_count: self.status_label.config(
                            text=f"Macro [รอบ {lc}]: รอตรวจพบหน้าล็อบบี้ (Lobby)...", fg="blue"
                        ))
                        step_start_time = time.time()
                        try:
                            timeout_limit = int(self.timeout_var.get()) * 60
                        except:
                            timeout_limit = 300
                            
                        lobby_reached = False
                        while self.macro_running:
                            elapsed = time.time() - step_start_time
                            self.root.after(0, lambda lc=loop_count, el=elapsed, tl=timeout_limit: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: รอตรวจพบหน้าล็อบบี้... ({int(el)}/{tl} วิ)", fg="blue"
                            ))
                            if self.check_lobby_reached():
                                lobby_reached = True
                                break
                            if elapsed > timeout_limit:
                                break
                            time.sleep(0.5)
                            
                        if lobby_reached:
                            self.root.after(0, lambda lc=loop_count: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: ถึงหน้าล็อบบี้แล้ว!", fg="green"
                            ))
                            time.sleep(1.0)
                        else:
                            self.log_bot_activity(f"[รอบที่ {loop_count}] หมดเวลารอหน้าล็อบบี้")
                        i += 1
                        continue
                    
                    # -- จัดการโหมด Solve-Minigame --
                    if step_item.startswith("[Solve-Minigame]"):
                        detect_img = "Bot check.png"
                        parts = step_item.split(" ", 1)
                        if len(parts) == 2:
                            detect_img = parts[1].strip()
                        
                        self.root.after(0, lambda lc=loop_count, di=detect_img: self.status_label.config(
                            text=f"Macro [รอบ {lc}]: ตรวจมินิเกมด้วยรูป '{di}'...", fg="blue"
                        ))
                        
                        max_val, pos = self.do_template_match_by_name(detect_img)
                        if max_val is not None and max_val >= 0.8:
                            self.log_bot_activity(f"[รอบที่ {loop_count}] ตรวจพบมินิเกมด้วยรูป '{detect_img}' (ความมั่นใจ: {max_val*100:.1f}%) กำลังเริ่มแก้ไข...")
                            self.root.after(0, lambda lc=loop_count: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: ตรวจพบมินิเกม! กำลังแก้ไข...", fg="orange"
                            ))
                            time.sleep(1.0)
                            
                            try:
                                success = self.solve_minigame_action(detect_img)
                                if success:
                                    self.log_bot_activity(f"[รอบที่ {loop_count}] แก้ไขมินิเกมสำเร็จ!")
                                    self.root.after(0, lambda lc=loop_count: self.status_label.config(
                                        text=f"Macro [รอบ {lc}]: แก้ไขมินิเกมสำเร็จ!", fg="green"
                                    ))
                                else:
                                    self.log_bot_activity(f"[รอบที่ {loop_count}] แก้ไขมินิเกมล้มเหลว")
                                    self.root.after(0, lambda lc=loop_count: self.status_label.config(
                                        text=f"Macro [รอบ {lc}]: แก้ไขมินิเกมล้มเหลว", fg="red"
                                    ))
                            except Exception as ex:
                                self.log_bot_activity(f"[รอบที่ {loop_count}] แก้ไขมินิเกมเกิดข้อผิดพลาด: {ex}")
                                logging.error(f"Solve Minigame error: {ex}")
                                self.root.after(0, lambda lc=loop_count, e=ex: self.status_label.config(
                                    text=f"Macro [รอบ {lc}]: เกิดข้อผิดพลาด: {e}", fg="red"
                                ))
                            time.sleep(3.0)
                        else:
                            self.root.after(0, lambda lc=loop_count: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: ไม่พบมินิเกม, ข้ามไป...", fg="green"
                            ))
                            time.sleep(0.2)
                        
                        i += 1
                        continue
                    
                    parts = step_item.split(" ", 1)
                    if len(parts) != 2: 
                        i += 1
                        continue
                    action, rest = parts[0], parts[1]
                    
                    delay_ms = 2000 # default delay
                    
                    # Parse optional Spam Target and Spam Interval
                    spam_target = None
                    spam_interval = 600 # Default spam interval
                    
                    if action in ["[Spam-Wait]", "[Spam-Click]"]:
                        if rest.startswith("["):
                            e_idx = rest.find("]")
                            if e_idx != -1:
                                spam_target = rest[1:e_idx]
                                rest = rest[e_idx+1:].strip()
                                
                        if rest.startswith("[S:"):
                            e_idx = rest.find("]")
                            if e_idx != -1:
                                try:
                                    spam_interval = int(rest[3:e_idx])
                                except ValueError:
                                    pass
                                rest = rest[e_idx+1:].strip()
                                
                    step_name = rest
                    
                    # Parse optional Delay [D:ms]
                    if rest.startswith("[D:"):
                        end_idx = rest.find("]")
                        if end_idx != -1:
                            try:
                                delay_ms = int(rest[3:end_idx])
                            except ValueError:
                                pass
                            step_name = rest[end_idx+1:].strip()
                    
                    # -- จัดการโหมด Skip-If --
                    if action.startswith("[Skip:"):
                        skip_count = int(action.split(":")[1][:-1]) # ดึงเลข N จาก [Skip:N]
                        self.root.after(0, lambda sn=step_name, lc=loop_count: self.status_label.config(
                            text=f"Macro [รอบ {lc}]: เช็คภาพ '{sn}' ว่าต้องข้ามหรือไม่...", fg="blue"
                        ))
                        # เช็คแค่ครั้งเดียว ไม่วนรอ
                        max_val, pos = self.do_template_match_by_name(step_name)
                        if max_val is not None and max_val >= 0.8:
                            self.root.after(0, lambda sn=step_name, sc=skip_count: self.status_label.config(
                                text=f"Macro: เจอ '{sn}' สั่งกระโดดข้าม {sc} สเต็ป!", fg="orange"
                            ))
                            time.sleep(0.5)
                            i += (skip_count + 1) # ข้ามไป N สเต็ป
                        else:
                            i += 1 # ไม่เจอภาพ ก็ให้ทำสเต็ปถัดไปตามปกติ
                        continue

                    # -- จัดการโหมด Skip-IfNot --
                    if action.startswith("[SkipNot:"):
                        skip_count = int(action.split(":")[1][:-1]) # ดึงเลข N จาก [SkipNot:N]
                        self.root.after(0, lambda sn=step_name, lc=loop_count: self.status_label.config(
                            text=f"Macro [รอบ {lc}]: เช็คภาพ '{sn}' ว่าต้องข้ามหรือไม่...", fg="blue"
                        ))
                        # เช็คแค่ครั้งเดียว ไม่วนรอ
                        max_val, pos = self.do_template_match_by_name(step_name)
                        if max_val is None or max_val < 0.8:
                            self.root.after(0, lambda sn=step_name, sc=skip_count: self.status_label.config(
                                text=f"Macro: ไม่เจอ '{sn}' สั่งกระโดดข้าม {sc} สเต็ป!", fg="orange"
                            ))
                            time.sleep(0.5)
                            i += (skip_count + 1) # ข้ามไป N สเต็ป
                        else:
                            i += 1 # เจอภาพ ก็ให้ทำสเต็ปถัดไปตามปกติ
                        continue
                        
                    # -- โหมดอื่นๆ (Click, Wait) --
                    self.root.after(0, lambda sn=step_name, lc=loop_count, act=action: self.status_label.config(
                        text=f"Macro [รอบ {lc}]: {act} รอภาพ '{sn}'...", fg="blue"
                    ))
                    
                    # เช็ครัวๆ จนกว่าจะเจอภาพของสเต็ปนี้
                    spam_thread_active = False
                    self.spam_running = False
                    
                    step_start_time = time.time()
                    try:
                        timeout_limit = int(self.timeout_var.get()) * 60
                    except:
                        timeout_limit = 300

                    while self.macro_running:
                        # เริ่ม Thread สแปมปุ่ม (ทำแค่ครั้งเดียวตอนเริ่มสเต็ปนี้)
                        if action in ["[Spam-Wait]", "[Spam-Click]"] and spam_target and not spam_thread_active:
                            self.spam_running = True
                            spam_thread_active = True
                            
                            tap_cmd = None
                            if "," in spam_target:
                                try:
                                    sx, sy = map(int, spam_target.split(","))
                                    tap_cmd = f"input tap {sx} {sy}"
                                except: pass
                            else:
                                config_path = os.path.join("templates", "config.json")
                                if os.path.exists(config_path):
                                    try:
                                        with open(config_path, 'r', encoding='utf-8') as f:
                                            cfg = json.load(f)
                                        if spam_target in cfg:
                                            c = cfg[spam_target]
                                            cx = (c['x1'] + c['x2']) // 2
                                            cy = (c['y1'] + c['y2']) // 2
                                            tap_cmd = f"input tap {cx} {cy}"
                                    except: pass
                                    
                            if tap_cmd:
                                def spammer(cmd, interval):
                                    while self.spam_running and self.macro_running:
                                        self.device.shell(cmd)
                                        time.sleep(interval / 1000.0)
                                        
                                threading.Thread(target=spammer, args=(tap_cmd, spam_interval), daemon=True).start()
                                self.root.after(0, lambda sn=step_name, sp=spam_target: self.status_label.config(
                                    text=f"Macro: เริ่มสแปมพิกัด '{sp}' เบื้องหลังแล้ว! กำลังรอภาพ '{sn}'...", fg="orange"
                                ))
                            else:
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: ผิดพลาด ไม่พบพิกัด '{spam_target}' ในระบบ (รอภาพ '{sn}' ต่อไป)", fg="red"
                                ))

                        # Update elapsed waiting status
                        elapsed = time.time() - step_start_time
                        if action in ["[Spam-Wait]", "[Spam-Click]"]:
                            self.root.after(0, lambda sn=step_name, lc=loop_count, sp=spam_target or "", el=elapsed, tl=timeout_limit: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: สแปม '{sp}' รอภาพ '{sn}'... ({int(el)}/{tl} วิ)", fg="orange"
                            ))
                        else:
                            self.root.after(0, lambda sn=step_name, lc=loop_count, act=action, el=elapsed, tl=timeout_limit: self.status_label.config(
                                text=f"Macro [รอบ {lc}]: {act} รอภาพ '{sn}'... ({int(el)}/{tl} วิ)", fg="blue"
                            ))

                        max_val, pos = self.do_template_match_by_name(step_name)
                        
                        if max_val is not None and max_val >= 0.8:
                            self.spam_running = False # หยุด Thread สแปม
                            
                            if action == "[Click]":
                                self.device.shell(f"input tap {pos[0]} {pos[1]}")
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: คลิก '{sn}' แล้ว!", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 2.0)
                            elif action == "[Spam-Click]":
                                self.device.shell(f"input tap {pos[0]} {pos[1]}")
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: เจอภาพ '{sn}' สั่งหยุดสแปมและคลิกภาพแล้ว!", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 2.0)
                            elif action == "[Spam-Wait]":
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: เจอภาพ '{sn}' แล้ว สั่งหยุดสแปมและไปต่อ (ไม่กด)...", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 0.5)
                            elif action == "[Break]":
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: เจอภาพ '{sn}' บังคับหยุดการทำงานมาโคร (Break)!", fg="red"
                                ))
                                self.log_bot_activity(f"Macro: ตรวจพบภาพ '{sn}' (คำสั่ง [Break]) สั่งหยุดมาโครและจบการทำงาน")
                                self.macro_running = False
                                break
                            else: # [Wait]
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: เจอภาพ '{sn}' แล้ว (ไม่กด) ไปสเต็ปถัดไป...", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 0.5)
                            break # หลุดลูปเพื่อไปทำสเต็ปต่อไปใน List
                            
                        # Check for timeout
                        elapsed = time.time() - step_start_time
                        if elapsed > timeout_limit:
                            self.spam_running = False # หยุด Thread สแปม
                            stuck_action = "รีสตาร์ทเกม & เริ่มใหม่"
                            package_name = self.package_var.get().strip()
                            
                            self.log_bot_activity(f"[Anti-Stuck] รอบที่ {loop_count} ตรวจพบหน้าจอค้างที่ขั้นตอน '{step_name}' นานเกิน {timeout_limit} วินาที (เริ่มทำ: '{stuck_action}')")
                            
                            # Capture and save stuck screenshot
                            try:
                                if self.device:
                                    screencap = self.device.screencap()
                                    if screencap:
                                        os.makedirs("stuck_screenshots", exist_ok=True)
                                        clean_step_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in step_name])
                                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                                        screenshot_filename = f"stuck_{timestamp}_{clean_step_name}.png"
                                        screenshot_path = os.path.join("stuck_screenshots", screenshot_filename)
                                        with open(screenshot_path, "wb") as f:
                                            f.write(screencap)
                                        self.log_bot_activity(f"[Anti-Stuck] บันทึกภาพหน้าจอค้างไว้ที่ '{screenshot_path}'")
                            except Exception as cap_ex:
                                self.log_bot_activity(f"[Anti-Stuck] ไม่สามารถบันทึกภาพหน้าจอค้างได้: {cap_ex}")
                                logging.error(f"Failed to capture stuck screenshot: {cap_ex}")
                                
                            self.root.after(0, lambda sn=step_name, sa=stuck_action: self.status_label.config(
                                text=f"Macro: ภาพ '{sn}' ไม่มาตามเวลา! กำลังทำ: {sa}", fg="red"
                            ))
                            time.sleep(2.0)
                            if self.device and package_name:
                                self.run_recovery_sequence(package_name, loop_count, is_test=False)
                                i = -1
                                break
                            else:
                                self.macro_running = False
                                break

                        # ถ้ายังไม่เจอภาพเป้าหมาย ให้รอสักพักก่อนแคปใหม่ (ถ้ามีสแปม Thread รันอยู่แล้ว ไม่ต้องสนใจ)
                        if not spam_thread_active:
                            time.sleep(1.0)
                        
                    i += 1 # ไปสเต็ปต่อไปตามปกติ
                        
                loop_count += 1
                
        except Exception as e:
            logging.error(f"Macro Thread Error: {traceback.format_exc()}")
        finally:
            self.macro_running = False
            self.root.after(0, lambda: self.start_macro_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_macro_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.create_template_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_label.config(text="Status: Macro Stopped", fg="red"))

if __name__ == "__main__":
    root = tk.Tk()
    app = CookieRunBotUI(root)
    root.mainloop()
