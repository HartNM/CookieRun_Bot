# AI Work History

This file tracks the changes and tasks performed by the AI on this project. 

## [2026-07-02]
- Created this `AI_HISTORY.md` file and configured `.agents/AGENTS.md` to track AI actions.
- Connected the Git repository (`https://github.com/HartNM/CookieRun_Bot.git`).
- Created a `main.py` Tkinter UI for a CookieRun ADB bot with `pure-python-adb` and OpenCV.
- Added ADB auto-download, global exception logging, and automatic resolution checks (requires 1080p).
- Built a complete Template Maker for cropping target images interactively and renaming them.
- Implemented a Macro Builder queue engine allowing `[Click]`, `[Wait]`, `[Skip-If]`, and `[Skip-IfNot]`.
- Implemented `[Spam-Wait]` for parallel background tapping of coordinates or secondary templates.
- Added dynamic minigame solving (`[Solve-Minigame]`) which isolates and clicks odd cards using OpenCV MSE.
- Added a full Anti-Stuck timeout and auto-recovery flow (restarting game and spamming to lobby).
- Implemented macro profile save/load (JSON) containing steps, timeouts, and package names.
- Added test buttons to verify package launching/killing and active app detection via `adb shell dumpsys`.

## [2026-07-03]
- Removed legacy `[Loop]` and `[Loop-Multi]` features to exclusively use the `[Loop-Control]` structure.
- Refactored `run_recovery_sequence` to correctly process loop controls with reduced delay latency (0.05s).
- Consolidated recovery options into a strict "Restart & Reload" flow for simplicity and moved settings to the Recovery tab.
- Replaced static `Lobby.png` checks with dynamic glob matching (`Lobby*.png`) to support multiple lobby variants.
- Integrated auto-closing of News popups (`Login Exit.png`) into the recovery sequence.
- Added live elapsed timers for recovery loops and live timeout countdowns for standard macro steps.
- Embedded minigame detection actively within the 45-second recovery loop to prevent blind-clicks.
- Refactored monolithic `main.py` (previously ~2000 lines) into modules to improve maintainability:
  - Extracted `CropWindow` to `ui_components.py`.
  - Extracted ADB and parsing utils to `utils.py`.
  - Extracted image processing (`do_template_match_by_name`, `solve_minigame_action`, `check_lobby_reached`) to `vision.py`.
  - Extracted popup dialogs to `ui_dialogs.py`.
  - Extracted JSON profile management to `config_manager.py`.
- Automated build pipeline rules: Created `CookieRun_Bot_Release.zip` containing the built `.exe`, `macros/`, and `templates/` on every successful PyInstaller build.
- Updated `.gitignore` to exclude `*.zip` release files.
