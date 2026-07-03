# AI Work History

This file tracks the changes and tasks performed by the AI on this project. 

## [2026-07-02]
- Created this `AI_HISTORY.md` file to track AI actions.
- Configured `.agents/AGENTS.md` to ensure the AI always reads and updates this history file upon starting or finishing a task.
- Linked Git repository to `https://github.com/HartNM/CookieRun_Bot.git`, committed initial files (`AI_HISTORY.md`, `.agents/AGENTS.md`), and pushed to `main`.
- Checked for Python installation (not found) and started installation using Winget (`Python.Python.3.12`).
- Created `main.py` (Tkinter UI) and `requirements.txt` for connecting to MuMu Player via ADB (pure-python-adb) and capturing screenshots using OpenCV.
- Created `run.bat` script to automatically check Python, install/verify `requirements.txt`, and start the app (`main.py`) for easier launching.
- Added global exception handling (`sys.excepthook`) and logging to `main.py` so crashes are recorded in `bot_error.log` and users see clear Thai popups instead of silent failures.
- Added ADB auto-download feature: If ADB is missing, `main.py` downloads it automatically from Google and starts the local server.
- Added automatic resolution check (via `wm size`) upon ADB connection to warn the user if MuMu is not set to 1080p.
- Added a "Find & Click 'Play!'" button that uses OpenCV `matchTemplate` to look for `template_play.png` on the live screen and auto-click it via ADB if confidence is > 80%.
- Added a "Test Find 'Play!' (No Click)" button to verify the button exists on the screen without triggering a tap.
- Created and executed a script (`crop_smart.py`) to perfectly crop `template_play.png` to a 160x60 tight rectangle centered on the word "Play!" for maximum OpenCV accuracy.
- **Redesigned UI: Added Template Maker!** Replaced hardcoded play button checks with a full Template Manager. Users can click "Capture & Crop New Template" to take a live screenshot, drag a mouse to crop a region, name it, and save it. It populates a dropdown list where users can select any saved template to test or click.
- **Migrated to 1080p:** Reverted to 1080p resolution per user request.
- **Added Macro Builder Engine:** Redesigned UI with tabs. Added a fully functional Macro Builder tab that uses `threading` to run automated sequences asynchronously. Users can chain multiple templates together into a list. The macro will scan for each image in sequence and wait infinitely until the image appears before clicking and moving to the next step, enabling fully automated bot loops.
- **Added Macro Action Types:** Added a dropdown to the Macro Builder allowing users to choose whether the step should `[Click]` (wait and click), `[Wait]` (wait but do not click), or `[Skip-If]` (check once, if found, skip N steps forward).
- **Added Rename Template Feature:** Added a button in the Template Manager tab to easily rename saved templates. It automatically renames the `.png` file, updates the internal `config.json` coordinates mapping, and retroactively updates any active steps in the Macro Builder list to reflect the new name.
- **Added Save/Load Macro Profiles:** Added 'Save' and 'Load' buttons to the Macro Builder tab, allowing users to save their entire macro sequence queue to a `.json` file in a dedicated `macros/` folder and load it back later.
- **Added Custom Delay:** Added a Delay (ms) input field to the Macro Builder. Users can now specify the exact waiting time after a `[Click]` or `[Wait]` action triggers before moving to the next step, replacing the hardcoded `2.0s` sleep.
- **Added Standalone Delay Step:** Users can now select `-- เพิ่มเวลาหน่วง (Delay) --` from the saved template dropdown to insert a pure time delay into the macro queue, without needing to check any images.
- **Added Restart App Button:** Added a `🔄 Restart App` button to the main UI. Clicking it safely stops any running macros and instantly restarts the Python application, allowing for a fresh state without manually closing and re-opening `run.bat`.
- **Enhanced Macro Listbox:** The Macro Builder listbox now supports direct drag-and-drop reordering with the mouse. Additionally, `Up` and `Down` arrow buttons have been added for manual reordering, and an `Edit` button has been added to modify the raw text of a step without having to recreate it.
- **Added Spam-Wait Parallel Task:** Added a `[Spam-Wait]` action type. It allows the macro to continuously click a secondary target image (e.g., a Jump button) OR a specific X,Y coordinate (e.g., `150,850`) every 600ms while simultaneously scanning the screen for the primary target image (e.g., Cookie Relay). This enables parallel background execution via ADB without taking control of the user's host OS keyboard and perfectly handles semi-transparent game buttons.
- **Added Auto-Solve Minigame Feature:** Added a `[Solve-Minigame]` action that checks if a bot verification minigame ("Surprise! Find the sliding card!") has appeared on screen (detecting via `Bot check.png`). If detected, it runs a dynamic feedback loop that continues to solve the cards as long as the verification screen is visible (up to 6 attempts), matching image templates at the start of each iteration. In each round, it crops the 6 card regions, calculates their pairwise Mean Squared Error (MSE) in grayscale to identify the 2 unique cards, clicks them via ADB, and waits 2.5 seconds. This handles cases where clicks are missed or the game has a variable number of rounds.
- **Added Skip-IfNot Action:** Added `[Skip-IfNot]` (rendered as `[SkipNot:N]`) to skip N steps if a target image is *not* found.
- **Created gitignore:** Created a minimal `.gitignore` file to ignore Python compiled files (`__pycache__/`, `*.pyc`), PyInstaller build output folders (`build/`, `dist/`), standalone executables (`*.exe`), and log files (`*.log`).
- **Added Anti-Stuck Timeout & Auto-Recovery:** Added a global Step Timeout setting to the UI (default 5 minutes) and a stuck recovery system. If the bot is stuck waiting for a button/template for longer than the set timeout, it can perform one of three actions: (1) restart the game using ADB (`am force-stop` followed by `monkey` launcher command) and reset macro index to 0 to recover automatically, (2) skip the stuck step and proceed, or (3) stop the macro and show an alert. Timeout settings are saved/loaded as part of the macro JSON profile. The restart recovery routine was enhanced to wait 20 seconds, then check and auto-solve any minigame (`Bot check.png`), and spam-click the level-up confirmation (`Level Up Confirm.png`) every 1.0s until the `Lobby.png` screen is reached (up to 45 seconds) to ensure the game is fully loaded before the macro restarts.
- **Added Template Management & Package Control Test buttons:** Added a `🗑️ ลบภาพ` button to delete selected template images from templates/ and remove their coordinates from templates/config.json. Also added `⚡ ทดสอบปิดเกม` and `🚀 ทดสอบเปิดเกม` buttons to manually trigger force-stop and monkey launch actions on the emulator using the package name input to verify the ADB configuration works properly.
- **Added Package Auto-Detection Button:** Added a `🔍 ดึงจากจอ` (Get Active App) button that queries ADB for the focused Android application's package name and auto-fills the package input field, making it easy to configure recovery commands without manual lookup.
- Differentiated Spam-Click and Spam-Wait: Exposed `[Spam-Click]` on the UI dropdown. Differentiated their logic so `[Spam-Click]` immediately taps the primary target image when detected, while `[Spam-Wait]` stops background spamming and moves to the next step without clicking the target image.
- Read and reviewed the contents of `.agents/AGENTS.md` as requested by the user.
- **Updated Solve-Minigame:** Increased `max_attempts` from 6 to 10 in the `[Solve-Minigame]` action function inside `main.py` per user request.
- **Built Executable:** Rebuilt the application executable `CookieRun_Bot.exe` using PyInstaller with the spec file `CookieRun_Bot.spec` and copied the newly built executable to the root directory.

