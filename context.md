# CookieRun Bot — Project Context

## Overview
A Python Tkinter desktop application that automates the **CookieRun: Kingdom** mobile game using ADB (Android Debug Bridge) and OpenCV template matching. It connects to an emulator (e.g., MuMu Player) via `pure-python-adb`, takes screenshots, finds UI elements by image matching, and dispatches tap commands.

---

## Tech Stack
| Layer | Technology |
|-------|------------|
| UI | Python `tkinter` + `ttk` |
| ADB Bridge | `pure-python-adb` (`ppadb`) |
| Image Matching | `opencv-python` (`cv2`), `numpy` |
| Image Handling | `Pillow` (`PIL`) |
| Config/Profile | `json` |
| Logging | Python `logging` → `bot_error.log`, `bot_run.log` |
| Build | PyInstaller (manual only, never automatic) |

---

## File Structure

```
CookieRun_Bot/
├── main.py              # Entry point + CookieRunBotUI (wire-up only, ~170 lines)
├── tab_templates.py     # TemplatesTab — UI and logic for Templates tab (Tab 1)
├── tab_macro.py         # MacroTab — UI and logic for Macro Builder tab (Tab 2)
├── tab_recovery.py      # RecoveryTab — UI and logic for Recovery tab (Tab 3)
├── macro_engine.py      # macro_worker(), run_recovery_sequence(), log_bot_activity()
├── adb_connect.py       # connect_adb() — port scanning and device connection
├── vision.py            # Image processing (template matching, minigame solver, lobby check)
├── ui_components.py     # CropWindow — interactive screenshot crop tool
├── ui_dialogs.py        # Popup dialogs (spam wait details, loop control, etc.)
├── config_manager.py    # Save/Load macro profiles as JSON
├── utils.py             # ADB server init, package name parsing helpers
├── templates/           # PNG template images captured by the user
│   └── config.json      # Optional ROI (Region of Interest) data per template
├── macros/              # Saved macro profiles (.json)
├── stuck_screenshots/   # Auto-saved screenshots when Anti-Stuck timeout fires
├── bot_error.log        # Crash / exception log
├── bot_run.log          # Activity log written during macro execution
└── .agents/AGENTS.md    # AI agent rules for this project
```

---

## UI Tabs

### 1. 🛠️ จัดการภาพต้นแบบ (Templates)
- **Capture & Crop** — takes a full screenshot from ADB or imports a local screenshot file (e.g. from `stuck_screenshots/`), opens `CropWindow` for the user to drag-select a region, and saves the crop as a `.png` in `templates/`.
- **Rename / Delete** — rename or remove saved templates. Renaming a template automatically updates all of its occurrences in active UI listboxes (Macro/Recovery tabs) and all profile JSON files in the `macros/` directory.
- **Test Find** — runs a one-shot template match against the current screen and shows the confidence score.
- **Find & Click** — runs a match and taps the found location.

### 2. 🚀 สร้างบอทมาโคร (Macro)
- Builds an ordered list (Listbox) of steps that the bot will execute sequentially, looping indefinitely.
- **"เลือกปุ่มที่เซฟไว้"** combobox — selects the template/action. Contains both image names from `templates/` and special action entries (see below).
- **"Action"** combobox — shown only when a template image is selected (hidden for special actions).
- **"ดีเลย์แคปภาพ" / "ดีเลย์เปลี่ยนสเต็ป"** — global configurations for screenshot check rate (default 1000ms) and post-action transition delay (default 1000ms).
- Supports drag-and-drop reordering, move up/down, edit, delete.
- Save/Load profiles via `config_manager.py`.

### 3. 🔄 กู้คืนเกม (Recovery)
- Identical layout to the Macro tab but defines the **recovery sequence** — steps run automatically when Anti-Stuck timeout fires.
- Settings: max timeout (minutes), game package name (default `com.devsisters.crg`).

---

## Special Action Entries in "เลือกปุ่มที่เซฟไว้"
These entries appear at the **top** of the combo and do **not** need an Action dropdown:

| Entry Label | Inserted Step Token | Behavior |
|-------------|--------------------|-|
| `-- เพิ่มเวลาหน่วง (Delay) --` | `[Delay] {ms}ms` | Pauses execution for N milliseconds |
| `-- แก้ไขมินิเกม (Solve Minigame) --` | `[Solve-Minigame] {img}` | Auto-solves the minigame using MSE card detection |
| `-- วนลูป (Loop) --` | `[Loop-Control:{N}] Duration:{ms}ms` or `[Loop-Control:{N}] Count:{times}` | วนลูป N สเต็ปล่าสุดซ้ำ — ตามระยะเวลา (Duration) หรือตามจำนวนรอบ (Count) |
| `-- ปิดแอปเกม (Force Stop) --` | `[Force-Stop-Game]` | Runs `adb shell am force-stop {package}` |
| `-- เปิดแอปเกม (Launch Game) --` | `[Launch-Game]` | Runs `adb shell monkey` to launch the game |
| `-- หยุดมาโคร (Break) --` | `[Break]` | Immediately stops the macro when selected template is found |
| `-- พิมพ์ข้อความ (Type Text) --` | `[Type-Text] {text}` | Types text via `adb shell input text` (spaces escaped as `%s`) |
| `-- กด Enter --` | `[Press-Enter]` | Sends Enter key via `adb shell input keyevent 66` |
| `-- ลากหน้าจอ (Swipe) --` | `[Swipe] {x1},{y1} -> {x2},{y2} {ms}ms` or `[Swipe-Img] {img} Direction:{dir} {ms}ms` | Performs a swipe gesture either via custom coordinates or dynamically inside a matched template area (e.g. from top edge to bottom edge) |

