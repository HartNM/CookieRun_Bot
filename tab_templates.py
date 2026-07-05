"""
tab_templates.py
UI and logic for the Templates tab (Tab 1).
Handles: capture, rename, delete, test-find, find-and-click templates.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk
import cv2
import os
import glob
import json
import logging

from ui_components import CropWindow


class TemplatesTab:
    """Manages the 🛠️ Templates tab."""

    def __init__(self, parent_frame, app):
        """
        :param parent_frame: tk.Frame — the notebook tab frame
        :param app: CookieRunBotUI — main app instance (for device, status_label, etc.)
        """
        self.app = app
        self._build_ui(parent_frame)

    def _build_ui(self, frame):
        # --- Create Template ---
        f_create = tk.LabelFrame(frame, text="2. สร้างภาพปุ่มใหม่ (ลากครอบเอง)")
        f_create.pack(fill="x", padx=10, pady=10)
        f_btns = tk.Frame(f_create)
        f_btns.pack(fill="x", padx=10, pady=10)

        self.create_template_btn = tk.Button(
            f_btns, text="Capture & Crop New Template...",
            command=self.create_template, state=tk.DISABLED
        )
        self.create_template_btn.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))

        self.import_template_btn = tk.Button(
            f_btns, text="Import Image & Crop...",
            command=self.import_template, bg="#FFF9C4"
        )
        self.import_template_btn.pack(side=tk.LEFT, fill="x", expand=True)

        # --- Manage Templates ---
        f_test = tk.LabelFrame(frame, text="3. จัดการภาพที่เซฟไว้")
        f_test.pack(fill="x", padx=10, pady=10)

        top_test = tk.Frame(f_test)
        top_test.pack(fill="x", padx=10, pady=5)

        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(top_test, textvariable=self.template_var, state="readonly")
        self.template_combo.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))

        self.rename_btn = tk.Button(top_test, text="✏️ เปลี่ยนชื่อ", command=self.rename_template, state=tk.DISABLED)
        self.rename_btn.pack(side=tk.LEFT)

        self.delete_btn = tk.Button(
            top_test, text="🗑️ ลบภาพ", command=self.delete_template,
            state=tk.DISABLED, bg="#FFCDD2", fg="#C62828"
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(5, 0))

        b_frame = tk.Frame(f_test)
        b_frame.pack(pady=5)
        self.test_find_btn = tk.Button(
            b_frame, text="Test Find (แค่หาเฉยๆ)", command=self.test_find,
            width=20, state=tk.DISABLED, bg="#2196F3", fg="white"
        )
        self.test_find_btn.pack(side=tk.LEFT, padx=5)
        self.play_btn = tk.Button(
            b_frame, text="Find & Click (กดจริง)", command=self.find_and_click,
            width=20, state=tk.DISABLED, bg="#4CAF50", fg="white"
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def refresh_templates(self):
        """Reload template list from disk and update combo values."""
        files = glob.glob("templates/*.png")
        names = [os.path.basename(f) for f in files]
        self.template_combo['values'] = names
        if names:
            self.template_combo.current(0)
            self.rename_btn.config(state=tk.NORMAL)
            self.delete_btn.config(state=tk.NORMAL)
        else:
            self.rename_btn.config(state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
        return names

    def enable_buttons(self):
        self.create_template_btn.config(state=tk.NORMAL)
        self.test_find_btn.config(state=tk.NORMAL)
        self.play_btn.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def create_template(self):
        app = self.app
        if not app.device:
            return
        try:
            app.status_label.config(text="Status: Capturing screen...", fg="orange")
            app.root.update()
            import numpy as np
            screencap = app.device.screencap()
            image_array = np.frombuffer(screencap, np.uint8)
            app.status_label.config(text="Status: Connected", fg="green")
            CropWindow(app.root, image_array, self._save_template_callback)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture screen: {e}")

    def import_template(self):
        from tkinter import filedialog
        import numpy as np
        app = self.app
        filepath = filedialog.askopenfilename(
            initialdir=os.path.join(os.getcwd(), "stuck_screenshots"),
            title="เลือกไฟล์รูปภาพที่ต้องการครอบ",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not filepath:
            return
        try:
            with open(filepath, 'rb') as f:
                image_bytes = f.read()
            image_array = np.frombuffer(image_bytes, np.uint8)
            CropWindow(app.root, image_array, self._save_template_callback)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")

    def _save_template_callback(self, name, bgr_image, x1, y1, x2, y2):
        filepath = os.path.join("templates", name)
        _, im_buf_arr = cv2.imencode(".png", bgr_image)
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
        self.app.refresh_templates()

    def rename_template(self):
        app = self.app
        old_name = self.template_var.get()
        if not old_name:
            return

        new_name = simpledialog.askstring("Rename", f"เปลี่ยนชื่อ '{old_name}' เป็น:", parent=app.root)
        if not new_name:
            return

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
            app.refresh_templates()
            self.template_var.set(new_name)

            # Update macro/recovery listboxes and macro files if old name is referenced
            import re

            def replace_template(step_str):
                padded = " " + step_str + " "
                pattern = r'([\[\]\s,\|])' + re.escape(old_name) + r'(?=[\[\]\s,\|])'
                replaced = re.sub(pattern, r'\1' + new_name, padded)
                return replaced[1:-1]

            # 1. Update active macro tab listbox
            macro_tab = app.macro_tab
            macro_steps = list(macro_tab.macro_listbox.get(0, tk.END))
            for idx, step in enumerate(macro_steps):
                new_step = replace_template(step)
                if new_step != step:
                    macro_tab.macro_listbox.delete(idx)
                    macro_tab.macro_listbox.insert(idx, new_step)

            # 2. Update active recovery tab listbox
            recovery_tab = app.recovery_tab
            recovery_steps = list(recovery_tab.recovery_listbox.get(0, tk.END))
            for idx, step in enumerate(recovery_steps):
                new_step = replace_template(step)
                if new_step != step:
                    recovery_tab.recovery_listbox.delete(idx)
                    recovery_tab.recovery_listbox.insert(idx, new_step)

            # 3. Update all saved macro JSON profiles in "macros" folder
            macros_dir = "macros"
            if os.path.exists(macros_dir):
                for filename in os.listdir(macros_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(macros_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            changed = False
                            if "steps" in data and isinstance(data["steps"], list):
                                new_steps = []
                                for step in data["steps"]:
                                    new_step = replace_template(step)
                                    if new_step != step:
                                        changed = True
                                    new_steps.append(new_step)
                                data["steps"] = new_steps
                                
                            if "recovery_steps" in data and isinstance(data["recovery_steps"], list):
                                new_rec_steps = []
                                for step in data["recovery_steps"]:
                                    new_step = replace_template(step)
                                    if new_step != step:
                                        changed = True
                                    new_rec_steps.append(new_step)
                                data["recovery_steps"] = new_rec_steps

                            if changed:
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=4)
                        except Exception as file_err:
                            print(f"Error updating macro file {filename}: {file_err}")

        except Exception as e:
            messagebox.showerror("Error", f"เปลี่ยนชื่อไม่สำเร็จ: {e}")

    def delete_template(self):
        app = self.app
        name = self.template_var.get()
        if not name:
            return

        confirm = messagebox.askyesno(
            "Delete Template",
            f"คุณต้องการลบภาพต้นแบบ '{name}' ใช่หรือไม่?\n(การกระทำนี้ไม่สามารถย้อนกลับได้)",
            parent=app.root
        )
        if not confirm:
            return

        path = os.path.join("templates", name)
        try:
            if os.path.exists(path):
                os.remove(path)

            config_path = os.path.join("templates", "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    config_data.pop(name, None)
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, ensure_ascii=False, indent=4)
                except Exception as ex:
                    logging.error(f"Error updating config during delete: {ex}")

            messagebox.showinfo("Success", f"ลบภาพต้นแบบ '{name}' สำเร็จแล้วครับ!")
            app.refresh_templates()
            files = glob.glob("templates/*.png")
            if files:
                self.template_var.set(os.path.basename(files[0]))
            else:
                self.template_var.set("")

        except Exception as e:
            messagebox.showerror("Error", f"ลบภาพไม่สำเร็จ: {e}")

    def test_find(self):
        app = self.app
        name = self.template_var.get()
        if not name:
            return
        app.status_label.config(text=f"Status: Searching for {name}...", fg="orange")
        app.root.update()
        max_val, pos = app.do_template_match_by_name(name)
        app.status_label.config(text="Status: Connected", fg="green")
        if max_val is None:
            return
        if max_val >= 0.8:
            messagebox.showinfo("เจอภาพ!", f"✅ ความมั่นใจ: {max_val*100:.1f}%\nพิกัด: {pos}")
        else:
            messagebox.showwarning("ไม่เจอภาพ", f"❌ ความมั่นใจต่ำเกินไป ({max_val*100:.1f}%)")

    def find_and_click(self):
        app = self.app
        name = self.template_var.get()
        if not name:
            return
        app.status_label.config(text=f"Status: Searching for {name}...", fg="orange")
        app.root.update()
        max_val, pos = app.do_template_match_by_name(name)
        app.status_label.config(text="Status: Connected", fg="green")
        if max_val is None:
            return
        if max_val >= 0.8:
            app.device.shell(f"input tap {pos[0]} {pos[1]}")
            messagebox.showinfo("คลิกแล้ว!", f"สั่งคลิกพิกัด {pos} สำเร็จ!\n(มั่นใจ {max_val*100:.1f}%)")
        else:
            messagebox.showwarning("ไม่คลิก", f"ความมั่นใจแค่ {max_val*100:.1f}%")
