<p align="center">
  <img src="assets/icon.iconset/icon_256x256.png" width="96" alt="CodexSwitch icon" />
</p>

<h1 align="center">CodexSwitch</h1>

<p align="center">
  让 Claude Codex CLI 使用 DeepSeek 模型 · 一键切换 · 无需改配置
</p>

<p align="center">
  <a href="https://github.com/lvjiawei369/CodexSwitch/releases/latest">
    <img src="https://img.shields.io/github/v/release/lvjiawei369/CodexSwitch?style=flat-square&label=最新版本&color=4A90D9" alt="Latest Release" />
  </a>
  <a href="https://github.com/lvjiawei369/CodexSwitch/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License" />
  </a>
  <img src="https://img.shields.io/badge/macOS-12%2B-lightgrey?style=flat-square&logo=apple" alt="macOS 12+" />
  <img src="https://img.shields.io/badge/Windows-10%2B-lightgrey?style=flat-square&logo=windows" alt="Windows 10+" />
</p>

---

## 这是什么

[Codex CLI](https://github.com/openai/codex) 默认只能调用 OpenAI 模型。CodexSwitch 在本地启动一个透明代理，让 Codex 以为自己在和 OpenAI 通信，实际上请求被转发到 [DeepSeek](https://platform.deepseek.com)。

**打开开关 → 用 DeepSeek。关闭开关 → 恢复 OpenAI。全程不碰任何配置文件。**

## 特性

- **零配置** — 自动生成和还原 Codex 配置，关闭后不留痕迹
- **本地代理** — 流量仅在本机和 DeepSeek 服务器之间流转，应用本身不经手任何数据
- **双模型** — V4 Pro（推理更强）/ V4 Flash（响应更快）随时切换
- **双端覆盖** — macOS 菜单栏版 · macOS 窗口版 · Windows 系统托盘版
- **开箱即用** — 内置预编译 Moon Bridge 二进制，无需安装 Go 环境

---

## 下载

前往 **[Releases](https://github.com/lvjiawei369/CodexSwitch/releases)** 下载：

| 平台 | 安装包 | 适用场景 |
|---|---|---|
| macOS | `CodexSwitch.dmg` | 菜单栏常驻，点击 ⚡ 弹出面板 |
| macOS | `CodexSwitch-Window.dmg` | 普通窗口应用，适合菜单栏不可见的用户 |
| Windows | `CodexSwitch-Setup.exe` | 系统托盘，双击直接运行 |

### macOS 安装说明

1. 打开 DMG，将 App 拖入 **Applications**
2. 在 Finder 中**右键点击** App → **打开**（首次需要手动授权，之后正常双击即可）

> **提示（macOS Ventura / Sonoma）**：若弹窗只有「完成」按钮，前往  
> **系统设置 → 隐私与安全性 → 滚动到底部 → 点「仍然打开」**

---

## 快速上手

1. 获取 [DeepSeek API Key](https://platform.deepseek.com)（注册 → API Keys → Create）
2. 打开 CodexSwitch，填入 API Key
3. 选择模型，打开开关
4. 打开 Codex，正常使用即可

---

## 工作原理

```
Codex CLI
    │  anthropic API 请求
    ▼
127.0.0.1:38440  (Moon Bridge 本地代理)
    │  格式转换 + 模型路由
    ▼
api.deepseek.com
```

**开启时**
1. 写入 Moon Bridge 配置（`~/.codex-switch/config.yml`）
2. 在后台启动代理进程，监听 `127.0.0.1:38440`
3. 调用 `moonbridge --print-codex-config` 生成 `~/.codex/config.toml`（原文件已备份）

**关闭时**
1. 终止代理进程
2. 还原原始 `~/.codex/config.toml`，删除备份

---

## 从源码构建

### macOS

```bash
# 前置条件：Xcode Command Line Tools
xcode-select --install

# 菜单栏版
bash build_swift.sh        # → dist/CodexSwitch.dmg

# 窗口版
bash build_swift_window.sh # → dist/CodexSwitch-Window.dmg
```

### Windows

```bash
pip install pyinstaller pillow pystray
pyinstaller --clean --noconfirm CodexSwitch.spec
# → dist/CodexSwitch.exe
```

推送 `v*` tag 后 GitHub Actions 会自动构建 Windows .exe 并发布 Release。

---

## 项目结构

```
CodexSwitch/
├── Swift/                    # macOS 菜单栏版（Swift + AppKit）
│   └── Sources/
│       ├── AppDelegate.swift       # NSStatusItem + Popover 管理
│       ├── ContentView.swift       # SwiftUI 面板 UI
│       ├── Manager.swift           # 核心逻辑：代理启停、配置管理
│       ├── NativeTextField.swift   # 原生文本框（支持粘贴）
│       └── VisualEffectView.swift  # 毛玻璃背景
├── Swift-Window/             # macOS 窗口版（独立 Bundle ID 和配置目录）
├── codex_switch_win.py       # Windows 版（Python + pystray + tkinter）
├── assets/
│   ├── moonbridge            # Moon Bridge macOS 通用二进制（arm64 + x86_64）
│   └── moonbridge.exe        # Moon Bridge Windows 二进制
├── build_swift.sh
├── build_swift_window.sh
├── build_dmg.sh              # 精品 DMG：背景图 + Applications + 使用指南
└── .github/workflows/
    └── release.yml           # 推 tag → 自动构建 Windows .exe → 发布 Release
```

---

## 版本记录

### v1.2
- 修复对话中断：强制 HTTP/1.1，避免 Go HTTP/2 空闲连接被重置
- 修复响应过慢：去掉强制高推理预算，让模型按需决定思考深度
- 修复开关逻辑：`toggle()` 拆分为明确的 `start()` / `stop()`
- 修复 Gatekeeper 拦截：去掉 ad-hoc 签名中的 `--options runtime`

### v1.1
- 修复 API Key 输入框无法粘贴
- 修复显示/隐藏密码按钮无响应
- 菜单栏版 DMG 精品打包（背景图 + Applications + 使用指南）
- 新增 GitHub Actions 自动构建 Windows .exe

### v1.0
- macOS 菜单栏版 + 窗口版
- Windows 系统托盘版
- 内置 Moon Bridge，无需 Go 环境

---

## 交流群

欢迎进群技术交流，反馈 Bug 👇

<p align="center">
  <img src="https://github.com/lvjiawei369/CodexSwitch/releases/download/v1.3/wechat_group_qr.jpg" width="260" alt="微信群二维码" />
</p>

---

## 贡献

欢迎提 Issue 和 PR，尤其是：

- 支持其他兼容 OpenAI API 格式的模型（Gemini、Grok 等）
- 更好的错误提示和状态反馈
- macOS 正式签名 + 公证（需 Apple Developer 账号）

---

## License

[MIT](LICENSE) · 与 Anthropic / DeepSeek 官方无关
