"""
CodexSwitch for Windows — System tray app
Toggles Codex between DeepSeek and default Claude via Moon Bridge proxy.
"""
import sys, os, json, subprocess, threading, time, shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import pystray
from PIL import Image

# ── Paths ─────────────────────────────────────────────────────────────────────
APP_DIR    = Path.home() / ".codex-switch"
SETTINGS   = APP_DIR / "settings.json"
CODEX_HOME = Path.home() / ".codex"
CONFIG_YML = APP_DIR / "config.yml"
BACKUP     = APP_DIR / "config.toml.backup"
PORT       = "38440"

# moonbridge.exe lives next to this script (or frozen exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
MOONBRIDGE = BASE_DIR / "moonbridge.exe"

# ── Settings ──────────────────────────────────────────────────────────────────
def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {"api_key": "", "model": "deepseek-v4-pro"}

def save_settings(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")

# ── Moon Bridge config ────────────────────────────────────────────────────────
def write_moonbridge_config(api_key, model):
    display = "DeepSeek V4 Flash" if model == "deepseek-v4-flash" else "DeepSeek V4 Pro"
    yaml = f"""\
mode: "Transform"

server:
  addr: "127.0.0.1:{PORT}"

defaults:
  model: "{model}"

models:
  {model}:
    context_window: 1000000
    max_output_tokens: 384000
    display_name: "{display}"
    default_reasoning_level: "high"
    supported_reasoning_levels:
      - effort: "high"
        description: "High reasoning effort"
      - effort: "xhigh"
        description: "Extra high reasoning effort"
    supports_reasoning_summaries: true
    default_reasoning_summary: "auto"
    extensions:
      deepseek_v4:
        enabled: true

providers:
  deepseek:
    base_url: "https://api.deepseek.com/anthropic"
    api_key: "{api_key}"
    version: "2023-06-01"
    user_agent: "moonbridge/1.0"
    offers:
      - model: {model}

routes:
  {model}:
    model: {model}
    provider: deepseek
"""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_YML.write_text(yaml, encoding="utf-8")

def is_port_open():
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", int(PORT)), timeout=0.3)
        s.close()
        return True
    except Exception:
        return False

def shell(*args):
    r = subprocess.run(list(args), capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return r.stdout.strip()

# ── App state ─────────────────────────────────────────────────────────────────
class State:
    def __init__(self):
        s = load_settings()
        self.api_key = s.get("api_key", "")
        self.model   = s.get("model", "deepseek-v4-pro")
        self.enabled = False
        self.status  = "已停止"
        self.process = None

state = State()

# ── Start / Stop ──────────────────────────────────────────────────────────────
def start_deepseek(on_done):
    def run():
        try:
            write_moonbridge_config(state.api_key, state.model)
            # Backup original Codex config
            codex_cfg = CODEX_HOME / "config.toml"
            if codex_cfg.exists() and not BACKUP.exists():
                shutil.copy2(codex_cfg, BACKUP)

            proc = subprocess.Popen(
                [str(MOONBRIDGE), "--config", str(CONFIG_YML)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            state.process = proc

            # Wait for port
            for _ in range(50):
                time.sleep(0.1)
                if is_port_open():
                    break
            else:
                proc.terminate()
                state.process = None
                state.enabled = False
                state.status = "启动超时"
                on_done(False)
                return

            # Generate Codex config
            mb = str(MOONBRIDGE)
            cfg = str(CONFIG_YML)
            model_id = shell(mb, "--config", cfg, "--print-codex-model")
            toml = shell(mb, "--config", cfg,
                         "--print-codex-config", model_id,
                         "--codex-base-url", f"http://127.0.0.1:{PORT}/v1",
                         "--codex-home", str(CODEX_HOME))

            display = "DeepSeek V4 Flash" if state.model == "deepseek-v4-flash" else "DeepSeek V4 Pro"
            toml = (toml
                .replace('model_provider = "moonbridge"', f'model_provider = "{state.model}"')
                .replace('[model_providers.moonbridge]',  f'[model_providers.{state.model}]')
                .replace('name = "Moon Bridge"',          f'name = "{display}"'))

            CODEX_HOME.mkdir(parents=True, exist_ok=True)
            (CODEX_HOME / "config.toml").write_text(toml, encoding="utf-8")

            state.status = "运行中"
            on_done(True)
        except Exception as e:
            state.enabled = False
            state.status = f"失败: {e}"
            on_done(False)
    threading.Thread(target=run, daemon=True).start()

def stop_deepseek():
    if state.process:
        state.process.terminate()
        state.process = None
    codex_cfg = CODEX_HOME / "config.toml"
    if BACKUP.exists():
        if codex_cfg.exists():
            codex_cfg.unlink()
        shutil.copy2(BACKUP, codex_cfg)
        BACKUP.unlink()
    elif codex_cfg.exists():
        codex_cfg.unlink()
    state.status = "已停止"

# ── Tray icon image ───────────────────────────────────────────────────────────
def make_tray_icon(active=False):
    icon_path = BASE_DIR / "icon.png"
    if icon_path.exists():
        img = Image.open(icon_path).resize((64, 64))
    else:
        # Fallback: draw a simple lightning bolt
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        bg = (40, 180, 100) if active else (30, 30, 30)
        d.ellipse([0, 0, 63, 63], fill=bg)
        pts = [(32,6),(20,34),(30,34),(22,58),(44,28),(33,28),(38,6)]
        d.polygon(pts, fill=(255, 255, 255))
    return img

# ── Settings window ───────────────────────────────────────────────────────────
_win = None

def open_settings_window(icon=None, item=None):
    global _win
    if _win and _win.winfo_exists():
        _win.lift()
        _win.focus_force()
        return

    win = tk.Tk()
    win.title("CodexSwitch")
    win.geometry("320x300")
    win.resizable(False, False)
    win.configure(bg="#1e1e2e")
    _win = win

    # Try to set window icon
    icon_path = BASE_DIR / "icon.png"
    if icon_path.exists():
        try:
            win.iconphoto(True, tk.PhotoImage(file=str(icon_path)))
        except Exception:
            pass

    FONT  = ("Segoe UI", 10)
    FONT_S = ("Segoe UI", 9)
    BG, FG = "#1e1e2e", "#cdd6f4"
    BLUE   = "#89b4fa"
    GREEN  = "#a6e3a1"
    SURF   = "#313244"

    pad = {"padx": 16, "pady": 6}

    # Header
    tk.Label(win, text="⚡  CodexSwitch", font=("Segoe UI", 13, "bold"),
             bg=BG, fg=BLUE).pack(anchor="w", padx=16, pady=(14, 2))
    ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=4)

    # API Key
    tk.Label(win, text="DeepSeek API Key", font=FONT_S, bg=BG, fg="#a6adc8").pack(anchor="w", **pad)
    key_var = tk.StringVar(value=state.api_key)
    key_entry = tk.Entry(win, textvariable=key_var, show="•", font=FONT,
                         bg=SURF, fg=FG, insertbackground=FG,
                         relief="flat", bd=0)
    key_entry.pack(fill="x", padx=16, ipady=5)

    # Model
    tk.Label(win, text="模型", font=FONT_S, bg=BG, fg="#a6adc8").pack(anchor="w", **pad)
    model_var = tk.StringVar(value=state.model)
    model_cb = ttk.Combobox(win, textvariable=model_var, state="readonly", font=FONT,
                             values=["deepseek-v4-pro", "deepseek-v4-flash"])
    model_cb.pack(fill="x", padx=16)

    ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=8)

    # Status row
    status_frame = tk.Frame(win, bg=BG)
    status_frame.pack(fill="x", padx=16)
    tk.Label(status_frame, text="DeepSeek", font=FONT, bg=BG, fg=FG).pack(side="left")
    status_lbl = tk.Label(status_frame, text=state.status, font=FONT_S,
                          bg=BG, fg=GREEN if state.enabled else "#6c7086")
    status_lbl.pack(side="left", padx=(8, 0))

    toggle_var = tk.BooleanVar(value=state.enabled)
    toggle_btn = tk.Button(status_frame, text="", font=FONT, bd=0, cursor="hand2",
                           activebackground=BG)
    toggle_btn.pack(side="right")

    def update_ui():
        col = GREEN if state.enabled else "#6c7086"
        status_lbl.config(text=state.status, fg=col)
        toggle_btn.config(text="● ON " if state.enabled else "○ OFF",
                          bg="#2a4d3a" if state.enabled else SURF, fg=GREEN if state.enabled else "#6c7086")
        key_entry.config(state="disabled" if state.enabled else "normal")
        model_cb.config(state="disabled" if state.enabled else "readonly")
        # Update tray icon
        if tray_icon:
            tray_icon.icon = make_tray_icon(state.enabled)

    def on_toggle():
        if state.enabled:
            # Turn off
            state.enabled = False
            state.status = "停止中..."
            update_ui()
            def do_stop():
                stop_deepseek()
                win.after(0, update_ui)
            threading.Thread(target=do_stop, daemon=True).start()
        else:
            # Turn on
            api = key_var.get().strip()
            if not api:
                status_lbl.config(text="请填写 API Key", fg="#f38ba8")
                return
            state.api_key = api
            state.model = model_var.get()
            save_settings({"api_key": state.api_key, "model": state.model})
            state.enabled = True
            state.status = "启动中..."
            update_ui()
            def on_done(ok):
                win.after(0, update_ui)
            start_deepseek(on_done)

    toggle_btn.config(command=on_toggle)
    update_ui()
    win.mainloop()

# ── Tray setup ────────────────────────────────────────────────────────────────
tray_icon = None

def run_tray():
    global tray_icon

    def on_open(icon, item):
        threading.Thread(target=open_settings_window, daemon=True).start()

    def on_quit(icon, item):
        save_settings({"api_key": state.api_key, "model": state.model})
        if state.enabled:
            stop_deepseek()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("设置", on_open, default=True),
        pystray.MenuItem("退出 CodexSwitch", on_quit),
    )
    tray_icon = pystray.Icon(
        "CodexSwitch",
        make_tray_icon(False),
        "CodexSwitch",
        menu,
    )
    tray_icon.run()

if __name__ == "__main__":
    run_tray()
