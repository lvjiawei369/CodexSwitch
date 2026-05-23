# CodexSwitch

让 [Claude Codex CLI](https://github.com/anthropics/claude-code) 使用 DeepSeek 模型的 macOS 原生应用。

通过内置的 Moon Bridge 代理在本地透明转发请求，无需修改任何 Codex 配置，开关即用。

---

## 版本

### v1.1（2026-05-23）
- **修复粘贴**：用原生 `NSTextField`/`NSSecureTextField` 替换 SwiftUI 文本框，Cmd+V 和右键粘贴均可正常使用
- **修复眼睛图标**：点击显示/隐藏 API Key 现在正确生效
- **菜单栏版 DMG 精品打包**：背景图、Applications 快捷方式、使用指南，与窗口版一致
- **DMG 构建稳定性**：修复 Finder 持有卷时 `hdiutil detach` 阻塞导致构建失败的问题

### v1.0（初始版本）
- 菜单栏版（`Swift/`）：点击 ⚡ 图标弹出毛玻璃面板
- 窗口版（`Swift-Window/`）：普通 Dock 应用，固定窗口，适合菜单栏图标不可见的用户
- 两个版本相互独立：独立 Bundle ID、独立配置目录、独立 UserDefaults
- 内置 Moon Bridge 通用二进制（arm64 + x86_64），macOS 12.0+
- 精品 DMG 安装包：带背景图、Applications 快捷方式、中文使用指南

---

## 两个版本

| | 菜单栏版 | 窗口版 |
|---|---|---|
| 入口 | 顶部菜单栏 ⚡ 图标 | Dock 图标 + 普通窗口 |
| 构建 | `bash build_swift.sh` | `bash build_swift_window.sh` |
| 输出 | `dist/CodexSwitch.dmg` | `dist/CodexSwitch-Window.dmg` |
| 配置目录 | `~/.codex-switch/` | `~/.codex-switch-window/` |
| Bundle ID | `com.codexswitch.app` | `com.codexswitch.window` |

---

## 快速开始

1. 下载 DMG，将 `.app` 拖入 Applications
2. 首次运行右键 → 「打开」绕过 Gatekeeper
3. 输入 [DeepSeek API Key](https://platform.deepseek.com)（格式：`sk-xxxx`）
4. 选择模型，打开开关，状态显示「运行中」
5. 打开 Codex，模型已切换为 DeepSeek

关闭开关后，Codex 自动恢复默认配置。

---

## 构建

```bash
# 菜单栏版
bash build_swift.sh

# 窗口版
bash build_swift_window.sh
```

依赖：Xcode Command Line Tools、`assets/moonbridge`（预编译二进制）

---

## 技术说明

- 代理运行在 `127.0.0.1:38440`，仅本地通信
- API 请求直接发往 `api.deepseek.com`，本应用不中转任何数据
- 启动时备份原 `~/.codex/config.toml`，关闭时自动还原