## [2026-07-03]
- **Added Bot Activity Logging:** Created a dedicated logging system that writes to `bot_run.log`, tracking which round has minigames and when the Anti-stuck system is triggered. Rebuilt the executable file `CookieRun_Bot.exe`.
- **Updated AGENTS.md Rules:** Added rules to prevent automatic execution of build and git commands without explicit user permission/requests.
- **Added Anti-Stuck Screen Capture:** Added automatic screenshot capturing and saving to a local `stuck_screenshots/` folder when the Anti-stuck system is triggered. Also added the folder to `.gitignore`.
- **Added Recovery Test Button:** Added a `🔄 ทดสอบรีสตาร์ทเกม & เริ่มใหม่` button in the Anti-Stuck Settings UI. It runs the full recovery flow (force-stopping the game, launching the game, checking/solving the minigame, and spam-clicking the level up confirmation until the lobby is reached) in a background thread with cancellation support so users can test recovery without freezing the app.
- **Enhanced Lobby Detection:** Replaced the hardcoded check for `Lobby.png` with a dynamic search of all files matching `Lobby*.png` (e.g. `Lobby 1.png`, `Lobby 3.png`, `Lobby 4.png` etc.) using a new `check_lobby_reached` helper. This fixes recovery detection for users who have multiple named lobby template files instead of a single `Lobby.png` file.
- **Added News Popup Auto-Close during Recovery:** Integrated automatic check and click for `Login Exit.png` inside the recovery loop and test recovery loop. If the News window popup appears, the bot will automatically detect `Login Exit.png` and tap it to close the popup, preventing it from blocking lobby detection.
- **Added Recovery Elapsed Timers:** Implemented live timers that track and display the exact number of seconds elapsed since starting the game recovery sequence (waiting for game load and scanning/spamming to lobby) in both actual macro and test recovery threads, updating the UI status dynamically.
- **Added Live Timeout Countdown for Macro Steps:** Implemented a live waiting timer format `(Elapsed / MaxTimeout seconds)` in the status label during the macro's image check loop. This lets users see exactly how many seconds have elapsed and how much time remains before the Anti-Stuck system triggers a game restart.
- **Refactored Recovery Loop to be Reactive & Anti-Stuck Solving:** Removed the static one-time minigame check before the recovery loop. Moved the minigame detection (`Bot check.png`) inside the 45-second recovery loop, prioritizing it over popups and fallback coordinate clicks. If `Bot check.png` is detected at any point during recovery, the bot immediately runs the minigame solver and suspends other actions, preventing blind clicks from failing the minigame.
- **Added [Break] Action Type:** Added a `[Break]` action to the macro dropdown list. When executing, the macro will wait for the specified target image to appear on screen, and once detected, it will programmatically stop the macro execution (setting `self.macro_running = False` and terminating the thread loops), allowing clean stop conditions within the macro queue.
- **Added [Loop] Action Type:** Added a `[Loop]` action to the macro dropdown list. Selecting this action prompts the user to input a loop click interval in milliseconds. During macro execution, the bot will first wait for the target image to appear (with standard timeout and recovery support), and once visible, it will repeatedly click the target image at the specified interval until it disappears from the screen, then proceed to the next step.
- **Added [Loop-Multi] Action Type:** Added a `[Loop-Multi]` action to the macro dropdown list. When adding this step, it opens a custom Toplevel dialog listing all template PNG files (enabling multiple selection via Listbox) and prompts for a click interval in milliseconds. During execution, the bot continuously scans for any of the selected templates. If any are matched, it clicks the matched coordinates, waits for the specified interval, and repeats. The loop ends (and proceeds to the next macro step) once none of the selected templates are visible on the screen.
- **Added [Loop-Control] Step Option:** Added `-- วนลูป (Loop) --` to the macro template dropdown selection. When added, it opens a single unified Toplevel dialog prompting the user for both the number of steps to jump back (repeat) and the loop duration in seconds. During execution, it functions as a JUMP instruction, repeating the previous N steps for the specified duration before proceeding to the next step, enabling clean time-bounded control loops.
- **Implemented Dynamic UI Visibility for Action Combobox:** Wrapped the "Action:" label and dropdown in a container frame (`self.action_frame`) and bound the `<<ComboboxSelected>>` event to `self.macro_combo`. When the user selects a special non-image option (e.g. `-- เพิ่มเวลาหน่วง (Delay) --`, `-- แก้ไขมินิเกม (Solve Minigame) --`, or `-- วนลูป (Loop) --`), the Action dropdown is automatically hidden (`pack_forget()`) to simplify the UI, and is shown again for normal image steps.
- **Recovered main.py and Fixed Syntax/Indentation Errors:** Deterministically reconstructed the full 2,092-line main.py from the global conversation transcript logs after a git checkout command reverted it to the 790-line baseline. Resolved all syntax and indentation errors within the macro_worker and run_recovery_sequence methods. Verified compilation success with zero errors.

