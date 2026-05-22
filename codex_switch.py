#!/usr/bin/env python3
"""
CodexSwitch — Codex × DeepSeek 可视化配置工具
通过 Moon Bridge 将 Codex 的请求转发到 DeepSeek API
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess, threading, json, os, platform, webbrowser
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
APP_DIR   = Path.home() / ".codex-switch"
MOON_DIR  = APP_DIR / "moon-bridge"
SETTINGS  = APP_DIR / "settings.json"
MOON_REPO = "https://github.com/ZhiYi-R/moon-bridge.git"
IS_WIN    = platform.system() == "Windows"
IS_MAC    = platform.system() == "Darwin"

# ── Rich PATH so subprocesses can find tools ──────────────────────────────────
if IS_WIN:
    _extra = [
        r"C:\Program Files\Go\bin",
        r"C:\Program Files (x86)\Go\bin",
        str(Path.home() / "go" / "bin"),
        str(Path.home() / "AppData" / "Local" / "Programs" / "Codex"),
    ]
    os.environ["PATH"] = ";".join(_extra) + ";" + os.environ.get("PATH", "")
else:
    _extra = [
        "/opt/homebrew/bin", "/opt/homebrew/sbin",
        "/usr/local/bin", "/usr/local/go/bin",
        str(Path.home() / "go" / "bin"),
    ]
    os.environ["PATH"] = ":".join(_extra) + ":" + os.environ.get("PATH", "")

# ── Model definitions ─────────────────────────────────────────────────────────
MODEL_META = {
    "deepseek-v4-pro": {
        "ctx":     1_000_000,
        "out":     384_000,
        "display": "DeepSeek V4 Pro",
        "reasoning": True,
    },
    "deepseek-v4-flash": {
        "ctx":     1_000_000,
        "out":     384_000,
        "display": "DeepSeek V4 Flash",
        "reasoning": True,
    },
}
MODELS = list(MODEL_META.keys())

# ── Catppuccin Mocha palette ───────────────────────────────────────────────────
C = {
    "bg":      "#1e1e2e",
    "bg2":     "#181825",
    "bg3":     "#11111b",
    "surface": "#313244",
    "overlay": "#45475a",
    "text":    "#cdd6f4",
    "subtext": "#a6adc8",
    "muted":   "#6c7086",
    "green":   "#a6e3a1",
    "red":     "#f38ba8",
    "blue":    "#89b4fa",
    "pink":    "#f5c2e7",
    "teal":    "#89dceb",
    "peach":   "#fab387",
    "yellow":  "#f9e2af",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def build_config(api_key: str, model: str, port: str) -> str:
    """Generate Moon Bridge config.yml with the correct schema."""
    meta = MODEL_META.get(model, MODEL_META["deepseek-v4-pro"])
    ctx, out, display = meta["ctx"], meta["out"], meta["display"]

    reasoning_block = ""
    if meta.get("reasoning"):
        reasoning_block = (
            f'    default_reasoning_level: "high"\n'
            f'    supported_reasoning_levels:\n'
            f'      - effort: "high"\n'
            f'        description: "High reasoning effort"\n'
            f'      - effort: "xhigh"\n'
            f'        description: "Extra high reasoning effort"\n'
            f'    supports_reasoning_summaries: true\n'
            f'    default_reasoning_summary: "auto"\n'
            f'    extensions:\n'
            f'      deepseek_v4:\n'
            f'        enabled: true\n'
        )

    return (
        f'mode: "Transform"\n\n'
        f'server:\n'
        f'  addr: "127.0.0.1:{port}"\n\n'
        f'defaults:\n'
        f'  model: "{model}"\n\n'
        f'models:\n'
        f'  {model}:\n'
        f'    context_window: {ctx}\n'
        f'    max_output_tokens: {out}\n'
        f'    display_name: "{display}"\n'
        + reasoning_block
        + f'\nproviders:\n'
          f'  deepseek:\n'
          f'    base_url: "https://api.deepseek.com/anthropic"\n'
          f'    api_key: "{api_key}"\n'
          f'    version: "2023-06-01"\n'
          f'    user_agent: "moonbridge/1.0"\n'
          f'    offers:\n'
          f'      - model: {model}\n'
          f'\nroutes:\n'
          f'  {model}:\n'
          f'    model: {model}\n'
          f'    provider: deepseek\n'
    )


# ── Main App ──────────────────────────────────────────────────────────────────
class CodexSwitch(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CodexSwitch")
        self.configure(bg=C["bg"])
        self.resizable(False, False)

        self._proc:  subprocess.Popen | None = None
        self._log_n: int = 0

        self.var_key   = tk.StringVar()
        self.var_model = tk.StringVar(value="deepseek-v4-pro")
        self.var_port  = tk.StringVar(value="38440")
        self.var_dir   = tk.StringVar()

        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._load_settings()
        self._build_ui()
        self.geometry("460x740")
        self.protocol("WM_DELETE_WINDOW", self._on_quit)
        threading.Thread(target=self._check_env, daemon=True).start()

    # ── Settings ──────────────────────────────────────────────────────────────
    def _load_settings(self):
        if SETTINGS.exists():
            try:
                d = json.loads(SETTINGS.read_text())
                self.var_key.set(d.get("api_key", ""))
                self.var_model.set(d.get("model", "deepseek-v4-pro"))
                self.var_port.set(d.get("port", "38440"))
                self.var_dir.set(d.get("project_dir", ""))
            except Exception:
                pass

    def _save_settings(self):
        SETTINGS.write_text(json.dumps({
            "api_key":     self.var_key.get(),
            "model":       self.var_model.get(),
            "port":        self.var_port.get(),
            "project_dir": self.var_dir.get(),
        }, indent=2))

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=C["bg2"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚡ CodexSwitch",
                 font=("Helvetica Neue", 18, "bold"),
                 fg=C["text"], bg=C["bg2"]).pack()
        tk.Label(hdr, text="让 Codex 使用 DeepSeek API",
                 font=("Helvetica Neue", 10),
                 fg=C["muted"], bg=C["bg2"]).pack()

        # Form
        frm = tk.Frame(self, bg=C["bg"], padx=20, pady=14)
        frm.pack(fill="x")

        # API Key
        self._field_label(frm, "DeepSeek API Key")
        kr = tk.Frame(frm, bg=C["bg"])
        kr.pack(fill="x", pady=(3, 12))
        self.ent_key = self._make_entry(kr, self.var_key, show="•")
        self.ent_key.pack(side="left", fill="x", expand=True)
        self.btn_eye = self._make_flat_btn(kr, "👁", self._toggle_key_vis, width=3)
        self.btn_eye.pack(side="left", padx=(5, 0))

        # Model
        self._field_label(frm, "模型 Model")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
            fieldbackground=C["surface"], background=C["surface"],
            foreground=C["text"], selectbackground=C["surface"],
            selectforeground=C["text"], arrowcolor=C["subtext"], padding=6,
        )
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", C["surface"])],
            foreground=[("readonly", C["text"])],
        )
        ttk.Combobox(frm, textvariable=self.var_model,
                     values=MODELS, font=("Menlo", 11),
                     style="Dark.TCombobox").pack(fill="x", pady=(3, 12))

        # Port
        self._field_label(frm, "本地端口 Local Port")
        self._make_entry(frm, self.var_port).pack(fill="x", pady=(3, 12))

        # Project directory
        self._field_label(frm, "项目目录 Project Directory (可选)")
        dr = tk.Frame(frm, bg=C["bg"])
        dr.pack(fill="x", pady=(3, 4))
        self._make_entry(dr, self.var_dir).pack(side="left", fill="x", expand=True)
        self._make_flat_btn(dr, "📂", self._browse_dir).pack(side="left", padx=(5, 0))

        # Divider
        tk.Frame(self, bg=C["surface"], height=1).pack(fill="x")

        # Status + Buttons
        ctrl = tk.Frame(self, bg=C["bg"], padx=20, pady=12)
        ctrl.pack(fill="x")

        self.lbl_status = tk.Label(ctrl, text="● 未启动",
                                   font=("Menlo", 11, "bold"),
                                   fg=C["muted"], bg=C["bg"])
        self.lbl_status.pack(anchor="w", pady=(0, 6))

        go_label = ("📦  安装 Go (brew install go)"
                    if IS_MAC else "📦  下载安装 Go (go.dev/dl)")
        self.btn_go = self._make_big_btn(ctrl, go_label, self._install_go, C["yellow"])
        self.btn_go.pack(fill="x", pady=(0, 8))

        self.btn_moon = self._make_big_btn(
            ctrl, "🚀  启动 Moon Bridge", self._toggle_moon, C["green"])
        self.btn_moon.pack(fill="x", pady=(0, 4))

        self.btn_cfg = self._make_big_btn(
            ctrl, "⚙️   生成 Codex 配置", self._gen_codex_config, C["blue"])
        self.btn_cfg.pack(fill="x", pady=(0, 4))

        self.btn_launch = self._make_big_btn(
            ctrl, "🖥   启动 Codex", self._launch_codex, C["pink"])
        self.btn_launch.pack(fill="x")

        # Divider
        tk.Frame(self, bg=C["surface"], height=1).pack(fill="x", pady=(8, 0))

        # Log area
        log_wrap = tk.Frame(self, bg=C["bg3"], padx=12, pady=8)
        log_wrap.pack(fill="both", expand=True)
        tk.Label(log_wrap, text="日志", font=("Helvetica Neue", 10),
                 fg=C["muted"], bg=C["bg3"]).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(
            log_wrap, height=9, font=("Menlo", 10),
            bg=C["bg3"], fg=C["text"], insertbackground=C["text"],
            relief="flat", bd=0, wrap="word", state="disabled",
        )
        self.log.pack(fill="both", expand=True, pady=(4, 0))

    # ── Widget factories ──────────────────────────────────────────────────────
    def _field_label(self, parent, text):
        tk.Label(parent, text=text, font=("Helvetica Neue", 11),
                 fg=C["subtext"], bg=C["bg"]).pack(anchor="w")

    def _make_entry(self, parent, var, show=None):
        kw = dict(textvariable=var, font=("Menlo", 12),
                  bg=C["surface"], fg=C["text"], insertbackground=C["text"],
                  relief="flat", bd=7, highlightthickness=0)
        if show:
            kw["show"] = show
        return tk.Entry(parent, **kw)

    def _make_flat_btn(self, parent, text, cmd, width=None):
        kw = dict(text=text, command=cmd, bg=C["overlay"], fg=C["text"],
                  font=("Helvetica Neue", 11), relief="flat", bd=0,
                  padx=8, pady=7, cursor="hand2",
                  activebackground=C["surface"], activeforeground=C["text"])
        if width:
            kw["width"] = width
        return tk.Button(parent, **kw)

    def _make_big_btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd,
                         bg=color, fg=C["bg2"],
                         font=("Helvetica Neue", 12, "bold"),
                         relief="flat", bd=0, pady=10, cursor="hand2",
                         activebackground=color, activeforeground=C["bg2"])

    # ── Interactions ──────────────────────────────────────────────────────────
    def _toggle_key_vis(self):
        hidden = self.ent_key.cget("show") == "•"
        self.ent_key.config(show="" if hidden else "•")
        self.btn_eye.config(text="🙈" if hidden else "👁")

    def _browse_dir(self):
        d = filedialog.askdirectory(title="选择项目目录")
        if d:
            self.var_dir.set(d)

    # ── Logging ───────────────────────────────────────────────────────────────
    def _log(self, msg: str, color: str | None = None):
        def _do():
            self.log.config(state="normal")
            if color:
                self._log_n += 1
                tag = f"t{self._log_n}"
                self.log.tag_config(tag, foreground=color)
                self.log.insert("end", f"[{ts()}] {msg}\n", tag)
            else:
                self.log.insert("end", f"[{ts()}] {msg}\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, _do)

    # ── Environment check ─────────────────────────────────────────────────────
    def _check_env(self):
        go_ok = False
        for cmd, name in [
            ("node --version",  "Node.js"),
            ("go version",      "Go"),
            ("codex --version", "Codex CLI"),
        ]:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if r.returncode == 0:
                ver = r.stdout.strip().split("\n")[0]
                self._log(f"✓ {name}  {ver}", C["green"])
                if name == "Go":
                    go_ok = True
            else:
                if name == "Go":
                    hint = "brew install go" if IS_MAC else "go.dev/dl"
                    self._log(f"✗ Go 未安装 — 点击「安装 Go」按钮（{hint}）", C["red"])
                else:
                    self._log(f"✗ {name} 未安装", C["red"])

        if go_ok:
            self.after(0, self.btn_go.pack_forget)

        if MOON_DIR.exists():
            self._log("✓ Moon Bridge 已就绪", C["green"])
        else:
            self._log("ℹ Moon Bridge 将在首次启动时自动克隆", C["teal"])

    # ── Install Go ────────────────────────────────────────────────────────────
    def _install_go(self):
        if IS_WIN:
            webbrowser.open("https://go.dev/dl/")
            self._log("已打开 Go 下载页面，安装完成后请重启 CodexSwitch", C["yellow"])
        else:
            self._log("正在通过 Homebrew 安装 Go，请稍候（需要几分钟）...", C["yellow"])
            self.btn_go.config(state="disabled", text="⏳  安装中...")
            threading.Thread(target=self._run_install_go_brew, daemon=True).start()

    def _run_install_go_brew(self):
        r = subprocess.run(
            ["/opt/homebrew/bin/brew", "install", "go"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            self._log("✓ Go 安装成功！", C["green"])
            threading.Thread(target=self._check_env, daemon=True).start()
        else:
            self._log(f"✗ 安装失败: {r.stderr.strip()}", C["red"])
            self.after(0, lambda: self.btn_go.config(
                state="normal", text="📦  安装 Go (brew install go)"))

    # ── Moon Bridge control ───────────────────────────────────────────────────
    def _toggle_moon(self):
        if self._proc and self._proc.poll() is None:
            self._stop_moon()
        else:
            if not self.var_key.get().strip():
                messagebox.showerror("缺少配置", "请先填写 DeepSeek API Key")
                return
            self._save_settings()
            threading.Thread(target=self._run_moon, daemon=True).start()

    def _run_moon(self):
        self._log("── 准备 Moon Bridge ──", C["teal"])

        if not MOON_DIR.exists():
            self._log("正在克隆 Moon Bridge 仓库，首次需要一点时间...")
            r = subprocess.run(
                ["git", "clone", MOON_REPO, str(MOON_DIR)],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                self._log(f"✗ 克隆失败: {r.stderr.strip()}", C["red"])
                return
            self._log("✓ Moon Bridge 克隆完成", C["green"])

        model = self.var_model.get().strip() or "deepseek-v4-pro"
        port  = self.var_port.get().strip()  or "38440"
        cfg   = build_config(self.var_key.get().strip(), model, port)
        (MOON_DIR / "config.yml").write_text(cfg)
        self._log("✓ config.yml 已更新", C["green"])

        self._log(f"正在启动 Moon Bridge (端口 {port})...")
        go_bin = "go.exe" if IS_WIN else "go"
        try:
            self._proc = subprocess.Popen(
                [go_bin, "run", "./cmd/moonbridge", "--config", "config.yml"],
                cwd=str(MOON_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
        except FileNotFoundError:
            self._log("✗ 未找到 go 命令，请先安装 Go 1.25+", C["red"])
            return

        self.after(0, self._ui_set_running)
        for line in self._proc.stdout:
            self._log(line.rstrip(), C["teal"])
        self._proc = None
        self.after(0, self._ui_set_stopped)

    def _stop_moon(self):
        if self._proc:
            self._proc.terminate()
            self._log("正在停止 Moon Bridge...", C["peach"])

    def _ui_set_running(self):
        self.btn_moon.config(text="⏹   停止 Moon Bridge", bg=C["red"])
        self.lbl_status.config(text="● 运行中", fg=C["green"])

    def _ui_set_stopped(self):
        self.btn_moon.config(text="🚀  启动 Moon Bridge", bg=C["green"])
        self.lbl_status.config(text="● 已停止", fg=C["muted"])
        self._log("Moon Bridge 已停止", C["peach"])

    # ── Generate Codex config ─────────────────────────────────────────────────
    def _gen_codex_config(self):
        if not MOON_DIR.exists():
            messagebox.showwarning("提示", "请先点击「启动 Moon Bridge」")
            return
        port = self.var_port.get().strip() or "38440"
        threading.Thread(target=self._run_gen_config, args=(port,), daemon=True).start()

    def _run_gen_config(self, port: str):
        self._log("── 生成 Codex 配置 ──", C["blue"])
        codex_home = Path.home() / ".codex"
        codex_home.mkdir(exist_ok=True)
        go_bin = "go.exe" if IS_WIN else "go"

        r = subprocess.run(
            [go_bin, "run", "./cmd/moonbridge", "--config", "config.yml",
             "--print-codex-model"],
            cwd=str(MOON_DIR), capture_output=True, text=True,
        )
        if r.returncode != 0:
            self._log(f"✗ 获取模型 ID 失败: {r.stderr.strip()}", C["red"])
            return
        model_id = r.stdout.strip()
        self._log(f"模型 ID: {model_id}")

        r2 = subprocess.run(
            [go_bin, "run", "./cmd/moonbridge",
             "--config",             "config.yml",
             "--print-codex-config", model_id,
             "--codex-base-url",     f"http://127.0.0.1:{port}/v1",
             "--codex-home",         str(codex_home)],
            cwd=str(MOON_DIR), capture_output=True, text=True,
        )
        if r2.returncode != 0:
            self._log(f"✗ 生成失败: {r2.stderr.strip()}", C["red"])
            return

        (codex_home / "config.toml").write_text(r2.stdout)
        self._log(f"✓ 写入: {codex_home}/config.toml", C["green"])
        self._log("✓ Codex 配置已就绪，可以启动 Codex 了 🎉", C["green"])

    # ── Launch Codex ──────────────────────────────────────────────────────────
    def _launch_codex(self):
        project    = self.var_dir.get().strip() or str(Path.home())
        codex_home = str(Path.home() / ".codex")

        if IS_WIN:
            cmd = f'set "CODEX_HOME={codex_home}" && cd /d "{project}" && codex --cd "{project}"'
            subprocess.Popen(
                ["cmd.exe", "/k", cmd],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            self._log("✓ Codex 已在新命令窗口启动", C["green"])
        else:
            launch_sh = APP_DIR / "launch_codex.sh"
            launch_sh.write_text(
                f'#!/bin/bash\nexport CODEX_HOME="{codex_home}"\n'
                f'cd "{project}"\nexec codex --cd "{project}"\n'
            )
            launch_sh.chmod(0o755)
            apple = f'tell application "Terminal" to do script "{launch_sh}"'
            r = subprocess.run(["osascript", "-e", apple], capture_output=True, text=True)
            if r.returncode != 0:
                self._log(f"✗ 启动 Terminal 失败: {r.stderr.strip()}", C["red"])
                return
            subprocess.run(["osascript", "-e",
                            'tell application "Terminal" to activate'],
                           capture_output=True)
            self._log("✓ Codex 已在 Terminal 启动", C["green"])

        self._log(f"  项目目录: {project}", C["subtext"])

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def _on_quit(self):
        self._save_settings()
        if self._proc and self._proc.poll() is None:
            self._stop_moon()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CodexSwitch()
    app.mainloop()
