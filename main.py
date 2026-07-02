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
        self.root.geometry("500x550")
        
        self.device = None
        self.macro_running = False
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
        
        self.setup_template_tab()
        self.setup_macro_tab()

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
        
        tk.Label(f_add, text="Action:").pack(side=tk.LEFT, padx=(5, 0))
        self.macro_action_var = tk.StringVar(value="[Click]")
        self.macro_action_combo = ttk.Combobox(f_add, textvariable=self.macro_action_var, state="readonly", width=12)
        self.macro_action_combo['values'] = ["[Click]", "[Wait]", "[Spam-Wait]", "[Skip-If]"]
        self.macro_action_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Button(f_add, text="เพิ่มสเต็ป", command=self.add_macro_step, bg="#E0E0E0").pack(side=tk.LEFT, padx=5)
        
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

    def refresh_templates(self):
        files = glob.glob("templates/*.png")
        names = [os.path.basename(f) for f in files]
        self.template_combo['values'] = names
        
        # เพิ่มเมนูพิเศษสำหรับ Macro
        macro_opts = ["-- เพิ่มเวลาหน่วง (Delay) --"] + names
        self.macro_combo['values'] = macro_opts
        
        if names:
            self.template_combo.current(0)
            if hasattr(self, 'rename_btn'): self.rename_btn.config(state=tk.NORMAL)
        else:
            if hasattr(self, 'rename_btn'): self.rename_btn.config(state=tk.DISABLED)
            
        if macro_opts:
            self.macro_combo.current(0)

    def restart_app(self):
        self.macro_running = False
        self.root.destroy()
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)

    def add_macro_step(self):
        val = self.macro_template_var.get()
        act = self.macro_action_var.get()
            
        if val == "-- เพิ่มเวลาหน่วง (Delay) --":
            delay_ms = simpledialog.askinteger("Delay Time", "ใส่เวลาที่ต้องการหน่วง\n(หน่วยเป็นมิลลิวินาที เช่น 1000 = 1 วินาที):", parent=self.root, minvalue=1, maxvalue=600000)
            if delay_ms:
                self.macro_listbox.insert(tk.END, f"[Delay-Only] {delay_ms}ms")
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
        templates = [f for f in self.macro_combo['values'] if f != "-- เพิ่มเวลาหน่วง (Delay) --"]
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
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(steps, f, ensure_ascii=False, indent=4)
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
                    steps = json.load(f)
                
                self.macro_listbox.delete(0, tk.END)
                for step in steps:
                    self.macro_listbox.insert(tk.END, step)
                    
                messagebox.showinfo("Success", "โหลดคิวมาโครสำเร็จ!")
            except Exception as e:
                messagebox.showerror("Error", f"โหลดไม่สำเร็จ: {e}")

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
        self.status_label.config(text="Status: Stopping Macro...", fg="red")

    def macro_worker(self, steps):
        try:
            loop_count = 1
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
                        
                    # -- โหมดอื่นๆ (Click, Wait) --
                    self.root.after(0, lambda sn=step_name, lc=loop_count, act=action: self.status_label.config(
                        text=f"Macro [รอบ {lc}]: {act} รอภาพ '{sn}'...", fg="blue"
                    ))
                    
                    # เช็ครัวๆ จนกว่าจะเจอภาพของสเต็ปนี้
                    spam_thread_active = False
                    self.spam_running = False

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

                        max_val, pos = self.do_template_match_by_name(step_name)
                        
                        if max_val is not None and max_val >= 0.8:
                            self.spam_running = False # หยุด Thread สแปม
                            
                            if action == "[Click]":
                                self.device.shell(f"input tap {pos[0]} {pos[1]}")
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: คลิก '{sn}' แล้ว!", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 2.0)
                            elif action in ["[Spam-Wait]", "[Spam-Click]"]:
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: เจอภาพ '{sn}' แล้ว สั่งหยุดสแปมและไปต่อ (ไม่กด)...", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 0.5)
                            else: # [Wait]
                                self.root.after(0, lambda sn=step_name: self.status_label.config(
                                    text=f"Macro: เจอภาพ '{sn}' แล้ว (ไม่กด) ไปสเต็ปถัดไป...", fg="green"
                                ))
                                time.sleep(delay_ms / 1000.0 if rest.startswith("[D:") else 0.5)
                            break # หลุดลูปเพื่อไปทำสเต็ปต่อไปใน List
                            
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