---

## Action Types (for template-based steps)
These appear in the **"Action"** combobox when a template image is selected:

| Action Token | Format Example | Behavior |
|---|---|---|
| `[Click]` | `[Click] Button.png` | Wait for image (using saved ROI/coordinates) → tap it |
| `[Wait]` | `[Wait] Screen.png` | Wait for image → do NOT tap, just proceed |
| `[Full-Click]` | `[Full-Click] Button.png` | Wait for image (scanning full screen, ignoring saved ROI) → tap it |
| `[Spam-Wait]` | `[Spam-Wait] [Tap.png] [S:600] [R:200] Target.png` | Spam-tap a button in background, wait for Target image to appear (no click on target). Supports multiple targets separated by `\|` (e.g., `T1.png\|T2.png\|T3.png`) — any match triggers success |
| `[Spam-Click]` | `[Spam-Click] [Tap.png] [S:600] [R:200] Target.png` | Same as Spam-Wait but also clicks the target image when found. Also supports multiple targets with `\|` |
| `[Skip-If]` | `[Skip:2] Image.png` | If image found (within saved ROI) → skip next N steps |
| `[Skip-IfNot]` | `[SkipNot:2] Image.png` | If image NOT found (within saved ROI) → skip next N steps |
| `[Full-Skip-If]` | `[FullSkip:2] Image.png` | If image found (scanning full screen, ignoring saved ROI) → skip next N steps |
| `[Full-Skip-IfNot]` | `[FullSkipNot:2] Image.png` | If image NOT found (scanning full screen, ignoring saved ROI) → skip next N steps |
| `[Break]` | `[Break] Image.png` | If image found → stop macro entirely |

### Spam-Wait / Spam-Click Parameter Syntax
```
[Spam-Wait] [{spam_target}] [S:{interval_ms}] [R:{random_ms}] {wait_template1}|{wait_template2}|...
```
- `spam_target` — a `.png` template name or raw `x,y` coordinate
- `S:` — base interval between taps in milliseconds
- `R:` — random additional delay (0 to R ms) added per tap to avoid detection
- `wait_templates` — one or more `.png` names separated by `|` (up to 3). Bot stops waiting as soon as **any** image is found.

*(Note: The default post-action delay for all generic Click, Wait, and Spam steps is 0 ms. If you need custom delays, insert a standalone `[Delay] {ms}ms` step).*

---

## Macro Execution Engine (main.py)
- Runs in a **background thread** (`threading.Thread`).
- Loops the entire step list indefinitely (`loop_count`).
- For each step:
  1. Parses the step token string to extract `action`, `spam_target`, `spam_interval`, `spam_random`, `delay_ms`, `step_name`.
  2. Dispatches to appropriate handler (Delay, Loop-Control, Solve-Minigame, Check-Lobby, Force-Stop-Game, Launch-Game, Skip-If, SkipNot, Click/Wait/Spam, Type-Text, Press-Enter).
  3. For image-waiting steps (including Click, Wait, Spam-Wait, and Spam-Click): polls `do_template_match_by_name()` every ~1s until target image is found or timeout fires.
  4. On **timeout**: triggers `run_recovery_sequence()`, resets step index to 0.

### Anti-Stuck System
- Timeout configured in minutes in the Recovery tab.
- When a step takes longer than the timeout:
  1. Saves a screenshot to `stuck_screenshots/`.
  2. Runs the recovery macro steps (Force-Stop → Launch-Game → wait for Lobby, etc.).
  3. Restarts the main macro from step 0.

---

## Image Matching (vision.py)
- Uses `cv2.TM_CCOEFF_NORMED`. Match threshold = **0.8**.
- Supports **ROI** (Region of Interest) from `templates/config.json` — search is restricted to a padded bounding box of the original crop position, speeding up matching on large screens.
- `do_template_match_by_name(device, name)` — returns `(max_val, (center_x, center_y))`.
- `solve_minigame_action(...)` — takes a screenshot, crops 6 card regions at hardcoded 1920×1080 coords, computes MSE between each pair, clicks the 2 most-different cards (max 10 attempts).

---

## Macro Profile Format (JSON)
Saved by `config_manager.py`:
```json
{
    "steps": ["[Click] Button.png", "[Wait] Screen.png"],
    "recovery_steps": ["[Force-Stop-Game]", "[Launch-Game]", "[Check-Lobby]"],
    "timeout_mins": 5,
    "package_name": "com.devsisters.crg",
    "screencap_delay_ms": 1000,
    "post_step_delay_ms": 1000
}
```

---

## Key Conventions
- Template images are always `.png`, stored in `templates/`.
- The game package is `com.devsisters.crg` by default.
- ADB is auto-downloaded if missing (platform-tools zip from Google).
- Resolution check: warns if device is not 1080p (matching still works but minigame solver assumes 1920×1080).
- All UI updates from background threads use `self.root.after(0, lambda: ...)`.
- `self.macro_running` is the global stop flag; setting it to `False` from any thread stops the macro.
