"""
Vision-Based Desktop Automation with Dynamic Icon Grounding
============================================================
1. Fetch 10 posts from JSONPlaceholder API (fallback to hardcoded)
2. For each post:
   a. Show desktop → Gemini vision grounds the Notepad icon → double-click
   b. Type post content, save as post_{id}.txt in Desktop/tjm-project
   c. Close Notepad (handle any unexpected pop-ups via vision)
   d. Repeat with a fresh screenshot for the next post
"""

import io
import json
import os
import subprocess
import time
from pathlib import Path

import mss
import pyautogui
import pyperclip
import pygetwindow as gw
from dotenv import load_dotenv
from openrouter import OpenRouter
from PIL import Image

load_dotenv()

client = OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"])
MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

SAVE_DIR = Path.home() / "Desktop" / "tjm-project"
SAVE_DIR.mkdir(parents=True, exist_ok=True)



# ── Screenshot ─────────────────────────────────────────────────────────────────

def take_screenshot() -> tuple[Image.Image, bytes]:
    """Capture full desktop. Returns (PIL Image resized to ≤1280px wide, JPEG bytes)."""
    with mss.MSS() as sct:
        raw = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if img.width > 1280:
        img = img.resize((1280, int(img.height * 1280 / img.width)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return img, buf.getvalue()


# ── Vision (OpenRouter) ────────────────────────────────────────────────────────

def ask_vision(image_bytes: bytes, question: str) -> str:
    """Send image + question to vision model via OpenRouter."""
    import base64
    image_b64 = base64.standard_b64encode(image_bytes).decode()
    try:
        response = client.chat.send(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": question},
                ],
            }],
            max_tokens=256,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        if "free-models-per-day" in str(e) or "TooManyRequests" in type(e).__name__:
            print("  [Vision] Daily free limit reached — add credits at openrouter.ai/credits")
        else:
            print(f"  [Vision] Error: {e}")
        return ""


def find_icon(description: str) -> tuple[int, int] | None:
    """
    Ask vision model to locate an icon/element on the desktop.
    Works for any icon regardless of position, theme, or background.
    Returns pixel (x, y) center coordinates, or None if not found.
    """
    img, image_bytes = take_screenshot()

    prompt = (
        f"Look at this Windows desktop screenshot. Find: {description}\n\n"
        "Reply with ONLY a JSON object, nothing else:\n"
        '  If found:   {"found": true, "x": 0.35, "y": 0.22}\n'
        '  If missing: {"found": false}\n\n'
        "x and y are the CENTER of the target as a FRACTION of image size "
        "(0.0 = left/top edge, 1.0 = right/bottom edge).\n"
        "Be precise — this will be used to click the exact center of the icon."
    )

    raw = ask_vision(image_bytes, prompt).strip("` \n").removeprefix("json").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [Vision] Could not parse JSON: {raw!r}")
        return None

    if not data.get("found"):
        print(f"  [Vision] '{description}' not found in screenshot")
        return None

    x = int(data["x"] * img.width)
    y = int(data["y"] * img.height)
    print(f"  [Vision] Found '{description}' at ({data['x']:.2f}, {data['y']:.2f}) → pixel ({x}, {y})")

    return x, y


