# gemini-bridge

A tiny MCP server that sends a prompt to the open **Gemini desktop app** and returns its reply. The app exposes no API, so the script drives the window like a person would: new chat, paste prompt, wait for the answer, copy it.

Limits: Windows only, the Gemini window must be open and the screen unlocked; it uses your keyboard and mouse for a few seconds per job. For headless or parallel use, call the Gemini API instead.

```
pip install pyperclip pillow mcp pywinauto
python gemini_desktop_mcp.py
```
