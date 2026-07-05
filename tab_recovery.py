"""
tab_recovery.py
UI and logic for the Recovery tab (Tab 3).
Handles: anti-stuck settings, recovery step list, test restart.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk
import threading
import logging

from tab_macro import SPECIAL_ACTIONS


class RecoveryTab:
    """Manages the 🔄 Recovery tab."""

    def __init__(self, parent_frame, app):
        self.app = app
        self._drag_start_index_rec = 0
        self._build_ui(parent_frame)

    def _build_ui(self, frame):
        # --- Anti-Stuck Settings ---
        f_stuck = tk.LabelFrame(frame, text="🛡️ ระบบกันค้าง (Anti-Stuck Settings)")
        f_stuck.pack(fill="x", padx=10, pady=5)

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

        self.detect_pkg_btn = tk.Button(r1, text="🔍 ดึงจากจอ", command=self._detect_current_package,
                                        bg="#E3F2FD", state=tk.DISABLED)
        self.detect_pkg_btn.pack(side=tk.LEFT, padx=5)

        r3 = tk.Frame(f_stuck)
        r3.pack(fill="x", padx=5, pady=2)
        self.restart_test_btn = tk.Button(r3, text="🔄 ทดสอบรีสตาร์ทเกม & เริ่มใหม่",
                                          command=self._test_restart_game,
                                          bg="#EFEBE9", fg="#4E342E", state=tk.DISABLED)
        self.restart_test_btn.pack(side=tk.LEFT, padx=5)

        # --- Recovery Step Builder ---
        f_add = tk.Frame(frame)
        f_add.pack(fill="x", padx=10, pady=10)
        tk.Label(f_add, text="เลือกปุ่มที่เซฟไว้:").pack(side=tk.LEFT)

        self.recovery_template_var = tk.StringVar()
        self.recovery_combo = ttk.Combobox(f_add, textvariable=self.recovery_template_var, state="readonly", width=20)
        self.recovery_combo.pack(side=tk.LEFT, padx=5)
        self.recovery_combo.bind("<<ComboboxSelected>>", self._on_combo_selected)

        self.rec_action_frame = tk.Frame(f_add)
        self.rec_action_frame.pack(side=tk.LEFT)

        tk.Label(self.rec_action_frame, text="Action:").pack(side=tk.LEFT, padx=(5, 0))
        self.recovery_action_var = tk.StringVar(value="[Click]")
        self.recovery_action_combo = ttk.Combobox(
            self.rec_action_frame, textvariable=self.recovery_action_var, state="readonly", width=12
        )
        self.recovery_action_combo['values'] = [
            "[Click]", "[Wait]", "[Spam-Wait]", "[Spam-Click]", 
            "[Full-Click]", "[Skip-If]", "[Skip-IfNot]", "[Full-Skip-If]", "[Full-Skip-IfNot]"
        ]
        self.recovery_action_combo.pack(side=tk.LEFT, padx=5)

        self.rec_add_step_btn = tk.Button(f_add, text="เพิ่มสเต็ป", command=self._add_step, bg="#E0E0E0")
        self.rec_add_step_btn.pack(side=tk.LEFT, padx=5)

        # --- Listbox ---
        tk.Label(frame, text="ลำดับคำสั่งที่จะทำเมื่อระบบค้าง/กู้คืนเกม (Restart Macro):").pack(anchor=tk.W, padx=10)
        self.recovery_listbox = tk.Listbox(frame, height=8, font=("Helvetica", 10))
        self.recovery_listbox.pack(fill="both", expand=True, padx=10, pady=2)
        self.recovery_listbox.bind('<Button-1>', self._on_drag_start)
        self.recovery_listbox.bind('<B1-Motion>', self._on_drag_motion)

        f_ctrl = tk.Frame(frame)
        f_ctrl.pack(fill="x", padx=10, pady=2)
        tk.Button(f_ctrl, text="⬆️", command=self._move_up).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="⬇️", command=self._move_down).pack(side=tk.LEFT, padx=1)
        tk.Button(f_ctrl, text="✏️ แก้ไข", command=self._edit_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="🗑️ ลบ", command=self._remove_step).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="ล้างทั้งหมด",
                  command=lambda: self.recovery_listbox.delete(0, tk.END)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_ctrl, text="💾 Save", command=self.app.save_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)
        tk.Button(f_ctrl, text="📂 Load", command=self.app.load_macro, bg="#E3F2FD").pack(side=tk.RIGHT, padx=2)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def enable_buttons(self):
        self.detect_pkg_btn.config(state=tk.NORMAL)
        self.restart_test_btn.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Combo
    # ------------------------------------------------------------------

    def _on_combo_selected(self, event=None):
        val = self.recovery_template_var.get()
        if val in SPECIAL_ACTIONS:
            self.rec_action_frame.pack_forget()
        else:
            self.rec_action_frame.pack(side=tk.LEFT)
            self.rec_add_step_btn.pack_forget()
            self.rec_add_step_btn.pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------
    # Step management (mirrors MacroTab.add_step for recovery list)
    # ------------------------------------------------------------------

    def _add_step(self):
        app = self.app
        val = self.recovery_template_var.get()
        act = self.recovery_action_var.get()

        if act == "[Loop-Multi]":
            multi_info = app.ask_multi_loop_details()
            if not multi_info:
                return
            templates, delay_ms = multi_info
            self.recovery_listbox.insert(tk.END, f"[Loop-Multi:{delay_ms}] {','.join(templates)}")
            return

        if val == "-- เพิ่มเวลาหน่วง (Delay) --":
            delay_ms = simpledialog.askinteger(
                "Delay Time", "ใส่เวลาที่ต้องการหน่วง\n(หน่วยเป็นมิลลิวินาที เช่น 1000 = 1 วินาที):",
                parent=app.root, minvalue=1, maxvalue=600000
            )
            if delay_ms:
                self.recovery_listbox.insert(tk.END, f"[Delay] {delay_ms}ms")
            return

        if val == "-- แก้ไขมินิเกม (Solve Minigame) --":
            detect_img = simpledialog.askstring(
                "Detect Template", "ใส่ชื่อรูปภาพที่ใช้ตรวจจับมินิเกม (เช่น Bot check.png):",
                initialvalue="Bot check.png", parent=app.root
            )
            if detect_img:
                if not detect_img.endswith(".png"):
                    detect_img += ".png"
                self.recovery_listbox.insert(tk.END, f"[Solve-Minigame] {detect_img}")
            return

        if val == "-- วนลูป (Loop) --":
            loop_info = app.ask_loop_control_details()
            if loop_info:
                steps_count, loop_mode, loop_val = loop_info
                if loop_mode == 'duration':
                    self.recovery_listbox.insert(tk.END, f"[Loop-Control:{steps_count}] Duration:{loop_val}ms")
                else:
                    self.recovery_listbox.insert(tk.END, f"[Loop-Control:{steps_count}] Count:{loop_val}")
            return

        if val == "-- ปิดแอปเกม (Force Stop) --":
            self.recovery_listbox.insert(tk.END, "[Force-Stop-Game]")
            return

        if val == "-- เปิดแอปเกม (Launch Game) --":
            self.recovery_listbox.insert(tk.END, "[Launch-Game]")
            return



        if val == "-- หยุดมาโคร (Break) --":
            self.recovery_listbox.insert(tk.END, "[Break]")
            return

        if val == "-- พิมพ์ข้อความ (Type Text) --":
            text_val = app.ask_type_text_details()
            if text_val is not None:
                self.recovery_listbox.insert(tk.END, f"[Type-Text] {text_val.replace(' ', '%s')}")
            return

        if val == "-- กด Enter --":
            self.recovery_listbox.insert(tk.END, "[Press-Enter]")
            return

        if val == "-- ลากหน้าจอ (Swipe) --":
            swipe_res = app.ask_swipe_details()
            if swipe_res:
                stype, sinfo = swipe_res
                if stype == 'coord':
                    start_xy, end_xy, dur_ms = sinfo
                    self.recovery_listbox.insert(tk.END, f"[Swipe] {start_xy} -> {end_xy} {dur_ms}ms")
                else:
                    img_name, sdir, dur_ms = sinfo
                    self.recovery_listbox.insert(tk.END, f"[Swipe-Img] {img_name} Direction:{sdir} {dur_ms}ms")
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
            self.recovery_listbox.insert(
                tk.END, f"{act} [{spam_img}] [S:{spam_delay}] [R:{rand_delay}] {'|'.join(wait_targets)}"
            )
        elif act == "[Skip-If]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าเจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.recovery_listbox.insert(tk.END, f"[Skip:{skip_count}] {val}")
        elif act == "[Skip-IfNot]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าไม่เจอภาพนี้ ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.recovery_listbox.insert(tk.END, f"[SkipNot:{skip_count}] {val}")
        elif act == "[Full-Skip-If]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าเจอภาพนี้ (สแกนทั้งหน้าจอ) ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.recovery_listbox.insert(tk.END, f"[FullSkip:{skip_count}] {val}")
        elif act == "[Full-Skip-IfNot]":
            skip_count = simpledialog.askinteger(
                "Skip Count", "ถ้าไม่เจอภาพนี้ (สแกนทั้งหน้าจอ) ต้องการให้ข้ามไปกี่สเต็ป?\n(เช่น ใส่ 2 เพื่อข้าม 2 คำสั่งถัดไป)",
                parent=app.root, minvalue=1, maxvalue=50
            )
            if skip_count:
                self.recovery_listbox.insert(tk.END, f"[FullSkipNot:{skip_count}] {val}")
        else:
            if act == "[Wait]":
                selected_templates = app.ask_multi_templates(initial_template=val)
                if selected_templates:
                    self.recovery_listbox.insert(tk.END, f"{act} {'|'.join(selected_templates)}")
            else:
                self.recovery_listbox.insert(tk.END, f"{act} {val}")

    def _remove_step(self):
        sel = self.recovery_listbox.curselection()
        if sel:
            self.recovery_listbox.delete(sel[0])

    def _move_up(self):
        sel = self.recovery_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i == 0:
            return
        val = self.recovery_listbox.get(i)
        self.recovery_listbox.delete(i)
        self.recovery_listbox.insert(i - 1, val)
        self.recovery_listbox.selection_set(i - 1)

    def _move_down(self):
        sel = self.recovery_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        if i == self.recovery_listbox.size() - 1:
            return
        val = self.recovery_listbox.get(i)
        self.recovery_listbox.delete(i)
        self.recovery_listbox.insert(i + 1, val)
        self.recovery_listbox.selection_set(i + 1)

    def _edit_step(self):
        sel = self.recovery_listbox.curselection()
        if not sel:
            return
        i = sel[0]
        old_val = self.recovery_listbox.get(i)
        new_val = simpledialog.askstring("Edit Step", "แก้ไขคำสั่ง (กู้คืน):", initialvalue=old_val, parent=self.app.root)
        if new_val and new_val != old_val:
            self.recovery_listbox.delete(i)
            self.recovery_listbox.insert(i, new_val)
            self.recovery_listbox.selection_set(i)

    # ------------------------------------------------------------------
    # Drag and drop
    # ------------------------------------------------------------------

    def _on_drag_start(self, event):
        self._drag_start_index_rec = self.recovery_listbox.nearest(event.y)

    def _on_drag_motion(self, event):
        i = self.recovery_listbox.nearest(event.y)
        if i < 0 or i >= self.recovery_listbox.size():
            return
        if i != self._drag_start_index_rec:
            val = self.recovery_listbox.get(self._drag_start_index_rec)
            self.recovery_listbox.delete(self._drag_start_index_rec)
            self.recovery_listbox.insert(i, val)
            self._drag_start_index_rec = i

    # ------------------------------------------------------------------
    # Detect package
    # ------------------------------------------------------------------

    def _detect_current_package(self):
        app = self.app
        if not app.device:
            messagebox.showwarning("Warning", "กรุณาเชื่อมต่อกับ MuMu Player ก่อนครับ")
            return
        try:
            from utils import parse_package_from_string
            focus_out = app.device.shell("dumpsys window | grep mCurrentFocus")
            package = parse_package_from_string(focus_out)
            if not package:
                resume_out = app.device.shell("dumpsys activity activities | grep mResumedActivity")
                package = parse_package_from_string(resume_out)
            if package:
                self.package_var.set(package)
                app.status_label.config(text=f"Macro: ดึงชื่อแพ็กเกจ '{package}' สำเร็จ!", fg="green")
                messagebox.showinfo("Success", f"ดึงชื่อแพ็กเกจแอปที่เปิดอยู่สำเร็จ!\n\nชื่อแพ็กเกจ: {package}")
            else:
                messagebox.showwarning("Warning",
                                       "ไม่พบแอปที่เปิดอยู่ หรือตรวจหาไม่พบ\nกรุณาเปิดเกม CookieRun ทิ้งไว้บนหน้าจอมือถือจำลองแล้วลองกดใหม่ครับ")
        except Exception as e:
            messagebox.showerror("Error", f"ดึงชื่อแพ็กเกจล้มเหลว: {e}")

    # ------------------------------------------------------------------
    # Test restart
    # ------------------------------------------------------------------

    def _test_restart_game(self):
        app = self.app
        if not app.device:
            messagebox.showwarning("Warning", "กรุณาเชื่อมต่อกับ MuMu Player ก่อนทดสอบครับ")
            return

        package_name = self.package_var.get().strip()
        if not package_name:
            messagebox.showwarning("Warning", "กรุณากรอกชื่อแพ็กเกจของเกมก่อนครับ")
            return

        if app.macro_running:
            messagebox.showwarning("Warning", "ไม่สามารถรันการทดสอบนี้ขณะมาโครกำลังทำงานอยู่ได้ครับ")
            return

        confirm = messagebox.askyesno(
            "ยืนยัน",
            "ระบบจะทำการปิดเกม, เปิดใหม่ และทดสอบการกู้คืน (เช็คมินิเกม/สแปมข้ามป๊อปอัปเข้าล็อบบี้)\n\nคุณต้องการเริ่มการทดสอบหรือไม่?"
        )
        if not confirm:
            return

        app.test_restart_running = True
        t = threading.Thread(target=self._run_test_restart_thread, args=(package_name,), daemon=True)
        t.start()

    def _run_test_restart_thread(self, package_name):
        app = self.app
        macro_tab = app.macro_tab

        app.root.after(0, lambda: macro_tab.start_macro_btn.config(state=tk.DISABLED))
        app.root.after(0, lambda: self.restart_test_btn.config(state=tk.DISABLED))
        app.root.after(0, lambda: macro_tab.stop_macro_btn.config(state=tk.NORMAL))

        try:
            from macro_engine import run_recovery_sequence
            success = run_recovery_sequence(app, package_name, loop_count=1, is_test=True)

            if app.test_restart_running:
                if not success:
                    app.root.after(0, lambda: app.status_label.config(
                        text="ทดสอบกู้คืน: ล้มเหลว! ไม่พบหน้าล็อบบี้", fg="red"
                    ))
                    app.root.after(0, lambda: messagebox.showwarning("Warning", "ทดสอบกู้คืนล้มเหลว: ค้นหาหน้าล็อบบี้ไม่พบ"))
                else:
                    app.root.after(0, lambda: messagebox.showinfo("Success", "ทดสอบการรีสตาร์ทเกม & กู้คืนสำเร็จ!"))
        except Exception as e:
            logging.error(f"Test recovery thread error: {e}")
            app.root.after(0, lambda err=e: messagebox.showerror("Error", f"การทดสอบล้มเหลว: {err}"))
        finally:
            app.root.after(0, lambda: macro_tab.start_macro_btn.config(state=tk.NORMAL))
            app.root.after(0, lambda: self.restart_test_btn.config(state=tk.NORMAL))
            app.root.after(0, lambda: macro_tab.stop_macro_btn.config(state=tk.DISABLED))
            app.root.after(0, lambda: app.status_label.config(text="Status: Connected", fg="green"))
            app.test_restart_running = False