def handle_popup() -> bool:
    """
    Ask vision model if any unexpected pop-up or dialog is visible.
    If yes, click its dismiss/OK/Close button automatically.
    Returns True if a pop-up was handled.
    """
    img, image_bytes = take_screenshot()

    prompt = (
        "Look at this Windows desktop screenshot.\n"
        "Is there any pop-up dialog, warning box, or modal window open "
        "(other than Notepad's main window)?\n\n"
        "Reply ONLY with JSON:\n"
        '  Pop-up present: {"popup": true, "button": "OK", "x": 0.5, "y": 0.6}\n'
        '  No pop-up:      {"popup": false}\n\n'
        "x and y are the CENTER of the button to click as fractions of image size.\n"
        "'button' is the label of the button you would click to dismiss it."
    )

    raw = ask_vision(image_bytes, prompt).strip("` \n").removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False

    if data.get("popup"):
        x = int(data["x"] * img.width)
        y = int(data["y"] * img.height)
        btn = data.get("button", "?")
        print(f"  [Vision] Pop-up detected — clicking '{btn}' at ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(0.5)
        return True

    return False


# ── Data ───────────────────────────────────────────────────────────────────────

def fetch_posts() -> list[dict]:
    import requests
    try:
        r = requests.get(
            "https://jsonplaceholder.typicode.com/posts",
            params={"_limit": 3},
            timeout=10,
        )
        r.raise_for_status()
        posts = r.json()
        print(f"Fetched {len(posts)} posts from JSONPlaceholder API")
        return posts
    except Exception as exc:
        print(f"JSONPlaceholder API unavailable ({exc.__class__.__name__}) — no posts to process")
        return []


# ── Notepad Automation ─────────────────────────────────────────────────────────

def open_notepad() -> bool:
    """
    Show desktop, ground the Notepad icon with Gemini, double-click it.
    Retries up to 3 times with 1s delay (as per task spec).
    Falls back to subprocess launch if vision grounding fails.
    """
    pyautogui.hotkey("win", "d")
    time.sleep(0.8)

    coords = None
    for attempt in range(1, 4):
        print(f"  Detection attempt {attempt}/3...")
        coords = find_icon("notepad.exe shortcut icon on the Windows desktop")
        if coords:
            break
        time.sleep(1)

    if coords:
        pyautogui.doubleClick(*coords)
        print(f"  Clicked Notepad at {coords}")
    else:
        print("  Icon not found after 3 attempts — launching Notepad directly")
        subprocess.Popen("notepad.exe")

    # Wait for Notepad window (up to 10s)
    deadline = time.time() + 10
    while time.time() < deadline:
        windows = gw.getWindowsWithTitle("Notepad")
        if windows:
            windows[0].activate()
            time.sleep(0.3)
            return True
        # Check for unexpected pop-up blocking launch
        handle_popup()
        time.sleep(0.5)

    return False


def write_and_save(title: str, body: str, post_id: int) -> Path:
    save_path = SAVE_DIR / f"post_{post_id}.txt"

    # Paste content (handles unicode safely)
    pyperclip.copy(f"Title: {title}\n\n{body}")
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)

    # Open Save As dialog and wait for it to fully render
    pyautogui.hotkey("ctrl", "shift", "s")
    time.sleep(2.0)

    # Focus the filename field explicitly (Alt+N moves focus to "File name:" box
    # in the standard Windows Save As dialog) then select-all and paste full path
    pyautogui.hotkey("alt", "n")
    time.sleep(0.2)
    pyperclip.copy(str(save_path))
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    pyautogui.press("enter")  # navigate to directory / confirm filename
    time.sleep(1.0)
    pyautogui.press("enter")  # confirm overwrite if file already exists
    time.sleep(0.5)

    # Windows 11 Notepad may show an encoding dialog ("Save as type" / encoding)
    # — dismiss it by pressing Enter (accepting the default UTF-8 encoding)
    windows = gw.getWindowsWithTitle("Notepad")
    if not windows:
        # No Notepad window means Save As succeeded; nothing more to do
        return save_path
    # Check for an encoding or extra confirmation dialog still open
    extra_dialogs = [w for w in gw.getAllWindows()
                     if w.title and w.title not in ("", "Notepad") and "Notepad" in w.title]
    if extra_dialogs:
        pyautogui.press("enter")
        time.sleep(0.5)

    return save_path


def close_notepad() -> None:
    pyautogui.hotkey("alt", "f4")
    time.sleep(1.2)

    # Primary: use the keyboard accelerator for "Don't Save".
    # Windows message-box buttons expose their underlined letter via Alt+<key>.
    # "Don't Save" → Alt+N (the 't' in "Don'T save" on older Notepad,
    # or the 'N' shortcut on Windows 11 Notepad's dialog).
    # We try both; only the active one will fire.
    pyautogui.hotkey("alt", "n")
    time.sleep(0.3)

    # Fallback: if the dialog is still up, use vision to click "Don't Save"
    windows_open = gw.getWindowsWithTitle("Notepad")
    if windows_open:
        img, image_bytes = take_screenshot()
        prompt = (
            "Look at this screenshot. Is there a Notepad 'Do you want to save' dialog visible?\n"
            "Reply ONLY with JSON:\n"
            '  Dialog present: {"dialog": true, "x": 0.5, "y": 0.55}\n'
            '  No dialog:      {"dialog": false}\n'
            "x and y are the center of the \"Don't Save\" or \"No\" button as fractions of image size."
        )
        raw = ask_vision(image_bytes, prompt).strip("` \n").removeprefix("json").strip()
        try:
            data = json.loads(raw)
            if data.get("dialog"):
                x = int(data["x"] * img.width)
                y = int(data["y"] * img.height)
                print(f"  [Vision] Save dialog detected — clicking Don't Save at ({x}, {y})")
                pyautogui.click(x, y)
                time.sleep(0.5)
        except json.JSONDecodeError:
            pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort

    posts = fetch_posts()
    ok = 0

    for post in posts:
        print(f"\n── Post {post['id']}: {post['title'][:55]} ──")

        if not open_notepad():
            print("  Notepad did not open — skipping this post")
            continue

        path = write_and_save(post["title"], post["body"], post["id"])
        print(f"  Saved → {path}")

        close_notepad()
        ok += 1
        time.sleep(0.5)

    print(f"\nDone. {ok}/{len(posts)} posts saved to {SAVE_DIR}")



if __name__ == "__main__":
    main()
