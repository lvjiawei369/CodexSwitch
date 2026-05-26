<p align="center">
  <img src="assets/icon.iconset/icon_256x256.png" width="96" alt="CodexSwitch icon" />
</p>

<h1 align="center">CodexSwitch</h1>

<p align="center">
  Route Codex CLI to DeepSeek · One-click toggle · Zero config edits
</p>

<p align="center">
  English · <a href="README.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/lvjiawei369/CodexSwitch/releases/latest">
    <img src="https://img.shields.io/github/v/release/lvjiawei369/CodexSwitch?style=flat-square&label=latest&color=4A90D9" alt="Latest Release" />
  </a>
  <a href="https://github.com/lvjiawei369/CodexSwitch/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License" />
  </a>
  <img src="https://img.shields.io/badge/macOS-12%2B-lightgrey?style=flat-square&logo=apple" alt="macOS 12+" />
  <img src="https://img.shields.io/badge/Windows-10%2B-lightgrey?style=flat-square&logo=windows" alt="Windows 10+" />
</p>

---

## What is this?

[Codex CLI](https://github.com/openai/codex) only talks to OpenAI by default. CodexSwitch starts a transparent local proxy that intercepts Codex's requests and forwards them to [DeepSeek](https://platform.deepseek.com) instead.

**Toggle ON → use DeepSeek. Toggle OFF → back to OpenAI. No config files touched.**

## Features

- **Zero config** — Codex config is generated on start and restored on stop, leaving no trace
- **Local proxy** — traffic flows only between your machine and DeepSeek's servers; the app never sees your data
- **Two models** — V4 Pro (stronger reasoning) / V4 Flash (faster responses), switch any time
- **Three platforms** — macOS menu bar · macOS window · Windows system tray
- **Works out of the box** — bundled Moon Bridge binary, no Go installation required

---

## Download

Go to **[Releases](https://github.com/lvjiawei369/CodexSwitch/releases)**:

| Platform | File | Notes |
|---|---|---|
| macOS | `CodexSwitch.dmg` | Menu bar app, click ⚡ to open panel |
| macOS | `CodexSwitch-Window.dmg` | Standalone window, for hidden-menu-bar setups |
| Windows | `CodexSwitch-Setup.exe` | System tray, double-click to run |

### macOS install

1. Open the DMG and drag **CodexSwitch.app** into **Applications**
2. In Finder **right-click** the app → **Open** (required once to bypass Gatekeeper)

> **macOS Ventura / Sonoma**: if the dialog only shows a "Done" button, go to  
> **System Settings → Privacy & Security → scroll to bottom → Open Anyway**

---

## Quick start

1. Get a [DeepSeek API Key](https://platform.deepseek.com) (sign up → API Keys → Create)
2. Open CodexSwitch and paste your API key
3. Choose a model and flip the toggle ON
4. Open Codex — it now uses DeepSeek automatically

---

## How it works

```
Codex CLI
    │  OpenAI Responses API request
    ▼
127.0.0.1:38440  (Moon Bridge local proxy)
    │  format conversion + model routing
    ▼
api.deepseek.com
```

**When toggled ON**
1. Writes Moon Bridge config (`~/.codex-switch/config.yml`)
2. Starts the proxy process in the background, listening on `127.0.0.1:38440`
3. Runs `moonbridge --print-codex-config` to write `~/.codex/config.toml` (original is backed up)

**When toggled OFF**
1. Terminates the proxy process
2. Restores the original `~/.codex/config.toml` and removes the backup

---

## Build from source

### macOS

```bash
# Prerequisites: Xcode Command Line Tools
xcode-select --install

# Menu bar build
bash build_swift.sh        # → dist/CodexSwitch.dmg

# Window build
bash build_swift_window.sh # → dist/CodexSwitch-Window.dmg
```

### Windows

```bash
pip install pyinstaller pillow pystray
pyinstaller --clean --noconfirm CodexSwitch.spec
# → dist/CodexSwitch.exe
```

Pushing a `v*` tag triggers GitHub Actions to build the Windows `.exe` and publish a Release automatically.

---

## Project structure

```
CodexSwitch/
├── Swift/                    # macOS menu bar app (Swift + AppKit)
│   └── Sources/
│       ├── AppDelegate.swift       # NSStatusItem + Popover management
│       ├── ContentView.swift       # SwiftUI panel UI
│       ├── Manager.swift           # Core logic: proxy start/stop, config
│       ├── NativeTextField.swift   # Native text field (paste support)
│       └── VisualEffectView.swift  # Vibrancy / blur background
├── Swift-Window/             # macOS window app (separate bundle ID)
├── codex_switch_win.py       # Windows app (Python + pystray + tkinter)
├── assets/
│   ├── moonbridge            # Moon Bridge macOS universal binary (arm64 + x86_64)
│   └── moonbridge.exe        # Moon Bridge Windows binary
├── build_swift.sh
├── build_swift_window.sh
├── build_dmg.sh              # DMG builder: background + Applications link
└── .github/workflows/
    └── release.yml           # Push tag → build Windows .exe → publish Release
```

---

## Changelog

### v1.5
- Fix Windows "failed to resolve feature override precedence" on Codex launch: pass native backslash path to moonbridge so `models_catalog.json` is correctly written to `~/.codex/`
- Add explicit check: if `models_catalog.json` is missing after config generation, show a clear error instead of letting Codex throw a cryptic message

### v1.4
- Windows: copy `moonbridge.exe` to `%LOCALAPPDATA%\CodexSwitch\` on startup — no longer relying on the temp `_MEIPASS` folder that AV aggressively scans
- Windows: if AV deletes the binary, auto-download it from GitHub Releases with live progress in the UI
- Windows: re-copy when bundled size changes (handles app updates), retry on AV file lock
- Fix: product name corrected from "Claude Codex CLI" to "Codex CLI" (openai/codex)

### v1.3
- WeChat community QR code
- README images switched to Release CDN URLs

### v1.2
- Fix conversation drops: force HTTP/1.1 to prevent Go HTTP/2 idle-connection resets
- Fix slow responses: remove forced high reasoning budget; let the model decide
- Fix toggle logic: `toggle()` split into explicit `start()` / `stop()`
- Fix Gatekeeper blocking: remove `--options runtime` from ad-hoc signing

### v1.1
- Fix API Key field not accepting paste
- Fix show/hide password button unresponsive
- Polished DMG for menu bar build (background image + Applications shortcut + guide)
- Add GitHub Actions to auto-build Windows `.exe`

### v1.0
- macOS menu bar + window builds
- Windows system tray build
- Bundled Moon Bridge binary — no Go required

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `WinError 2` / moonbridge not found | Antivirus quarantined `moonbridge.exe` | CodexSwitch will auto-download it; or add `%LOCALAPPDATA%\CodexSwitch\` to your AV whitelist |
| `502 Insufficient Balance` | DeepSeek account balance is zero | Top up at [platform.deepseek.com](https://platform.deepseek.com) |
| `Reconnecting… 5/5` | Proxy stopped or network issue | Toggle OFF then ON again |
| macOS "Open Anyway" not shown | Gatekeeper strict mode | System Settings → Privacy & Security → Open Anyway |

---

## Contributing

Issues and PRs are welcome, especially:

- Support for other OpenAI-compatible providers (Gemini, Grok, etc.)
- Better error messages and status feedback
- macOS notarization with a proper Apple Developer certificate

---

## License

[MIT](LICENSE) · Not affiliated with OpenAI, Anthropic, or DeepSeek
