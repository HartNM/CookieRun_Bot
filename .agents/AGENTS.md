# Project Rules

## Context Management
- **Read Context:** Always read `context.md` in the project root at the start of any new session or task to understand the full project architecture, module responsibilities, macro step formats, and UI layout before making any changes.
- **Update Context:** After completing any task that involves a significant change (new feature, refactor, UI change, new module, changed step format, etc.), update the relevant sections of `context.md` to reflect the current state of the project.
- **Language:** All content written to `context.md` and `AGENTS.md` MUST be in English only. No Thai or other languages.

## Code Editing Rules
- **Minimal File Reading:** Before reading any file, explicitly state which files you need to read and why. Do NOT mass-read files on your own. Only read files that are strictly necessary for the current task.

## Response Style
- **Compact & Structured:** Always respond in a concise, well-structured format. Use bullet points, short sentences, and headers where appropriate. Avoid long paragraphs or unnecessary explanation.

## Execution Rules
- **No Automatic Build:** Do NOT build/package the application (using PyInstaller, etc.) automatically. Wait for the user to explicitly request a build.
- **No Automatic Git:** Do NOT run git commands (add, commit, push, etc.) automatically. Wait for the user to explicitly request git actions.
- **Post-Build Process:** After building the application (e.g., with PyInstaller), you MUST always move the resulting `.exe` file from the `dist` directory to the project root directory. Then, create a zip file (e.g., `CookieRun_Bot_Release.zip`) containing the `.exe`, the `macros` folder, and the `templates` folder.