## 2026-07-03 - ลบฟีเจอร์ Loop และ Loop-Multi ออก
- **การเปลี่ยนแปลง:** นำคำสั่ง `[Loop]` และ `[Loop-Multi]` ออกจากตัวเลือกการตั้งค่าทั้งหมด (Macro และ Recovery) ตามความต้องการของผู้ใช้ เพื่อหลีกเลี่ยงความสับสนและให้ผู้ใช้หันไปใช้ `-- วนลูป (Loop) --` (คือ `[Loop-Control]`) แทน
- **การแก้ไขหลัก:** ปรับลดตัวเลือกใน combobox, ลบเงื่อนไขรับค่าจาก UI, ถอดลอจิกการวนลูปคลิกใน `macro_worker` และ `run_recovery_sequence`
- **แก้ไขข้อผิดพลาด:** กู้คืนเนื้อหาที่ถูกแก้ไขผิดพลาดจากเครื่องมือ replace อัตโนมัติกลับมาสมบูรณ์เรียบร้อยแล้วด้วย Python script

## 2026-07-03 - อัปเดตการทำงาน Loop-Control และหน้าล็อบบี้
- **อัปเดต Package Name:** เปลี่ยนค่าเริ่มต้นช่องชื่อแพ็กเกจเกมใน UI จาก `com.devsisters.gb` เป็น `com.devsisters.crg`
- **เพิ่มลอจิกมาโครกู้คืน:** เพิ่มระบบแปลคำสั่ง `[Loop-Control]`, `[Skip]` และ `[SkipNot]` เข้าไปในฟังก์ชัน `run_recovery_sequence` (ก่อนหน้านี้โค้ดไม่รู้จักคำสั่งเหล่านี้ ทำให้เวลาอยู่ในโหมดกู้คืนมันจะค้างรอ 10 วินาทีถึงจะไปสเต็ปถัดไป ซึ่งเป็นสาเหตุให้ Loop-Control ช้ามาก)
- **ปรับแต่งความเร็ว:** ลด Delay คงที่ของการประมวลผลคำสั่ง `[Loop-Control]` ลงเหลือ 0.05 วินาที ทำให้เวลามันสั่งกระโดดกลับ (Loop Jump) แทบจะเกิดขึ้นทันที ไม่มีอาการหน่วงค้าง
- **รวมปุ่ม Save/Load:** รวมการทำงานของปุ่ม Save และ Load ในหน้าต่างกู้คืน (Recovery) ให้เชื่อมต่อกับฟังก์ชันของหน้าต่างหลัก (Macro) แล้ว ส่งผลให้ไม่ว่าจะกดปุ่ม Save/Load จากหน้าต่างไหน ระบบก็จะบันทึกข้อมูลทุกอย่างไปพร้อมกันในไฟล์เดียว (ทั้ง steps, recovery_steps, timeout_mins, package_name, และ stuck_action)
- **ปรับแต่ง UI:** ลบปุ่มทดสอบที่ซ้ำซ้อนออก และลบตัวเลือก `stuck_action` (เมื่อภาพไม่มาตามเวลา) ออกจาก UI ทั้งหมด โดยตั้งค่าให้รันโฟลว์ "รีสตาร์ทเกม & เริ่มใหม่" แบบอัตโนมัติ 100% ทำให้ UI ดูสะอาดและใช้งานง่ายขึ้น
- **จัดระเบียบหน้าต่าง:** ย้ายส่วนควบคุม `🛡️ ระบบกันค้าง (Anti-Stuck Settings)` ทั้งบล็อก (ที่ใช้ตั้งเวลารอสูงสุดและใส่ชื่อแพ็กเกจเกม) จากหน้าต่าง Macro ไปรวมไว้ที่หน้าต่าง Recovery (หน้า 3) เพื่อให้การตั้งค่าเกี่ยวกับการกู้คืนระบบทั้งหมดรวมอยู่ในหน้าเดียวกันอย่างเป็นหมวดหมู่











