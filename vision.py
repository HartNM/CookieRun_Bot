import cv2
import numpy as np

def match_template(screen_bgr, template_bgr, threshold=0.8):
    """
    Find a template in the screen image using cv2.matchTemplate.
    Returns (True, max_loc, max_val, template_w, template_h) if found,
    else (False, None, max_val, 0, 0)
    """
    if screen_bgr is None or template_bgr is None:
        return False, None, 0, 0, 0
        
    screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
    
    h, w = template_gray.shape
    res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val >= threshold:
        return True, max_loc, max_val, w, h
    return False, None, max_val, 0, 0
import os
import glob
import json
import numpy as np

def do_template_match_by_name(device, template_name, ignore_roi=False):
    if not device: return None, None
    template_path = os.path.join("templates", template_name)
    if not os.path.exists(template_path):
        return None, None
        
    screencap = device.screencap()
    image_array = np.frombuffer(screencap, np.uint8)
    screen_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    template_array = np.fromfile(template_path, np.uint8)
    template_img = cv2.imdecode(template_array, cv2.IMREAD_COLOR)
    
    config_path = os.path.join("templates", "config.json")
    search_roi = None
    if not ignore_roi and os.path.exists(config_path):
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
import time

def solve_minigame_action(device, is_running_callback, set_status_callback, detect_img="Bot check.png"):
    if not device: return False
    
    attempt = 1
    max_attempts = 10
    
    while attempt <= max_attempts and is_running_callback():
        # Check if the minigame is still active
        max_val, _ = do_template_match_by_name(device, detect_img)
        if max_val is None or max_val < 0.8:
            set_status_callback("Macro: มินิเกมหายไปแล้ว (ผ่านสำเร็จ)!", "green")
            return True
            
        set_status_callback(f"Macro: แก้ไขมินิเกม รอบที่ {attempt}...", "orange")
        
        screencap = device.screencap()
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
        device.shell(f"input tap {tap1_x} {tap1_y}")
        time.sleep(1.0)
        device.shell(f"input tap {tap2_x} {tap2_y}")
        
        # Wait for animation/shuffle before checking again
        time.sleep(1.0)
        attempt += 1
        
    return False

