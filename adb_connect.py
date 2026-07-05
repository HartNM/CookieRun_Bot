"""
adb_connect.py
ADB connection logic — scans ports, connects to device, handles UI updates.
"""

import socket
import logging
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import messagebox
from ppadb.client import Client as AdbClient

from utils import ensure_adb_server


def connect_adb(app) -> None:
    """
    Initiate ADB connection in a background thread.
    :param app: CookieRunBotUI instance.
    """
    app.connect_btn.config(state=tk.DISABLED)
    app.status_label.config(text="Status: Starting ADB...", fg="orange")

    def _do_connect():
        try:
            ensure_adb_server()
            client = AdbClient(host="127.0.0.1", port=5037)

            # Build list of ports to probe
            mumu12_ports = [16384 + i * 32 for i in range(16)]
            ports_to_try = (
                list(range(7555, 7600, 2)) +           # MuMu Player 6 / NoxPlayer
                list(range(5554, 5600, 2)) +            # LDPlayer / stock emulator
                mumu12_ports +                          # MuMu Player 12 (instance 0-15)
                list(range(21503, 21600, 10)) +         # BlueStacks 5
                [62001, 62025, 62026, 62027, 62028] +   # NoxPlayer
                list(range(6555, 6600, 2))              # MEmu / other
            )

            def _try_connect(port):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                        pass
                    return port
                except Exception:
                    return None

            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = {executor.submit(_try_connect, p): p for p in ports_to_try}
                for future in as_completed(futures):
                    port = future.result()
                    if port is not None:
                        try:
                            client.remote_connect("127.0.0.1", port)
                        except Exception:
                            pass

            devices = client.devices()

            if len(devices) == 0:
                def _no_device():
                    app.connect_btn.config(state=tk.NORMAL)
                    app.status_label.config(text="Status: No device found", fg="red")
                    messagebox.showwarning("ไม่พบอุปกรณ์",
                                           "ไม่พบอุปกรณ์ ADB ที่เชื่อมต่ออยู่\nกรุณาเปิด Emulator แล้วลองใหม่")
                app.root.after(0, _no_device)
                return

            if len(devices) == 1:
                app.root.after(0, lambda: _finish(devices[0]))
            else:
                def _ask():
                    from ui_dialogs import ask_select_device
                    idx = ask_select_device(app.root, devices)
                    if idx is None:
                        app.connect_btn.config(state=tk.NORMAL)
                        app.status_label.config(text="Status: Cancelled", fg="gray")
                        return
                    _finish(devices[idx])
                app.root.after(0, _ask)

        except Exception as e:
            logging.error(traceback.format_exc())
            def _err(err=e):
                app.connect_btn.config(state=tk.NORMAL)
                app.status_label.config(text="Status: Connection Error", fg="red")
                messagebox.showerror("Error", f"เชื่อมต่อไม่สำเร็จ:\n{err}")
            app.root.after(0, _err)

    def _finish(chosen):
        try:
            app.device = chosen
            serial = app.device.serial

            try:
                wm_size = app.device.shell("wm size")
                if "1920x1080" not in wm_size and "1080x1920" not in wm_size:
                    messagebox.showwarning("เตือนขนาดจอ",
                                           "ความละเอียดไม่ใช่ 1080p (1920x1080)\nกรุณาตั้งค่า Emulator เป็น 1080p")
            except Exception:
                pass

            app.status_label.config(text=f"Status: Connected ({serial})", fg="green")
            app.connect_btn.config(state=tk.NORMAL)

            # Enable buttons in each tab
            app.templates_tab.enable_buttons()
            app.macro_tab.start_macro_btn.config(state=tk.NORMAL)
            app.recovery_tab.enable_buttons()

            app.refresh_templates()

        except Exception as e:
            logging.error(traceback.format_exc())
            app.connect_btn.config(state=tk.NORMAL)
            app.status_label.config(text="Status: Connection Error", fg="red")
            messagebox.showerror("Error", f"เชื่อมต่อไม่สำเร็จ:\n{e}")

    threading.Thread(target=_do_connect, daemon=True).start()
