# Project Rules

## AI History Tracking
- **Read History:** Always read `AI_HISTORY.md` in the project root at the start of any new session or task to understand the context and past actions.
- **Update History:** Update `AI_HISTORY.md` when you finish a task, summarizing what you did, the date, and any important notes for future reference. Use a chronological format.
- **Language:** Always write history entries in English.

## Execution Rules
- **No Automatic Build:** Do NOT build/package the application (using PyInstaller, etc.) automatically. Wait for the user to explicitly request a build.
- **No Automatic Git:** Do NOT run git commands (add, commit, push, etc.) automatically. Wait for the user to explicitly request git actions.
- **Post-Build Process:** After building the application (e.g., with PyInstaller), you MUST always move the resulting `.exe` file from the `dist` directory to the project root directory. Then, create a zip file (e.g., `CookieRun_Bot_Release.zip`) containing the `.exe`, the `macros` folder, and the `templates` folder.
