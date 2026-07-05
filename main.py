"""
main.py
Entry point and top-level controller for CookieRun Bot.

Module responsibilities:
  - CookieRunBotUI: builds the window, notebook, and wires sub-modules together.
  - Delegates tab logic to tab_templates / tab_macro / tab_recovery.
  - Delegates ADB connection to adb_connect.
  - Delegates macro execution to macro_engine.
  - Delegates dialogs to ui_dialogs.
  - Delegates config I/O to config_manager.
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import os
import sys
import subprocess
import threading
import logging
import traceback

# ── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    filename='bot_error.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def global_exception_handler(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error("Unhandled exception: \n" + error_msg)
    try:
        messagebox.showerror(
            "Critical Error",
            f"เกิดข้อผิดพลาดที่ไม่ได้คาดคิด (Crash)\n\n"
            f"ระบบได้บันทึกข้อผิดพลาดไว้ในไฟล์ bot_error.log แล้ว\n\n"
            f"สาเหตุเบื้องต้น:\n{exc_value}"
        )
    except Exception:
        pass
    sys.exit(1)


sys.excepthook = global_exception_handler

# ── Sub-module imports ──────────────────────────────────────────────────────
from tab_templates import TemplatesTab
from tab_macro import MacroTab, SPECIAL_ACTIONS
from tab_recovery import RecoveryTab
from adb_connect import connect_adb
from macro_engine import macro_worker, log_bot_activity
from vision import do_template_match_by_name as vision_match
from vision import solve_minigame_action as vision_solve


class CookieRunBotUI:
    """Top-level application controller."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CookieRun Bot - Macro Builder")
        self.root.geometry("500x650")

        self.device = None
        self.macro_running = False
        self.test_restart_running = False
        self.spam_running = False
        os.makedirs("templates", exist_ok=True)

        self._build_top_bar()
        self._build_notebook()

    # ── Top bar ────────────────────────────────────────────────────────────

    def _build_top_bar(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(top_frame, text="CookieRun ADB Bot & Macro",
                 font=("Helvetica", 14, "bold")).pack(pady=5)

        self.status_label = tk.Label(top_frame, text="Status: Disconnected",
                                     fg="red", font=("Helvetica", 10, "bold"))
        self.status_label.pack()

        self.connect_btn = tk.Button(
            top_frame, text="1. Connect to MuMu Player",
            command=self.connect_adb, bg="#FFC107", font=("Helvetica", 10, "bold")
        )
        self.connect_btn.pack(fill="x", pady=5)

        self.restart_btn = tk.Button(
            top_frame, text="🔄 Restart App (รีสตาร์ทโปรแกรม)",
            command=self.restart_app, bg="#E0E0E0"
        )
        self.restart_btn.pack(fill="x", pady=(0, 5))

    # ── Notebook ───────────────────────────────────────────────────────────

    def _build_notebook(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both", padx=10, pady=5)

        tab_frame_templates = tk.Frame(notebook)
        notebook.add(tab_frame_templates, text="🛠️ จัดการภาพต้นแบบ (Templates)")

        tab_frame_macro = tk.Frame(notebook)
        notebook.add(tab_frame_macro, text="🚀 สร้างบอทมาโคร (Macro)")

        tab_frame_recovery = tk.Frame(notebook)
        notebook.add(tab_frame_recovery, text="🔄 กู้คืนเกม (Recovery)")

        self.templates_tab = TemplatesTab(tab_frame_templates, self)
        self.macro_tab = MacroTab(tab_frame_macro, self)
        self.recovery_tab = RecoveryTab(tab_frame_recovery, self)

    # ── Delegates ──────────────────────────────────────────────────────────

    def connect_adb(self):
        connect_adb(self)

    def restart_app(self):
        self.macro_running = False
        self.root.destroy()
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)

    def refresh_templates(self):
        """Reload templates from disk and update all combos."""
        names = self.templates_tab.refresh_templates()

        macro_opts = SPECIAL_ACTIONS + names
        self.macro_tab.macro_combo['values'] = macro_opts
        self.recovery_tab.recovery_combo['values'] = macro_opts

        if macro_opts:
            self.macro_tab.macro_combo.current(0)
            self.macro_tab.on_combo_selected()
            self.recovery_tab.recovery_combo.current(0)
            self.recovery_tab._on_combo_selected()

    # ── Dialog delegates ───────────────────────────────────────────────────

    def ask_spam_wait_details(self):
        from ui_dialogs import ask_spam_wait_details as dlg
        templates = [f for f in self.macro_tab.macro_combo['values'] if not f.startswith("-- ")]
        return dlg(self.root, templates)

    def ask_multi_loop_details(self):
        from ui_dialogs import ask_multi_loop_details as dlg
        return dlg(self.root)

    def ask_loop_control_details(self):
        from ui_dialogs import ask_loop_control_details as dlg
        return dlg(self.root)

    def ask_type_text_details(self):
        from ui_dialogs import ask_type_text_details as dlg
        return dlg(self.root)

    def ask_multi_templates(self, initial_template=None):
        from ui_dialogs import ask_multi_templates as dlg
        templates = [f for f in self.macro_tab.macro_combo['values'] if not f.startswith("-- ")]
        return dlg(self.root, templates, initial_template)

    def ask_swipe_details(self):
        from ui_dialogs import ask_swipe_details as dlg
        templates = [f for f in self.macro_tab.macro_combo['values'] if not f.startswith("-- ")]
        return dlg(self.root, templates)

    # ── Config delegates ───────────────────────────────────────────────────

    def save_macro(self):
        from config_manager import save_macro as cfg_save
        cfg_save(
            self.macro_tab.macro_listbox,
            self.recovery_tab.recovery_listbox,
            self.recovery_tab.timeout_var,
            self.recovery_tab.package_var,
            self.macro_tab.screencap_delay_var,
            self.macro_tab.post_step_delay_var,
        )

    def load_macro(self):
        from config_manager import load_macro as cfg_load
        cfg_load(
            self.macro_tab.macro_listbox,
            self.recovery_tab.recovery_listbox,
            self.recovery_tab.timeout_var,
            self.recovery_tab.package_var,
            self.macro_tab.screencap_delay_var,
            self.macro_tab.post_step_delay_var,
        )

    # ── Vision delegates ───────────────────────────────────────────────────

    def do_template_match_by_name(self, template_name: str, ignore_roi=False):
        return vision_match(self.device, template_name, ignore_roi)



    def solve_minigame_action(self, detect_img: str = "Bot check.png") -> bool:
        def is_running():
            return self.macro_running or self.test_restart_running

        def set_status(msg, color):
            self.root.after(0, lambda: self.status_label.config(text=msg, fg=color))

        return vision_solve(self.device, is_running, set_status, detect_img)

    # ── Macro engine ───────────────────────────────────────────────────────

    def start_macro(self):
        steps = self.macro_tab.macro_listbox.get(0, tk.END)
        if not steps:
            messagebox.showwarning("เตือน", "กรุณาเพิ่มสเต็ปลงใน Macro ก่อนครับ")
            return
        self.macro_running = True
        self.macro_tab.start_macro_btn.config(state=tk.DISABLED)
        self.macro_tab.stop_macro_btn.config(state=tk.NORMAL)
        self.templates_tab.create_template_btn.config(state=tk.DISABLED)
        threading.Thread(target=macro_worker, args=(self, steps), daemon=True).start()

    def stop_macro(self):
        self.macro_running = False
        self.test_restart_running = False
        self.status_label.config(text="Status: Stopping...", fg="red")


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = CookieRunBotUI(root)
    root.mainloop()
