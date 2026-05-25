# CodexSwitch

让 [Claude Codex CLI](https://github.com/anthropics/claude-code) 使用 [DeepSeek](https://platform.deepseek.com) 模型的原生桌面应用。

一键切换，无需手动改配置。关闭后自动恢复默认。

---

## 下载安装

前往 [Releases](https://github.com/lvjiawei369/CodexSwitch/releases) 下载对应平台的安装包：

| 平台 | 文件 | 说明 |
|---|---|---|
| macOS 菜单栏版 | `CodexSwitch.dmg` | 顶部菜单栏 ⚡ 图标，弹出毛玻璃面板 |
| macOS 窗口版 | `CodexSwitch-Window.dmg` | 普通 Dock 应用，适合菜单栏不可见的用户 |
| Windows | `CodexSwitch-Setup.exe` | 系统托盘图标，双击直接运行 |

### macOS 首次运行

拖入 Applications 后，**右键点击 → 打开**（绕过 Gatekeeper）。

> 如果弹窗只有「完成」按钮（macOS Ventura/Sonoma）：  
> 系统设置 → 隐私与安全性 → 滚动到底部 → 点「仍然打开」

---

## 使用方法

1. 打开 CodexSwitch
2. 输入 [DeepSeek API Key](https://platform.deepseek.com)（格式：`sk-xxxx`）
3. 选择模型（V4 Pro 更强 / V4 Flash 更快）
4. 打开开关 → 状态显示「运行中」
5. 正常使用 Codex，模型已切换为 DeepSeek

**关闭开关后，Codex 自动恢复默认 Claude 配置。**

---

## 工作原理

```
Codex CLI  →  127.0.0.1:38440  →  Moon Bridge  →  api.deepseek.com
                (本地代理)         (格式转换)         (DeepSeek API)
```

- 启动时：写入 moonbridge 配置 → 启动本地代理进程 → 生成 Codex config.toml
- 关闭时：停止代理进程 → 还原原始 config.toml
- 所有数据仅在本机和 DeepSeek 服务器之间流动，本应用不中转任何请求

---

## 项目结构

```
CodexSwitch/
├── Swift/                  # macOS 菜单栏版（NSStatusItem + Popover）
│   ├── Sources/
│   │   ├── AppDelegate.swift
│   │   ├── ContentView.swift
│   │   ├── Manager.swift       # 核心逻辑：代理启停、配置管理
│   │   ├── NativeTextField.swift
│   │   └── VisualEffectView.swift
│   └── Info.plist
├── Swift-Window/           # macOS 窗口版（NSWindow + Dock 图标）
│   └── Sources/            # 与菜单栏版功能相同，独立 Bundle ID 和配置目录
├── codex_switch_win.py     # Windows 版（pystray + tkinter）
├── CodexSwitch.spec        # PyInstaller 打包配置
├── assets/
│   ├── moonbridge          # Moon Bridge 预编译二进制（macOS universal）
│   └── moonbridge.exe      # Moon Bridge 预编译二进制（Windows）
├── build_swift.sh          # 构建 macOS 菜单栏版
├── build_swift_window.sh   # 构建 macOS 窗口版
├── build_dmg.sh            # 制作精品 DMG（背景图 + Applications 快捷方式）
└── .github/workflows/
    └── release.yml         # 推 tag 自动构建 Windows .exe 并发布 Release
```

---

## 从源码构建

### macOS

```bash
# 依赖：Xcode Command Line Tools
xcode-select --install

# 菜单栏版
bash build_swift.sh

# 窗口版
bash build_swift_window.sh

# 产物在 dist/
```

### Windows

```bash
pip install pyinstaller pillow pystray
pyinstaller --clean --noconfirm CodexSwitch.spec
# 产物：dist/CodexSwitch.exe
```

---

## 版本记录

### v1.2（2026-05-25）
- **修复对话中断**：moonbridge 进程增加 `GODEBUG=http2client=0`，强制 HTTP/1.1，避免 Go HTTP/2 空闲连接被重置导致 Codex 对话中途断开
- **修复响应很慢**：去掉 `default_reasoning_level: "high"`，不再强制每次请求都用最高推理预算
- **修复开关逻辑**：将 `toggle()` 拆分为明确的 `start()` / `stop()`，消除 Task.detached 中的状态读取时序问题
- **修复 Gatekeeper 拦截**：去掉 ad-hoc 签名中的 `--options runtime`，恢复右键→打开可绕过的行为

### v1.1（2026-05-23）
- **修复粘贴**：用原生 `NSTextField`/`NSSecureTextField` 替换 SwiftUI 文本框，Cmd+V 和右键粘贴均可正常使用
- **修复眼睛图标**：切换显示/隐藏 API Key 正确生效
- **菜单栏版 DMG 精品打包**：背景图、Applications 快捷方式、使用指南
- **CI/CD**：推 tag 自动触发 GitHub Actions 构建 Windows .exe 并发布 Release

### v1.0（初始版本）
- macOS 菜单栏版：毛玻璃弹出面板
- macOS 窗口版：普通 Dock 应用
- Windows 版：系统托盘应用
- 内置 Moon Bridge 通用二进制，无需安装 Go

---

## 贡献

欢迎 PR 和 Issue。主要方向：

- 支持更多模型（其他 OpenAI 兼容 API）
- 更好的错误提示
- macOS 正式签名和公证（需 Apple Developer 账号）

---

## License

[MIT](LICENSE)

---

> **注意**：本项目与 Anthropic、DeepSeek 官方无关。Moon Bridge 二进制来自 [moonbridge](https://github.com/moonbridge-dev/moonbridge)。
