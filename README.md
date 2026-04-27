# ScreenSeeker — Vision-Based Desktop Automation

Fetches blog posts from a REST API, then uses a multimodal vision model to locate the Notepad icon on the Windows desktop, open it, type the post content, save each file, and close Notepad — all without hardcoded pixel coordinates.

## How it works

### 1. Fetch posts

`main.py` calls the [JSONPlaceholder](https://jsonplaceholder.typicode.com/posts) API for 3 sample posts. If the network is unavailable it falls back to a hardcoded list of 100 posts.

### 2. Vision grounding (ScreenSpot-Pro approach)

For every post the script:

1. Presses **Win + D** to show the desktop.
2. Takes a full-desktop screenshot with `mss`.
3. Sends the screenshot (JPEG, ≤1280px wide) and a natural-language description to a vision-language model via [OpenRouter](https://openrouter.ai):
   > *"Find: notepad.exe shortcut icon on the Windows desktop"*
4. The model replies with normalized `(x, y)` fractions for the icon center.
5. The script scales those fractions to pixel coordinates and double-clicks.

No template images, no OCR, no hardcoded positions — the VLM understands visual semantics and finds the target regardless of icon theme, desktop background, or screen resolution.

| Approach | Weakness |
|---|---|
| Template matching | Breaks on different icon themes/sizes |
| OCR | Fails on icon-only elements |
| Color/shape heuristics | Brittle on custom backgrounds |
| **VLM grounding** | Works on any icon, any layout |

### 3. Pop-up handling

A second vision call checks for unexpected dialogs (UAC prompts, encoding warnings) after each action and clicks the dismiss button — no prior knowledge of the dialog required.

### 4. Save & close

- Content is pasted via the clipboard to handle Unicode safely.
- **Ctrl + Shift + S** opens Save As; the full file path is typed into the filename field.
- **Alt + F4** closes Notepad; **Alt + N** dismisses the "Don't Save" dialog (file is already saved). A vision fallback fires if the keyboard shortcut doesn't catch the dialog.

### Output

Files are written to `%USERPROFILE%\Desktop\tjm-project\post_<id>.txt`.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10 or 11 | Tested on Windows 11 |
| Python 3.11+ | |
| [uv](https://docs.astral.sh/uv/) | `pip install uv` |
| Notepad shortcut on the Desktop | Right-click desktop → New → Shortcut → `notepad.exe` |
| OpenRouter API key | Free tier works — get one at [openrouter.ai](https://openrouter.ai) |

---

## Setup & run

```bash
# 1. Clone the repo
git clone https://github.com/michaelraoof/screen-tjm.git
cd screen-tjm

# 2. Add your OpenRouter key
echo OPENROUTER_API_KEY=sk-or-... > .env

# 3. Install dependencies (uv resolves the lockfile automatically)
uv sync

# 4. Run
uv run main.py
```

> **Failsafe:** move your mouse to the top-left corner of the screen at any time to abort the script immediately (`pyautogui.FAILSAFE = True`).

---

## Project structure

```
screen-tjm/
├── main.py          # All logic: vision grounding, Notepad automation, data fetching
├── pyproject.toml   # Dependencies & build config (uv / hatchling)
├── uv.lock          # Pinned dependency tree
└── .env             # OPENROUTER_API_KEY — never committed
```

---

## Error handling

| Scenario | Behavior |
|---|---|
| Icon not found | 3 retries with 1 s delay, then falls back to `subprocess.Popen("notepad.exe")` |
| Notepad doesn't open within 10 s | Skips the post, continues with the next one |
| API unavailable | Falls back to 100 hardcoded sample posts |
| File already exists | Automatically confirms the overwrite dialog |
| Save dialog on close | Vision detects and clicks "Don't Save" (file is already saved) |
| Per-post isolation | A failure on post N does not affect post N+1 |

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Get one at [openrouter.ai](https://openrouter.ai) |

---

## Model

Default: `nvidia/nemotron-nano-12b-v2-vl:free` (free tier on OpenRouter).  
To switch models, change the `MODEL` constant at the top of `main.py`.
