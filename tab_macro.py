"""
tab_macro.py
UI and logic for the Macro Builder tab (Tab 2).
Handles: step list, add/edit/delete/reorder, drag-and-drop, start/stop macro.
"""

import tkinter as tk
from tkinter import simpledialog
from tkinter import ttk

# Special action entries in the combo that do NOT need an Action dropdown
SPECIAL_ACTIONS = [
    "-- เพิ่มเวลาหน่วง (Delay) --",
    "-- แก้ไขมินิเกม (Solve Minigame) --",
    "-- วนลูป (Loop) --",
    "-- ปิดแอปเกม (Force Stop) --",
    "-- เปิดแอปเกม (Launch Game) --",
    "-- หยุดมาโคร (Break) --",
    "-- พิมพ์ข้อความ (Type Text) --",
    "-- กด Enter --",
    "-- ลากหน้าจอ (Swipe) --",
]


class MacroTab:
    """Manages the 🚀 Macro Builder tab."""

    def __init__(self, parent_frame, app):
        self.app = app
        self._drag_start_index = 0
        self._build_ui(parent_frame)

    def _build_ui(self, frame):
        # --- Add Step Row ---
        f_add = tk.Frame(frame)
        f_add.pack(fill="x", padx=10, pady=10)
        tk.Label(f_add, text="เลือกปุ่มที่เซฟไว้:").pack(side=tk.LEFT)

        self.macro_template_var = tk.StringVar()
        self.macro_combo = ttk.Combobox(f_add, textvariable=self.macro_template_var, state="readonly", width=20)
        self.macro_combo.pack(side=tk.LEFT, padx=5)
        self.macro_combo.bind("<<ComboboxSelected>>", self.on_combo_selected)

        # Action sub-frame (hidden for special actions)
        self.action_frame = tk.Frame(f_add)
        self.action_frame.pack(side=tk.LEFT)

        tk.Label(self.action_frame, text="Action:").pack(side=tk.LEFT, padx=(5, 0))
        self.macro_action_var = tk.StringVar(value="[Click]")
        self.macro_action_combo = ttk.Combobox(
            self.action_frame, textvariable=self.macro_action_var, state="readonly", width=12
        )
        self.macro_action_combo['values'] = [
            "[Click]", "[Wait]", "[Spam-Wait]", "[Spam-Click]", 
            "[Full-Click]", "[Skip-If]", "[Skip-IfNot]", "[Full-Skip-If]", "[Full-Skip-IfNot]"
        ]
        self.macro_action_combo.pack(side=tk.LEFT, padx=5)

        self.add_step_btn = tk.Button(f_add, text="เพิ่มสเต็ป", command=self.add_step, bg="#E0E0E0")
        self.add_step_btn.pack(side=tk.LEFT, padx=5)

        # --- Delay Settings Row ---
        f_delay = tk.Frame(frame)
        f_delay.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(f_delay, text="ดีเลย์แคปภาพ (ms):").pack(side=tk.LEFT)
        self.screencap_delay_var = tk.StringVar(value="1000")
        self.screencap_delay_entry = tk.Entry(f_delay, textvariable=self.screencap_delay_var, width=8)
        self.screencap_delay_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(f_delay, text="ดีเลย์เปลี่ยนสเต็ป (ms):").pack(side=tk.LEFT, padx=(15, 0))
        self.post_step_delay_var = tk.StringVar(value="1000")
        self.post_step_delay_entry = tk.Entry(f_delay, textvariable=self.post_step_delay_var, width=8)
        self.post_step_delay_entry.pack(side=tk.LEFT, padx=5)

        # --- Listbox ---
        tk.Label(frame, text="ลำดับการกดของบอท (จะรอจนกว่าจะเจอภาพ ถึงจะกด):").pack(anchor=tk.W, padx=10)
        self.macro_listbox = tk.Listbox(frame, height=8, font=("Helvetica", 10))
        self.macro_listbox.pack(fill="both", expand=True, padx=10, pady=2)
        self.macro_listbox.bind('<Button-1>', self._on_drag_start)
        self.macro_listbox.bind('<B1-Motion>', self._on_drag_motion)

        # --- List Controls ---
        f_ctrl = tk.Frame(frame)
        f_ctrl.pack(fill="x", padx=10, pady=2)
        tk.Button(f_ctrl, text="⬆️", command=self.move_up).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="⬇️", command=self.move_down).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="✏️ แก้ไข", command=self.edit_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="🗑️ ลบ", command=self.remove_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="ล้างทั้งหมด", command=lambda: self.macro_listbox.delete(0, tk.END)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="💾 Save", command=self.app.save_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)
        tk.Button(f_ctrl, text="📂 Load", command=self.app.load_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)

        # --- Start / Stop ---
        f_run = tk.Frame(frame)
        f_run.pack(pady=10)
        self.start_macro_btn = tk.Button(
            f_run, text="▶ START MACRO", command=self.app.start_macro,
            bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"), width=15, state=tk.DISABLED
        )
        self.start_macro_btn.grid(row=0, column=0, padx=5)
        self.stop_macro_btn = tk.Button(
            f_run, text="⏹ STOP MACRO", command=self.app.stop_macro,
            bg="#F44336", fg="white", font=("Helvetica", 12, "bold"), width=15, state=tk.DISABLED
        )
        self.stop_macro_btn.grid(row=0, column=1, padx=5)

    # ------------------------------------------------------------------
    # Combo selection
    # ------------------------------------------------------------------

    def on_combo_selected(self, event=None):
        val = self.macro_template_var.get()
        if val in SPECIAL_ACTIONS:
            self.action_frame.pack_forget()
        else:
            self.action_frame.pack(side=tk.LEFT)
            self.add_step_btn.pack_forget()
            self.add_step_btn.pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------
    # Step management
    # ------------------------------------------------------------------

    def add_step(self):
        app = self.app
        val = self.macro_template_var.get()
        act = self.macro_action_var.get()

        if act == "[Loop-Multi]":
            multi_info = app.ask_multi_loop_details()
            if not multi_info:
                return
            templates, delay_ms = multi_info
            self.macro_listbox.insert(tk.END, f"[Loop-Multi:{delay_ms}] {','.join(templates)}")
            return

        if val == "-- เพิ่มเวลาหน่วง (Delay) --":
            delay_ms = simpledialog.askinteger(
                "Delay Time", "ใส่เวลาที่ต้องการหน่วง\n(หน่วยเป็นมิลลิวินาที เช่น 1000 = 1 วินาที):",
                parent=app.root, minvalue=1, maxvalue=600000
            )
            if delay_ms:
                self.macro_listbox.insert(tk.END, f"[Delay] {delay_ms}ms")
            return

        if val == "-- แก้ไขมินิเกม (Solve Minigame) --":
            detect_img = simpledialog.askstring(
                "Detect Template", "ใส่ชื่อรูปภาพที่ใช้ตรวจจับมินิเกม (เช่น Bot check.png):",
                initialvalue="Bot check.png", parent=app.root
            )
            if detect_img:
                if not detect_img.endswith(".png"):
                    detect_img += ".png"
                self.macro_listbox.insert(tk.END, f"[Solve-Minigame] {detect_img}")
            return

        if val == "-- วนลูป (Loop) --":
            loop_info = app.ask_loop_control_details()
            if loop_info:
                steps_count, loop_mode, loop_val = loop_info
                if loop_mode == 'duration':
                    self.macro_listbox.insert(tk.END, f"[Loop-Control:{steps_count}] Duration:{loop_val}ms")
                else:
                    self.macro_listbox.insert(tk.END, f"[Loop-Control:{steps_count}] Count:{loop_val}")
            return

        if val == "-- ปิดแอปเกม (Force Stop) --":
            self.macro_listbox.insert(tk.END, "[Force-Stop-Game]")
            return

        if val == "-- เปิดแอปเกม (Launch Game) --":
            self.macro_listbox.insert(tk.END, "[Launch-Game]")
            return


        if val == "-- หยุดมาโคร (Break) --":
            self.macro_listbox.insert(tk.END, "[Break]")
            return

        if val == "-- พิมพ์ข้อความ (Type Text) --":
            text_val = app.ask_type_text_details()
            if text_val is not None:
                self.macro_listbox.insert(tk.END, f"[Type-Text] {text_val.replace(' ', '%s')}")
            return

        if val == "-- กด Enter --":
            self.macro_listbox.insert(tk.END, "[Press-Enter]")
            return

        if val == "-- ลากหน้าจอ (Swipe) --":
            swipe_res = app.ask_swipe_details()
            if swipe_res:
                stype, sinfo = swipe_res
                if stype == 'coord':
                    start_xy, end_xy, dur_ms = sinfo
                    self.macro_listbox.insert(tk.END, f"[Swipe] {start_xy} -> {end_xy} {dur_ms}ms")
                else:
                    img_name, sdir, dur_ms = sinfo
                    self.macro_listbox.insert(tk.END, f"[Swipe-Img] {img_name} Direction:{sdir} {dur_ms}ms")
            return

        if not val:
            return

        if act in ["[Spam-Wait]", "[Spam-Click]"]:
            spam_info = app.ask_spam_wait_details()
            if not spam_info or not spam_info[0]:
                return
            spam_img, spam_delay, rand_delay, wait_targets = spam_info
            if not spam_img.endswith(".png") and "," not in spam_img:
                spam_img += ".png"
            self.macro_listbox.insert(tk.END, f"{act} [{spam_img}] [S:{spam_delay}] [R:{rand_delay}] {'|'.join(wait_targets)}")

        elif act == "[Skip-If]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าเจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.macro_listbox.insert(tk.END, f"[Skip:{skip_count}] {val}")

        elif act == "[Skip-IfNot]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าไม่เจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.macro_listbox.insert(tk.END, f"[SkipNot:{skip_count}] {val}")

        elif act == "[Full-Skip-If]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าเจอภาพนี้ (สแกนทั้งหน้าจอ) ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.macro_listbox.insert(tk.END, f"[FullSkip:{skip_count}] {val}")

        elif act == "[Full-Skip-IfNot]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าไม่เจอภาพนี้ (สแกนทั้งหน้าจอ) ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.macro_listbox.insert(tk.END, f"[FullSkipNot:{skip_count}] {val}")

        elif act == "[Loop]":
            loop_ms = simpledialog.askinteger(
                "Loop Interval",
                "ใส่เวลาหน่วงระหว่างคลิกวนลูป (มิลลิวินาที):\n(เช่น 500 = คลิกปุ่มเดิมซ้ำทุกๆ 0.5 วินาทีจนกว่าจะหายไป)",
                parent=app.root, minvalue=50, maxvalue=10000, initialvalue=500
            )
            if loop_ms:
                self.macro_listbox.insert(tk.END, f"[Loop:{loop_ms}] {val}")

        else:  # [Click], [Wait]
            if act == "[Wait]":
                selected_templates = app.ask_multi_templates(initial_template=val)
                if selected_templates:
                    self.macro_listbox.insert(tk.END, f"{act} {'|'.join(selected_templates)}")
            else:
                self.macro_listbox.insert(tk.END, f"{act} {val}")

    def remove_step(self):
        sel = self.macro_listbox.curselection()
        if sel:
            self.macro_listbox.delete(sel[0])

    def move_up(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i == 0:
            return
        val = self.macro_listbox.get(i)
        self.macro_listbox.delete(i)
        self.macro_listbox.insert(i - 1, val)
        self.macro_listbox.selection_set(i - 1)

    def move_down(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i == self.macro_listbox.size() - 1:
            return
        val = self.macro_listbox.get(i)
        self.macro_listbox.delete(i)
        self.macro_listbox.insert(i + 1, val)
        self.macro_listbox.selection_set(i + 1)

    def edit_step(self):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        old_val = self.macro_listbox.get(i)
        new_val = simpledialog.askstring("Edit Step", "แก้ไขคำสั่ง:", initialvalue=old_val, parent=self.app.root)
        if new_val and new_val != old_val:
            self.macro_listbox.delete(i)
            self.macro_listbox.insert(i, new_val)
            self.macro_listbox.selection_set(i)

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def _on_drag_start(self, event):
        self._drag_start_index = self.macro_listbox.nearest(event.y)

    def _on_drag_motion(self, event):
        i = self.macro_listbox.nearest(event.y)
        if i < 0 or i >= self.macro_listbox.size():
            return
        if i != self._drag_start_index:
            val = self.macro_listbox.get(self._drag_start_index)
            self.macro_listbox.delete(self._drag_start_index)
            self.macro_listbox.insert(i, val)
            self._drag_start_index = i
