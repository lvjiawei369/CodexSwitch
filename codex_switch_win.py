"""
CodexSwitch for Windows — System tray app
Toggles Codex between DeepSeek and default Claude via Moon Bridge proxy.
"""
import sys, os, json, subprocess, threading, time, shutil, urllib.request
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

# PyInstaller single-file: bundled files are extracted to sys._MEIPASS at runtime
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)          # temp extraction dir
    EXE_DIR  = Path(sys.executable).parent # dir where the .exe lives (for icon)
else:
    BASE_DIR = Path(__file__).parent
    EXE_DIR  = BASE_DIR

def _ensure_moonbridge() -> Path:
    """Copy moonbridge.exe to a stable AppData location and keep it up-to-date.

    _MEIPASS is a fresh temp folder on every launch — AV quarantines files there
    aggressively.  AppData\\Local\\CodexSwitch persists across restarts so the binary
    lives at a predictable, whitelistable path.  We also re-copy when the bundled
    size differs (app update) and retry if AV briefly locks the file during scanning.
    """
    appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    persist_dir = appdata / "CodexSwitch"
    persist_mb  = persist_dir / "moonbridge.exe"

    # Find the bundled source (prefer _MEIPASS, fall back to beside the .exe)
    src = next(
        (p for p in [BASE_DIR / "moonbridge.exe", EXE_DIR / "moonbridge.exe"] if p.exists()),
        None,
    )

    # Decide whether to (re-)copy: missing OR bundled size changed (new app version)
    needs_copy = not persist_mb.exists()
    if not needs_copy and src:
        try:
            needs_copy = persist_mb.stat().st_size != src.stat().st_size
        except OSError:
            needs_copy = True

    if needs_copy and src:
        persist_dir.mkdir(parents=True, exist_ok=True)
        # Retry up to 4 times — AV may briefly lock the file while scanning _MEIPASS
        for attempt in range(4):
            try:
                shutil.copy2(src, persist_mb)
                # Verify copy landed intact
                if persist_mb.stat().st_size == src.stat().st_size:
                    break
            except Exception:
                pass
            if attempt < 3:
                time.sleep(0.5)

    return persist_mb

_MB_DOWNLOAD_URL = (
    "https://github.com/lvjiawei369/CodexSwitch/releases/latest/download/moonbridge.exe"
)

