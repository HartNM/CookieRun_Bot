import os
import sys
import subprocess
import urllib.request
import zipfile
import logging

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def ensure_adb_server():
    """ Ensures ADB is running, downloading it if necessary """
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

def parse_package_from_string(text):
    if not text: return None
    import re
    match = re.search(r'([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)', text)
    if match:
        return match.group(1)
    return None
