"""MCP server: send a job to the open Gemini desktop window and return its reply.

The Gemini app exposes no UI-Automation tree for its content, so this drives it
like a person: new chat -> paste prompt -> Enter -> select-all/copy until stable.
shortcut: needs the Gemini window open and the screen unlocked; the machine's
keyboard/mouse are used for a few seconds per job. Upgrade to the Gemini API if
you need headless/parallel jobs.
"""
import ctypes
import time

import pyperclip
from PIL import ImageChops, ImageStat
from mcp.server.mcpserver import MCPServer
from pywinauto import Desktop, mouse
from pywinauto.keyboard import send_keys

ctypes.windll.shcore.SetProcessDpiAwareness(2)  # keep rect + click coords consistent

mcp = MCPServer("gemini-desktop")

FOOTER = "Gemini is AI and can make mistakes"


def _window():
    w = Desktop(backend="uia").window(title="Gemini", class_name="Chrome_WidgetWin_1")
    w.wait("exists", timeout=10)
    if w.get_show_state() == 2:  # minimized
        w.restore()
    w.set_focus()
    return w


def _click(w, fx, fy):
    r = w.rectangle()
    mouse.click(coords=(int(r.left + fx * r.width()), int(r.top + fy * r.height())))


def _grab(w):
    """Click the chat area, select all, copy; return the page text."""
    _click(w, 0.62, 0.30)
    pyperclip.copy("")
    send_keys("^a^c")
    time.sleep(0.4)
    return pyperclip.paste()


def _extract(text, prompt):
    # Page text = sidebar + chat + input box. Keep what follows our prompt.
    p = prompt.strip()
    i = text.rfind(p[:80])
    if i != -1:
        text = text[i + len(p):] if len(p) <= 80 else text[i:].split("\n", 1)[-1]
    j = text.find(FOOTER)
    if j != -1:
        text = text[:j]
    return text.replace("Ask Gemini", "").strip()


@mcp.tool()
def ask_gemini(prompt: str, timeout_seconds: int = 120, new_chat: bool = True) -> str:
    """Send a job to the open Gemini desktop window and return Gemini's reply.

    new_chat=True starts a fresh chat first (recommended: keeps replies clean).
    The reply is read by copying the page text, so it may include light UI noise.
    """
    w = _window()
    if new_chat:
        send_keys("^+o")
        time.sleep(1.5)
    else:
        _click(w, 0.62, 0.86)
    pyperclip.copy(prompt)
    send_keys("^v")
    time.sleep(0.5)
    send_keys("{ENTER}")

    # Clicking while Gemini generates stops the reply, so wait passively: the chat
    # area keeps changing (streaming/spinner) until done, then stays identical.
    deadline = time.time() + timeout_seconds
    last, same = None, 0
    time.sleep(4)
    while time.time() < deadline:
        r = w.rectangle()
        snap = w.capture_as_image().convert("L").crop(
            (int(r.width() * 0.4), int(r.height() * 0.1), r.width(), int(r.height() * 0.78))
        )
        # translucent window shows the animated wallpaper: ~0.02 noise, so use a threshold
        quiet = last is not None and ImageStat.Stat(ImageChops.difference(snap, last)).mean[0] < 0.1
        same = same + 1 if quiet else 0
        last = snap
        if same >= 3:  # ~6s with no visual change
            return _extract(_grab(w), prompt)
        time.sleep(2)
    return "TIMEOUT after %ss. Partial: %s" % (timeout_seconds, _extract(_grab(w), prompt))


if __name__ == "__main__":
    mcp.run()