def _download_moonbridge(dest: Path, on_status=None) -> bool:
    """Download moonbridge.exe from the latest GitHub Release into dest.
    on_status(msg: str) is called with progress text so the UI can show it.
    Returns True on success.
    """
    tmp = dest.with_suffix(".tmp")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if on_status:
            on_status("正在下载 moonbridge.exe...")

        def _hook(count, block, total):
            if on_status and total > 0:
                pct = min(100, count * block * 100 // total)
                on_status(f"下载中... {pct}%")

        urllib.request.urlretrieve(_MB_DOWNLOAD_URL, tmp, _hook)

        # Verify the download is a real Windows PE (starts with "MZ")
        with open(tmp, "rb") as f:
            magic = f.read(2)
        if magic != b"MZ":
            tmp.unlink(missing_ok=True)
            if on_status:
                on_status("下载文件损坏，请手动获取 moonbridge.exe")
            return False

        tmp.replace(dest)
        if on_status:
            on_status("下载完成")
        return True
    except Exception as e:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        if on_status:
            on_status(f"下载失败: {e}")
        return False

MOONBRIDGE = _ensure_moonbridge()

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
def _yaml_str(s: str) -> str:
    """Wrap s in YAML single-quotes (safe for any content; only ' needs escaping)."""
    return "'" + s.replace("'", "''") + "'"

def write_moonbridge_config(api_key, model):
    display = "DeepSeek V4 Flash" if model == "deepseek-v4-flash" else "DeepSeek V4 Pro"
    safe_key = _yaml_str(api_key)
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
    supports_reasoning_summaries: true
    default_reasoning_summary: "auto"
    extensions:
      deepseek_v4:
        enabled: true

providers:
  deepseek:
    base_url: "https://api.deepseek.com/anthropic"
    api_key: {safe_key}
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
    CONFIG_YML.write_text(yaml, encoding="utf-8", newline="\n")

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

def _strip_model_keys(toml_text: str) -> str:
    """Remove root-level `model` / `model_provider` assignments from a config.toml.

    Codex saves the last-selected model (e.g. gpt-5.5) at the top of config.toml.
    When we append the user's original config to our generated one, that line would
    override the deepseek model and cause '404 unknown model'.  Only root-table
    lines (before the first [section] header) are stripped; everything else —
    MCP servers, notify, plugins — is kept verbatim."""
    out, in_root = [], True
    for line in toml_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("["):
            in_root = False
        if in_root:
            key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
            if key in ("model", "model_provider"):
                continue
        out.append(line)
    return "\n".join(out)


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
LOG_FILE = APP_DIR / "moonbridge.log"

# Map known upstream error signatures (matched case-insensitively) to plain-language
# Chinese hints.  moonbridge only tells Codex "502 Bad Gateway: Unknown error";
# the real cause lives in moonbridge.log, which we surface in the panel instead.
_ERROR_HINTS = [
    ("insufficient balance",  "DeepSeek 余额不足，请先充值"),
    ("402",                   "DeepSeek 余额不足，请先充值"),
    ("401",                   "API Key 无效或已失效，请检查"),
    ("authentication",        "API Key 无效或已失效，请检查"),
    ("invalid api key",       "API Key 无效或已失效，请检查"),
    ("429",                   "请求过于频繁(限流)，请稍后再试"),
    ("rate limit",            "请求过于频繁(限流)，请稍后再试"),
    ("timeout",               "连接 DeepSeek 超时，请尝试关闭 VPN/代理"),
    ("deadline exceeded",     "连接 DeepSeek 超时，请尝试关闭 VPN/代理"),
    ("no such host",          "无法解析 DeepSeek 域名，请尝试关闭 VPN/代理"),
    ("connection refused",    "无法连接 DeepSeek，请尝试关闭 VPN/代理"),
    ("connection reset",      "连接被重置，请尝试关闭 VPN/代理"),
    ("dial tcp",              "无法连接 DeepSeek，请尝试关闭 VPN/代理"),
    ("eof",                   "上游连接中断，请尝试关闭 VPN/代理后重试"),
]

# Benign log lines that contain an `error=`/`upstream=` field but are NOT failures
# (config notices and normal per-request routing logs).
_BENIGN = ("config_store", "持久化", "persistence")

# HTTP/server failure markers.  The generic fallback fires only when one of these
# appears *together with* an explicit "error" token, so normal routing logs like
# `model=... provider=deepseek upstream=api.deepseek.com` are never flagged.
_STRONG_FAIL = ("502", "503", "500", "bad gateway", "panic", "fatal", "status 5")

def _hint_for(line: str):
    low = line.lower()
    if any(b in low for b in _BENIGN):
        return None
    # Known, specifically-handled causes always win
    for sig, hint in _ERROR_HINTS:
        if sig in low:
            return hint
    # Generic fallback: require both an explicit error token AND a failure marker
    if ("error" in low or "fail" in low) and any(k in low for k in _STRONG_FAIL):
        return "上游错误: " + line.strip()[-80:]
    return None

def latest_log_error(start_line: int = 0):
    """Scan moonbridge.log from start_line onward for an error.
    Returns (hint, total_lines).  hint is None if no new error-like line found.
    Pass the returned total_lines back as start_line next time so only freshly
    appended lines are considered (avoids re-reporting a stale transient error)."""
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None, start_line
    hint = None
    for line in lines[start_line:]:
        h = _hint_for(line)
        if h:
            hint = h   # keep the latest error in the new range
    return hint, len(lines)

def start_deepseek(on_done):
    def run():
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            write_moonbridge_config(state.api_key, state.model)

            # Re-ensure each time: re-extract if AV deleted the AppData copy
            mb = _ensure_moonbridge()
            if not mb.exists():
                # Bundle copy unavailable — try downloading from GitHub Releases
                def _on_dl_status(msg):
                    state.status = msg
                    on_done(None)   # refresh UI mid-download without finishing

                ok = _download_moonbridge(mb, _on_dl_status)
                if not ok or not mb.exists():
                    state.enabled = False
                    state.status = (
                        f"moonbridge.exe 下载失败，请手动将其放至:\n{mb}"
                    )
                    on_done(False)
                    return

            # Backup original Codex config
            codex_cfg = CODEX_HOME / "config.toml"
            if codex_cfg.exists() and not BACKUP.exists():
                shutil.copy2(codex_cfg, BACKUP)

            # Launch moonbridge, redirect output to log file
            log_f = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
            proc = subprocess.Popen(
                [str(mb), "--config", str(CONFIG_YML)],
                stdout=log_f, stderr=log_f,
                env={**os.environ,
                     "MOONBRIDGE_LOG_LEVEL": "info",
                     "GODEBUG": "http2client=0"},   # force HTTP/1.1; prevents EOF-on-first-request 502
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            state.process = proc

            # Wait for port (up to 10 seconds)
            for _ in range(100):
                time.sleep(0.1)
                # Check if process died early
                if proc.poll() is not None:
                    log_f.flush()
                    log_content = LOG_FILE.read_text(encoding="utf-8", errors="replace")
                    state.process = None
                    state.enabled = False
                    state.status = f"moonbridge 崩溃 (exit {proc.returncode})"
                    on_done(False)
                    return
                if is_port_open():
                    break
            else:
                proc.terminate()
                state.process = None
                state.enabled = False
                state.status = "启动超时 (见 moonbridge.log)"
                on_done(False)
                return

            # Generate Codex config via moonbridge CLI
            mb_str = str(mb)
            cfg    = str(CONFIG_YML)
            model_id = shell(mb_str, "--config", cfg, "--print-codex-model")

            # Always pass the native OS path — forward-slash form can cause
            # moonbridge to silently fail to write models_catalog.json on Windows.
            CODEX_HOME.mkdir(parents=True, exist_ok=True)
            codex_home_str = str(CODEX_HOME)
            toml = shell(mb_str, "--config", cfg,
                         "--print-codex-config", model_id,
                         "--codex-base-url", f"http://127.0.0.1:{PORT}/v1",
                         "--codex-home", codex_home_str)

            # Verify models_catalog.json was written — its absence causes
            # "failed to resolve feature override precedence" in Codex.
            catalog = CODEX_HOME / "models_catalog.json"
            if not catalog.exists():
                state.enabled = False
                state.status = "models_catalog.json 未生成，请更新 moonbridge 或重试"
                on_done(False)
                return

            # Merge: preserve original settings (MCP servers, notify, plugins) but
            # strip the user's saved model selection so it can't override deepseek
            # (a leftover `model = "gpt-5.5"` causes 404 unknown model).
            if BACKUP.exists():
                original = _strip_model_keys(BACKUP.read_text(encoding="utf-8")).strip()
                if original:
                    toml = toml + "\n\n# ── Original user settings ──\n" + original

            CODEX_HOME.mkdir(parents=True, exist_ok=True)
            (CODEX_HOME / "config.toml").write_text(toml, encoding="utf-8")

            # Monitor: if moonbridge dies, update status
            def monitor():
                proc.wait()
                if state.enabled:
                    state.enabled = False
                    state.status = "代理已停止 (重新开关以重启)"
            threading.Thread(target=monitor, daemon=True).start()

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
    icon_path = BASE_DIR / "icon.png"   # extracted to _MEIPASS alongside moonbridge
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
    icon_path = BASE_DIR / "icon.png"   # same _MEIPASS path
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
            log_pos[0] = 0   # log file is rewritten on start; rescan from top
            state.enabled = True
            state.status = "启动中..."
            update_ui()
            def on_done(ok):
                win.after(0, update_ui)
            start_deepseek(on_done)

    toggle_btn.config(command=on_toggle)

    # Periodically surface real upstream errors from the log while running.
    # Only newly-appended lines are scanned so a past transient error isn't
    # reported forever.
    log_pos = [0]
    def poll_log():
        if not win.winfo_exists():
            return
        if state.enabled and state.status == "运行中":
            hint, log_pos[0] = latest_log_error(log_pos[0])
            if hint:
                status_lbl.config(text=hint, fg="#f38ba8")
        win.after(2000, poll_log)
    win.after(2000, poll_log)

    # Bottom diagnostic buttons row
    btn_frame = tk.Frame(win, bg=BG)
    btn_frame.pack(fill="x", padx=16, pady=(0, 10))

    def open_log():
        if LOG_FILE.exists():
            os.startfile(str(LOG_FILE))
    tk.Button(btn_frame, text="查看日志", font=("Segoe UI", 8),
              bg=SURF, fg="#6c7086", bd=0, cursor="hand2",
              command=open_log).pack(side="right", padx=(4, 0))

    def open_codex_cfg():
        if (CODEX_HOME / "config.toml").exists():
            os.startfile(str(CODEX_HOME / "config.toml"))
    tk.Button(btn_frame, text="查看 Codex 配置", font=("Segoe UI", 8),
              bg=SURF, fg="#6c7086", bd=0, cursor="hand2",
              command=open_codex_cfg).pack(side="right")

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
