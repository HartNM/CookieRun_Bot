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
