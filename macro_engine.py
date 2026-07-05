"""
macro_engine.py
Core macro execution engine — runs in a background thread.
Handles: macro_worker, run_recovery_sequence, log_bot_activity.
"""

import time
import threading
import os
import json
import logging
import traceback
import tkinter as tk


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def log_bot_activity(message: str) -> None:
    """Write a timestamped message to bot_run.log and stdout."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    print(log_line, end="")
    try:
        with open("bot_run.log", "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        logging.error(f"Failed to write to bot_run.log: {e}")


# ---------------------------------------------------------------------------
# Recovery sequence
# ---------------------------------------------------------------------------

def run_recovery_sequence(app, package_name: str, loop_count: int, is_test: bool = False) -> bool:
    """
    Execute the recovery steps listed in the Recovery tab's listbox.

    :param app: CookieRunBotUI instance.
    :param package_name: Game package name (e.g. com.devsisters.crg).
    :param loop_count: Current macro loop count (used for log prefix).
    :param is_test: True when called from the test button (uses test_restart_running flag).
    :returns: True if recovery completed without failure, False otherwise.
    """
    def is_running():
        return app.test_restart_running if is_test else app.macro_running

    def set_status(text, color):
        app.root.after(0, lambda: app.status_label.config(text=text, fg=color))

    def log_act(msg):
        prefix = "[Test-Restart]" if is_test else "[Anti-Stuck]"
        log_bot_activity(f"{prefix} {msg}")

    recovery_steps = list(app.recovery_tab.recovery_listbox.get(0, tk.END))
    if not recovery_steps:
        log_act("ไม่มีขั้นตอนกู้คืนในคิว (คิวว่าง) ยกเลิกการกู้คืน")
        return False

    log_act(f"เริ่มรันขั้นตอนกู้คืนคัสตอม (ทั้งหมด {len(recovery_steps)} ขั้นตอน)")

    rec_idx = 0
    recovery_failed = False
    rec_loop_start_times: dict = {}
    rec_loop_counts: dict = {}

    while rec_idx < len(recovery_steps) and is_running():
        rec_step = recovery_steps[rec_idx]

        # Force-Stop
        if rec_step.startswith("[Force-Stop-Game]"):
            set_status("กู้คืน: สั่งปิดเกม (Force-Stop)...", "orange")
            if app.device and package_name:
                app.device.shell(f"am force-stop {package_name}")
            time.sleep(1.0)
            rec_idx += 1
            continue

        # Launch-Game
        if rec_step.startswith("[Launch-Game]"):
            set_status("กู้คืน: สั่งเปิดเกมใหม่...", "orange")
            if app.device and package_name:
                app.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
            time.sleep(1.0)
            rec_idx += 1
            continue

        # Delay
        if rec_step.startswith("[Delay]"):
            try:
                ms = int(rec_step.split(" ")[1].replace("ms", ""))
                delay_start = time.time()
                while time.time() - delay_start < (ms / 1000.0) and is_running():
                    elapsed = time.time() - delay_start
                    set_status(f"กู้คืน: กำลังโหลด/หน่วงเวลา... ({elapsed:.1f} วินาที)", "orange")
                    time.sleep(0.2)
            except Exception:
                time.sleep(1.0)
            rec_idx += 1
            continue

        # Swipe-Up
        if rec_step.startswith("[Swipe-Up]"):
            set_status("กู้คืน: กำลังลากขึ้น (Swipe Up)...", "blue")
            app.device.shell("input swipe 960 800 960 300 500")
            time.sleep(1.0)
            rec_idx += 1
            continue

        # Custom Swipe
        if rec_step.startswith("[Swipe]"):
            try:
                parts = rec_step.split(" ")
                if len(parts) >= 5:
                    start_xy = parts[1].split(",")
                    end_xy = parts[3].split(",")
                    dur = parts[4].replace("ms", "")
                    x1, y1 = start_xy[0], start_xy[1]
                    x2, y2 = end_xy[0], end_xy[1]
                    set_status(f"กู้คืน: กำลังลากหน้าจอ ({x1},{y1} -> {x2},{y2} เป็นเวลา {dur}ms)...", "blue")
                    if app.device:
                        app.device.shell(f"input swipe {x1} {y1} {x2} {y2} {dur}")
            except Exception as e:
                logging.error(f"Recovery custom swipe failed: {e}")
            time.sleep(1.0)
            rec_idx += 1
            continue

        # Template-Based Swipe
        if rec_step.startswith("[Swipe-Img]"):
            try:
                content = rec_step[12:].strip()
                dir_idx = content.rfind("Direction:")
                if dir_idx != -1:
                    img_name = content[:dir_idx].strip()
                    suffix = content[dir_idx:]
                    suffix_parts = suffix.split(" ")
                    if len(suffix_parts) >= 2:
                        sdir = suffix_parts[0].split(":")[1]
                        dur = suffix_parts[1].replace("ms", "")
                        
                        # Read coordinates from config.json directly
                        tx1, ty1, tx2, ty2 = 0, 0, 1920, 1080
                        config_path = os.path.join("templates", "config.json")
                        if os.path.exists(config_path):
                            try:
                                with open(config_path, 'r', encoding='utf-8') as f:
                                    cfg = json.load(f)
                                if img_name in cfg:
                                    c = cfg[img_name]
                                    tx1, ty1, tx2, ty2 = c['x1'], c['y1'], c['x2'], c['y2']
                            except Exception:
                                pass
                        
                        cx = (tx1 + tx2) // 2
                        cy = (ty1 + ty2) // 2
                        
                        if sdir == "Top-to-Bottom":
                            x1, y1 = cx, ty1 + 10
                            x2, y2 = cx, ty2 - 10
                        elif sdir == "Bottom-to-Top":
                            x1, y1 = cx, ty2 - 10
                            x2, y2 = cx, ty1 + 10
                        elif sdir == "Left-to-Right":
                            x1, y1 = tx1 + 10, cy
                            x2, y2 = tx2 - 10, cy
                        else: # Right-to-Left
                            x1, y1 = tx2 - 10, cy
                            x2, y2 = tx1 + 10, cy
                                
                        set_status(f"กู้คืน: ลากบนพิกัดรูป '{img_name}' เป็นเวลา {dur}ms...", "blue")
                        if app.device:
                            app.device.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {dur}")
            except Exception as e:
                logging.error(f"Recovery template swipe failed: {e}")
            time.sleep(1.0)
            rec_idx += 1
            continue

        # Solve-Minigame
        if rec_step.startswith("[Solve-Minigame]"):
            detect_img = "Bot check.png"
            parts = rec_step.split(" ", 1)
            if len(parts) == 2:
                detect_img = parts[1].strip()
            try:
                max_val, pos = app.do_template_match_by_name(detect_img)
                if max_val is not None and max_val >= 0.8:
                    log_act(f"ช่วงกู้คืน: ตรวจพบมินิเกม '{detect_img}' กำลังแก้ไข...")
                    success = app.solve_minigame_action(detect_img)
                    log_act("ช่วงกู้คืน: แก้ไขมินิเกมสำเร็จ!" if success else "ช่วงกู้คืน: แก้ไขมินิเกมล้มเหลว")
            except Exception as ex:
                log_act(f"ช่วงกู้คืน: แก้ไขมินิเกมล้มเหลว: {ex}")
            rec_idx += 1
            continue

        # Loop-Control
        if rec_step.startswith("[Loop-Control:"):
            try:
                steps_to_jump = int(rec_step.split(":")[1].split("]")[0])
                is_count_mode = "Count:" in rec_step

                if is_count_mode:
                    max_count = int(rec_step.split("Count:")[1])
                    if rec_idx not in rec_loop_counts:
                        rec_loop_counts[rec_idx] = 0
                    if rec_loop_counts[rec_idx] < max_count:
                        rec_loop_counts[rec_idx] += 1
                        done = rec_loop_counts[rec_idx]
                        set_status(f"กู้คืน: วนลูปย้อนกลับ {steps_to_jump} สเต็ป (รอบ {done}/{max_count})...", "blue")
                        time.sleep(0.05)
                        rec_idx = max(0, rec_idx - steps_to_jump)
                        continue
                    else:
                        set_status("กู้คืน: ครบจำนวนรอบวนลูปแล้ว ไปต่อ...", "green")
                        del rec_loop_counts[rec_idx]
                else:
                    dur_part = rec_step.split("Duration:")[1]
                    if "ms" in dur_part:
                        duration_sec = int(dur_part.replace("ms", "")) / 1000.0
                    else:
                        duration_sec = int(dur_part.replace("s", ""))
                    if rec_idx not in rec_loop_start_times:
                        rec_loop_start_times[rec_idx] = time.time()
                    elapsed_loop = time.time() - rec_loop_start_times[rec_idx]
                    if elapsed_loop < duration_sec:
                        remaining = duration_sec - elapsed_loop
                        set_status(f"กู้คืน: วนลูปย้อนกลับ {steps_to_jump} สเต็ป (เหลือ {remaining:.1f} วิ)...", "blue")
                        time.sleep(0.05)
                        rec_idx = max(0, rec_idx - steps_to_jump)
                        continue
                    else:
                        set_status("กู้คืน: หมดเวลาวนลูป ไปต่อ...", "green")
                        del rec_loop_start_times[rec_idx]
            except Exception as e:
                logging.error(f"Recovery loop control failed: {e}")
            rec_idx += 1
            continue

        # Skip / SkipNot / FullSkip / FullSkipNot
        if rec_step.startswith("[Skip:") or rec_step.startswith("[SkipNot:") or rec_step.startswith("[FullSkip:") or rec_step.startswith("[FullSkipNot:"):
            try:
                is_skip_if = rec_step.startswith("[Skip:") or rec_step.startswith("[FullSkip:")
                ignore_roi = rec_step.startswith("[FullSkip:") or rec_step.startswith("[FullSkipNot:")
                skip_count = int(rec_step.split(":")[1].split("]")[0])
                target_name = rec_step.split("]")[1].strip()
                set_status(f"กู้คืน: ตรวจสอบภาพ '{target_name}' เพื่อข้ามสเต็ป...", "blue")
                max_val, pos = app.do_template_match_by_name(target_name, ignore_roi=ignore_roi)
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

        # Click / Wait (generic)
        parts = rec_step.split(" ", 1)
        if len(parts) == 2:
            action_type, target_name = parts[0], parts[1]
            target_names = [t.strip() for t in target_name.split("|") if t.strip()]
            display_name = target_names[0] if target_names else target_name
            set_status(f"กู้คืน: {action_type} รอรูป '{display_name}'...", "blue")
            step_start = time.time()
            while time.time() - step_start < 10.0 and is_running():
                max_val, pos, matched_name = None, None, None
                ignore_roi = (action_type == "[Full-Click]")
                for tn in target_names:
                    mv, p = app.do_template_match_by_name(tn, ignore_roi=ignore_roi)
                    if mv is not None and mv >= 0.8:
                        max_val, pos, matched_name = mv, p, tn
                        break
                if max_val is not None and max_val >= 0.8:
                    if action_type in ["[Click]", "[Full-Click]"]:
                        app.device.shell(f"input tap {pos[0]} {pos[1]}")
                    break
                time.sleep(0.5)

        rec_idx += 1

    if recovery_failed:
        log_act("การกู้คืนล้มเหลว (ไม่พบหน้าล็อบบี้)")
        return False
    else:
        log_act("สิ้นสุดการทำงานขั้นตอนกู้คืนเรียบร้อย")
        return True


# ---------------------------------------------------------------------------
# Main macro worker
# ---------------------------------------------------------------------------

def macro_worker(app, steps: tuple) -> None:
    """
    Background-thread function that loops through macro steps until stopped.

    :param app: CookieRunBotUI instance.
    :param steps: Tuple of step strings from the macro listbox.
    """
    try:
        loop_count = 1
        loop_start_times: dict = {}
        loop_counts: dict = {}

        while app.macro_running:
            i = 0
            while i < len(steps) and app.macro_running:
                step_item = steps[i]

                # --- Delay ---
                if step_item.startswith("[Delay]"):
                    try:
                        ms = int(step_item.split(" ")[1].replace("ms", ""))
                        app.root.after(0, lambda lc=loop_count, m=ms: app.status_label.config(
                            text=f"Macro [รอบ {lc}]: หน่วงเวลา (Delay) {m} ms...", fg="blue"
                        ))
                        time.sleep(ms / 1000.0)
                    except Exception:
                        pass
                    i += 1
                    continue

                # --- Loop-Control ---
                if step_item.startswith("[Loop-Control:"):
                    try:
                        steps_to_jump = int(step_item.split(":")[1].split("]")[0])
                        is_count_mode = "Count:" in step_item

                        if is_count_mode:
                            max_count = int(step_item.split("Count:")[1])
                            if i not in loop_counts:
                                loop_counts[i] = 0
                            if loop_counts[i] < max_count:
                                loop_counts[i] += 1
                                done = loop_counts[i]
                                app.root.after(0, lambda lc=loop_count, s=steps_to_jump, d=done, mx=max_count:
                                               app.status_label.config(
                                                   text=f"Macro [รอบ {lc}]: วนลูปย้อนกลับ {s} สเต็ป (รอบ {d}/{mx})...",
                                                   fg="blue"
                                               ))
                                time.sleep(0.05)
                                i = max(0, i - steps_to_jump) - 1
                            else:
                                app.root.after(0, lambda lc=loop_count: app.status_label.config(
                                    text=f"Macro [รอบ {lc}]: ครบจำนวนรอบวนลูปแล้ว ไปต่อ...", fg="green"
                                ))
                                del loop_counts[i]
                        else:
                            dur_part = step_item.split("Duration:")[1]
                            if "ms" in dur_part:
                                duration_sec = int(dur_part.replace("ms", "")) / 1000.0
                            else:
                                duration_sec = int(dur_part.replace("s", ""))
                            if i not in loop_start_times:
                                loop_start_times[i] = time.time()
                            elapsed_loop = time.time() - loop_start_times[i]
                            if elapsed_loop < duration_sec:
                                remaining = duration_sec - elapsed_loop
                                app.root.after(0, lambda lc=loop_count, s=steps_to_jump,
                                                      el=elapsed_loop, rem=remaining:
                                               app.status_label.config(
                                                   text=f"Macro [รอบ {lc}]: วนลูปย้อนกลับ {s} สเต็ป "
                                                        f"(รันแล้ว {el:.1f}/{duration_sec} วิ, เหลือ {rem:.1f} วิ)...",
                                                   fg="blue"
                                               ))
                                time.sleep(0.05)
                                i = max(0, i - steps_to_jump) - 1
                            else:
                                app.root.after(0, lambda lc=loop_count: app.status_label.config(
                                    text=f"Macro [รอบ {lc}]: หมดระยะเวลาวนลูปแล้ว ไปต่อ...", fg="green"
                                ))
                                del loop_start_times[i]
                    except Exception as e:
                        logging.error(f"Loop control parser failed: {e}")
                    i += 1
                    continue

                # --- Force-Stop-Game ---
                if step_item.startswith("[Force-Stop-Game]"):
                    package_name = app.recovery_tab.package_var.get().strip()
                    app.root.after(0, lambda lc=loop_count, pkg=package_name: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: สั่งปิดเกม ({pkg})...", fg="orange"
                    ))
                    if app.device and package_name:
                        app.device.shell(f"am force-stop {package_name}")
                    time.sleep(1.0)
                    i += 1
                    continue

                # --- Launch-Game ---
                if step_item.startswith("[Launch-Game]"):
                    package_name = app.recovery_tab.package_var.get().strip()
                    app.root.after(0, lambda lc=loop_count, pkg=package_name: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: สั่งเปิดเกม ({pkg})...", fg="orange"
                    ))
                    if app.device and package_name:
                        app.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
                    time.sleep(1.0)
                    i += 1
                    continue

                # --- Swipe-Up ---
                if step_item.startswith("[Swipe-Up]"):
                    app.root.after(0, lambda lc=loop_count: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: กำลังลากขึ้น (Swipe Up)...", fg="blue"
                    ))
                    if app.device:
                        app.device.shell("input swipe 960 800 960 300 500")
                    time.sleep(1.0)
                    i += 1
                    continue

                # --- Custom Swipe ---
                if step_item.startswith("[Swipe]"):
                    try:
                        parts = step_item.split(" ")
                        if len(parts) >= 5:
                            start_xy = parts[1].split(",")
                            end_xy = parts[3].split(",")
                            dur = parts[4].replace("ms", "")
                            x1, y1 = start_xy[0], start_xy[1]
                            x2, y2 = end_xy[0], end_xy[1]
                            app.root.after(0, lambda lc=loop_count, sx=x1, sy=y1, ex=x2, ey=y2, d=dur:
                                           app.status_label.config(
                                               text=f"Macro [รอบ {lc}]: ลากหน้าจอ ({sx},{sy} -> {ex},{ey} {d}ms)...",
                                               fg="blue"
                                           ))
                            if app.device:
                                app.device.shell(f"input swipe {x1} {y1} {x2} {y2} {dur}")
                    except Exception as e:
                        logging.error(f"Macro custom swipe failed: {e}")
                    time.sleep(1.0)
                    i += 1
                    continue

                # --- Template-Based Swipe ---
                if step_item.startswith("[Swipe-Img]"):
                    try:
                        content = step_item[12:].strip()
                        dir_idx = content.rfind("Direction:")
                        if dir_idx != -1:
                            img_name = content[:dir_idx].strip()
                            suffix = content[dir_idx:]
                            suffix_parts = suffix.split(" ")
                            if len(suffix_parts) >= 2:
                                sdir = suffix_parts[0].split(":")[1]
                                dur = suffix_parts[1].replace("ms", "")
                                
                                # Read coordinates from config.json directly
                                tx1, ty1, tx2, ty2 = 0, 0, 1920, 1080
                                config_path = os.path.join("templates", "config.json")
                                if os.path.exists(config_path):
                                    try:
                                        with open(config_path, 'r', encoding='utf-8') as f:
                                            cfg = json.load(f)
                                        if img_name in cfg:
                                            c = cfg[img_name]
                                            tx1, ty1, tx2, ty2 = c['x1'], c['y1'], c['x2'], c['y2']
                                    except Exception:
                                        pass
                                
                                cx = (tx1 + tx2) // 2
                                cy = (ty1 + ty2) // 2
                                
                                if sdir == "Top-to-Bottom":
                                    x1, y1 = cx, ty1 + 10
                                    x2, y2 = cx, ty2 - 10
                                elif sdir == "Bottom-to-Top":
                                    x1, y1 = cx, ty2 - 10
                                    x2, y2 = cx, ty1 + 10
                                elif sdir == "Left-to-Right":
                                    x1, y1 = tx1 + 10, cy
                                    x2, y2 = tx2 - 10, cy
                                else: # Right-to-Left
                                    x1, y1 = tx2 - 10, cy
                                    x2, y2 = tx1 + 10, cy
                                        
                                app.root.after(0, lambda lc=loop_count, img=img_name, d=dur:
                                               app.status_label.config(
                                                   text=f"Macro [รอบ {lc}]: ลากบนพิกัดรูป '{img}' เป็นเวลา {d}ms...", fg="orange"
                                               ))
                                if app.device:
                                    app.device.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {dur}")
                    except Exception as e:
                        logging.error(f"Macro template swipe failed: {e}")
                    time.sleep(1.0)
                    i += 1
                    continue

                # --- Solve-Minigame ---
                if step_item.startswith("[Solve-Minigame]"):
                    detect_img = "Bot check.png"
                    parts = step_item.split(" ", 1)
                    if len(parts) == 2:
                        detect_img = parts[1].strip()
                    app.root.after(0, lambda lc=loop_count, di=detect_img: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: ตรวจมินิเกมด้วยรูป '{di}'...", fg="blue"
                    ))
                    max_val, pos = app.do_template_match_by_name(detect_img)
                    if max_val is not None and max_val >= 0.8:
                        log_bot_activity(f"[รอบที่ {loop_count}] ตรวจพบมินิเกมด้วยรูป '{detect_img}' "
                                         f"(ความมั่นใจ: {max_val*100:.1f}%) กำลังเริ่มแก้ไข...")
                        app.root.after(0, lambda lc=loop_count: app.status_label.config(
                            text=f"Macro [รอบ {lc}]: ตรวจพบมินิเกม! กำลังแก้ไข...", fg="orange"
                        ))
                        try:
                            success = app.solve_minigame_action(detect_img)
                            if success:
                                log_bot_activity(f"[รอบที่ {loop_count}] แก้ไขมินิเกมสำเร็จ!")
                                app.root.after(0, lambda lc=loop_count: app.status_label.config(
                                    text=f"Macro [รอบ {lc}]: แก้ไขมินิเกมสำเร็จ!", fg="green"
                                ))
                            else:
                                log_bot_activity(f"[รอบที่ {loop_count}] แก้ไขมินิเกมล้มเหลว")
                                app.root.after(0, lambda lc=loop_count: app.status_label.config(
                                    text=f"Macro [รอบ {lc}]: แก้ไขมินิเกมล้มเหลว", fg="red"
                                ))
                        except Exception as ex:
                            log_bot_activity(f"[รอบที่ {loop_count}] แก้ไขมินิเกมเกิดข้อผิดพลาด: {ex}")
                            logging.error(f"Solve Minigame error: {ex}")
                    else:
                        app.root.after(0, lambda lc=loop_count: app.status_label.config(
                            text=f"Macro [รอบ {lc}]: ไม่พบมินิเกม, ข้ามไป...", fg="green"
                        ))
                    i += 1
                    continue

                # --- Type-Text ---
                if step_item.startswith("[Type-Text]"):
                    parts_t = step_item.split(" ", 1)
                    text_to_type = parts_t[1].strip() if len(parts_t) == 2 else ""
                    app.root.after(0, lambda lc=loop_count, tx=text_to_type: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: พิมพ์ข้อความ '{tx}'...", fg="blue"
                    ))
                    if app.device and text_to_type:
                        try:
                            app.device.shell(f"input text {text_to_type}")
                        except Exception as ex:
                            logging.error(f"Type-Text error: {ex}")
                    time.sleep(0.5)
                    i += 1
                    continue

                # --- Press-Enter ---
                if step_item.startswith("[Press-Enter]"):
                    app.root.after(0, lambda lc=loop_count: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: กด Enter...", fg="blue"
                    ))
                    if app.device:
                        try:
                            app.device.shell("input keyevent 66")
                        except Exception as ex:
                            logging.error(f"Press-Enter error: {ex}")
                    time.sleep(0.5)
                    i += 1
                    continue

                # --- Standalone Break ---
                if step_item.strip() == "[Break]":
                    app.root.after(0, lambda lc=loop_count: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: คำสั่ง [Break] — หยุดมาโครทันที!", fg="red"
                    ))
                    app.macro_running = False
                    break

                # --- Generic step: action + image name ---
                parts = step_item.split(" ", 1)
                if len(parts) != 2:
                    i += 1
                    continue

                action, rest = parts[0], parts[1]
                spam_target = None
                spam_interval = 600
                spam_random = 0

                # Parse [spam_target] [S:ms] [R:ms]
                if action in ["[Spam-Wait]", "[Spam-Click]"]:
                    if rest.startswith("["):
                        e_idx = rest.find("]")
                        if e_idx != -1:
                            spam_target = rest[1:e_idx]
                            rest = rest[e_idx + 1:].strip()
                    if rest.startswith("[S:"):
                        e_idx = rest.find("]")
                        if e_idx != -1:
                            try:
                                spam_interval = int(rest[3:e_idx])
                            except ValueError:
                                pass
                            rest = rest[e_idx + 1:].strip()
                    if rest.startswith("[R:"):
                        e_idx = rest.find("]")
                        if e_idx != -1:
                            try:
                                spam_random = int(rest[3:e_idx])
                            except ValueError:
                                pass
                            rest = rest[e_idx + 1:].strip()

                step_name = rest
                step_names = [s.strip() for s in step_name.split("|") if s.strip()]

                # --- Skip-If / FullSkip-If ---
                if action.startswith("[Skip:") or action.startswith("[FullSkip:"):
                    is_full = action.startswith("[FullSkip:")
                    skip_count = int(action.split(":")[1][:-1])
                    app.root.after(0, lambda sn=step_name, lc=loop_count: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: เช็คภาพ '{sn}' (Full) ว่าต้องข้ามหรือไม่..." if is_full else f"Macro [รอบ {lc}]: เช็คภาพ '{sn}' ว่าต้องข้ามหรือไม่...", fg="blue"
                    ))
                    max_val, pos = app.do_template_match_by_name(step_name, ignore_roi=is_full)
                    if max_val is not None and max_val >= 0.8:
                        app.root.after(0, lambda sn=step_name, sc=skip_count: app.status_label.config(
                            text=f"Macro: เจอ '{sn}' สั่งกระโดดข้าม {sc} สเต็ป!", fg="orange"
                        ))
                        i += skip_count + 1
                    else:
                        i += 1
                    continue

                # --- Skip-IfNot / FullSkip-IfNot ---
                if action.startswith("[SkipNot:") or action.startswith("[FullSkipNot:"):
                    is_full = action.startswith("[FullSkipNot:")
                    skip_count = int(action.split(":")[1][:-1])
                    app.root.after(0, lambda sn=step_name, lc=loop_count: app.status_label.config(
                        text=f"Macro [รอบ {lc}]: เช็คภาพ '{sn}' (Full) ว่าต้องข้ามหรือไม่..." if is_full else f"Macro [รอบ {lc}]: เช็คภาพ '{sn}' ว่าต้องข้ามหรือไม่...", fg="blue"
                    ))
                    max_val, pos = app.do_template_match_by_name(step_name, ignore_roi=is_full)
                    if max_val is None or max_val < 0.8:
                        app.root.after(0, lambda sn=step_name, sc=skip_count: app.status_label.config(
                            text=f"Macro: ไม่เจอ '{sn}' สั่งกระโดดข้าม {sc} สเต็ป!", fg="orange"
                        ))
                        i += skip_count + 1
                    else:
                        i += 1
                    continue

                # --- Click / Wait / Spam ---
                step_name_display = step_names[0] if step_names else step_name
                app.root.after(0, lambda sn=step_name_display, lc=loop_count, act=action: app.status_label.config(
                    text=f"Macro [รอบ {lc}]: {act} รอภาพ '{sn}'...", fg="blue"
                ))

                spam_thread_active = False
                app.spam_running = False

                step_start_time = time.time()
                try:
                    timeout_limit = int(app.recovery_tab.timeout_var.get()) * 60
                except Exception:
                    timeout_limit = 300

                while app.macro_running:
                    # Start spam thread (once per step)
                    if action in ["[Spam-Wait]", "[Spam-Click]"] and spam_target and not spam_thread_active:
                        app.spam_running = True
                        spam_thread_active = True

                        tap_cmd = None
                        if "," in spam_target:
                            try:
                                sx, sy = map(int, spam_target.split(","))
                                tap_cmd = f"input tap {sx} {sy}"
                            except Exception:
                                pass
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
                                except Exception:
                                    pass

                        if tap_cmd:
                            def spammer(cmd, interval, rand_interval):
                                import random
                                while app.spam_running and app.macro_running:
                                    app.device.shell(cmd)
                                    added = random.randint(0, rand_interval) if rand_interval > 0 else 0
                                    time.sleep((interval + added) / 1000.0)
                            threading.Thread(target=spammer,
                                             args=(tap_cmd, spam_interval, spam_random),
                                             daemon=True).start()
                            app.root.after(0, lambda sn=step_name, sp=spam_target: app.status_label.config(
                                text=f"Macro: เริ่มสแปมพิกัด '{sp}' เบื้องหลังแล้ว! กำลังรอภาพ '{sn}'...",
                                fg="orange"
                            ))
                        else:
                            app.root.after(0, lambda sn=step_name: app.status_label.config(
                                text=f"Macro: ผิดพลาด ไม่พบพิกัด '{spam_target}' ในระบบ (รอภาพ '{sn}' ต่อไป)",
                                fg="red"
                            ))

                    # Update status
                    elapsed = time.time() - step_start_time
                    if action in ["[Spam-Wait]", "[Spam-Click]"]:
                        names_display = "|".join(step_names) if step_names else step_name
                        app.root.after(0, lambda sn=names_display, lc=loop_count,
                                              sp=spam_target or "", el=elapsed, tl=timeout_limit:
                                       app.status_label.config(
                                           text=f"Macro [รอบ {lc}]: สแปม '{sp}' รอภาพ '{sn}'... ({int(el)}/{tl} วิ)",
                                           fg="orange"
                                       ))
                    else:
                        nd = step_names[0] if step_names else step_name
                        app.root.after(0, lambda sn=nd, lc=loop_count, act=action, el=elapsed, tl=timeout_limit:
                                       app.status_label.config(
                                           text=f"Macro [รอบ {lc}]: {act} รอภาพ '{sn}'... ({int(el)}/{tl} วิ)",
                                           fg="blue"
                                       ))

                    # Check image
                    max_val, pos, matched_name = None, None, None
                    ignore_roi = (action == "[Full-Click]")
                    for sn in (step_names if step_names else [step_name]):
                        mv, p = app.do_template_match_by_name(sn, ignore_roi=ignore_roi)
                        if mv is not None and mv >= 0.8:
                            max_val, pos, matched_name = mv, p, sn
                            break

                    if max_val is not None and max_val >= 0.8:
                        app.spam_running = False
                        _found = matched_name or step_name

                        if action in ["[Click]", "[Full-Click]"]:
                            app.device.shell(f"input tap {pos[0]} {pos[1]}")
                            app.root.after(0, lambda sn=_found: app.status_label.config(
                                text=f"Macro: คลิก '{sn}' แล้ว!", fg="green"
                            ))

                        elif action == "[Spam-Click]":
                            app.device.shell(f"input tap {pos[0]} {pos[1]}")
                            app.root.after(0, lambda sn=_found: app.status_label.config(
                                text=f"Macro: เจอภาพ '{sn}' สั่งหยุดสแปมและคลิกภาพแล้ว!", fg="green"
                            ))

                        elif action == "[Spam-Wait]":
                            app.root.after(0, lambda sn=_found: app.status_label.config(
                                text=f"Macro: เจอภาพ '{sn}' แล้ว สั่งหยุดสแปมและไปต่อ (ไม่กด)...", fg="green"
                            ))

                        elif action == "[Break]":
                            app.root.after(0, lambda sn=_found: app.status_label.config(
                                text=f"Macro: เจอภาพ '{sn}' บังคับหยุดการทำงานมาโคร (Break)!", fg="red"
                            ))
                            app.macro_running = False
                            break

                        else:  # [Wait]
                            app.root.after(0, lambda sn=_found: app.status_label.config(
                                text=f"Macro: เจอภาพ '{sn}' แล้ว (ไม่กด) ไปสเต็ปถัดไป...", fg="green"
                            ))

                        break  # exit inner while loop

                    # Timeout check
                    elapsed = time.time() - step_start_time
                    if elapsed > timeout_limit:
                        app.spam_running = False
                        package_name = app.recovery_tab.package_var.get().strip()
                        log_bot_activity(
                            f"[Anti-Stuck] รอบที่ {loop_count} ตรวจพบหน้าจอค้างที่ขั้นตอน '{step_name}' "
                            f"นานเกิน {timeout_limit} วินาที"
                        )

                        # Save stuck screenshot
                        try:
                            if app.device:
                                screencap = app.device.screencap()
                                if screencap:
                                    os.makedirs("stuck_screenshots", exist_ok=True)
                                    clean = "".join(
                                        c if c.isalnum() or c in ("-", "_") else "_" for c in step_name
                                    )
                                    ts = time.strftime("%Y%m%d_%H%M%S")
                                    path = os.path.join("stuck_screenshots", f"stuck_{ts}_{clean}.png")
                                    with open(path, "wb") as f:
                                        f.write(screencap)
                                    log_bot_activity(f"[Anti-Stuck] บันทึกภาพหน้าจอค้างไว้ที่ '{path}'")
                        except Exception as cap_ex:
                            log_bot_activity(f"[Anti-Stuck] ไม่สามารถบันทึกภาพหน้าจอค้างได้: {cap_ex}")

                        app.root.after(0, lambda sn=step_name: app.status_label.config(
                            text=f"Macro: ภาพ '{sn}' ไม่มาตามเวลา! กำลังกู้คืน...", fg="red"
                        ))
                        time.sleep(2.0)
                        if app.device and package_name:
                            run_recovery_sequence(app, package_name, loop_count, is_test=False)
                            i = -1
                            break
                        else:
                            app.macro_running = False
                            break

                    try:
                        sc_d = int(app.macro_tab.screencap_delay_var.get()) / 1000.0
                    except Exception:
                        sc_d = 1.0
                    time.sleep(sc_d)

                # Post-step delay before moving to next step
                try:
                    ps_d = int(app.macro_tab.post_step_delay_var.get()) / 1000.0
                except Exception:
                    ps_d = 1.0
                if ps_d > 0 and app.macro_running:
                    time.sleep(ps_d)

                i += 1  # move to next step

            loop_count += 1

    except Exception:
        logging.error(f"Macro Thread Error: {traceback.format_exc()}")
    finally:
        app.macro_running = False
        macro_tab = app.macro_tab
        app.root.after(0, lambda: macro_tab.start_macro_btn.config(state=tk.NORMAL))
        app.root.after(0, lambda: macro_tab.stop_macro_btn.config(state=tk.DISABLED))
        app.root.after(0, lambda: app.templates_tab.create_template_btn.config(state=tk.NORMAL))
        app.root.after(0, lambda: app.status_label.config(text="Status: Macro Stopped", fg="red"))
