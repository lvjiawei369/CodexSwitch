#!/usr/bin/env python3
"""Generate DMG background image and usage guide for CodexSwitch."""
import os
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS     = os.path.join(SCRIPT_DIR, 'assets')

# ── Dimensions ──────────────────────────────────────────────────────────────
# Logical (1x) window content size: 600 × 380
# We draw at 2× (1200×760) and save at 144 dpi → crisp on Retina
W, H = 1200, 760

# ── Canvas ──────────────────────────────────────────────────────────────────
img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
draw = ImageDraw.Draw(img)

# Background: dark navy gradient top → bottom
for y in range(H):
    t = y / H
    r = int(12 + t * 6)
    g = int(16 + t * 10)
    b = int(38 + t * 22)
    draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

# Soft radial glow behind the arrow area
cx, cy = W // 2, 380
for glow_r in range(320, 0, -6):
    alpha = int(18 * (1 - glow_r / 320))
    draw.ellipse([(cx - glow_r, cy - glow_r // 2), (cx + glow_r, cy + glow_r // 2)],
                 outline=(50, 100, 200, alpha))

# ── App icon (left) ──────────────────────────────────────────────────────────
ICON_SIZE = 220
icon_cx, icon_cy = 310, 330          # center in 2× pixels

icon_src = os.path.join(ASSETS, 'icon_512.png')
icon = Image.open(icon_src).convert('RGBA').resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

# Drop shadow
shadow_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow_layer)
sx = icon_cx - ICON_SIZE // 2
sy = icon_cy - ICON_SIZE // 2
sd.ellipse([sx + 20, sy + ICON_SIZE - 10, sx + ICON_SIZE - 20, sy + ICON_SIZE + 28],
           fill=(0, 0, 0, 70))
img = Image.alpha_composite(img, shadow_layer)

img.paste(icon, (icon_cx - ICON_SIZE // 2, icon_cy - ICON_SIZE // 2), icon)
draw = ImageDraw.Draw(img)

# ── Applications folder icon (right) ────────────────────────────────────────
FOLDER_W, FOLDER_H = 230, 195
folder_cx, folder_cy = 888, 330

fx = folder_cx - FOLDER_W // 2
fy = folder_cy - FOLDER_H // 2

def rounded_rect(draw, x1, y1, x2, y2, r, fill):
    draw.rectangle([x1 + r, y1, x2 - r, y2], fill=fill)
    draw.rectangle([x1, y1 + r, x2, y2 - r], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*r, y1 + 2*r], fill=fill)
    draw.ellipse([x2 - 2*r, y1, x2, y1 + 2*r], fill=fill)
    draw.ellipse([x1, y2 - 2*r, x1 + 2*r, y2], fill=fill)
    draw.ellipse([x2 - 2*r, y2 - 2*r, x2, y2], fill=fill)

# Folder shadow
shadow_layer2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
sd2 = ImageDraw.Draw(shadow_layer2)
sd2.ellipse([fx + 14, fy + FOLDER_H - 4, fx + FOLDER_W - 14, fy + FOLDER_H + 26],
            fill=(0, 0, 0, 65))
img = Image.alpha_composite(img, shadow_layer2)
draw = ImageDraw.Draw(img)

# Folder tab
tab_w = FOLDER_W // 3 + 10
tab_h = 32
rounded_rect(draw, fx, fy, fx + tab_w, fy + tab_h + 8, 10, (55, 115, 215))

# Folder body
rounded_rect(draw, fx, fy + tab_h, fx + FOLDER_W, fy + FOLDER_H, 14, (65, 135, 255))

# Folder highlight
draw.rectangle([fx + 10, fy + tab_h + 10, fx + FOLDER_W - 10, fy + tab_h + 26],
               fill=(105, 165, 255, 120))

# Folder inner stripe (subtle)
for i in range(3):
    y_stripe = fy + tab_h + 60 + i * 28
    draw.rounded_rectangle([fx + 20, y_stripe, fx + FOLDER_W - 20, y_stripe + 12],
                            radius=6, fill=(90, 155, 255, 90))

# ── Arrow ────────────────────────────────────────────────────────────────────
arr_x1 = icon_cx + ICON_SIZE // 2 + 30
arr_x2 = folder_cx - FOLDER_W // 2 - 30
arr_y  = 330
arr_color = (110, 165, 255)

# Shaft
draw.line([(arr_x1, arr_y), (arr_x2 - 2, arr_y)], fill=arr_color, width=7)

# Arrowhead
tip_x = arr_x2 + 28
ah, aw = 30, 20
pts = [(tip_x, arr_y), (tip_x - ah, arr_y - aw), (tip_x - ah, arr_y + aw)]
draw.polygon(pts, fill=arr_color)

# ── Fonts ────────────────────────────────────────────────────────────────────
CN_FONT = '/System/Library/Fonts/STHeiti Light.ttc'
try:
    f_label  = ImageFont.truetype(CN_FONT, 34)
    f_instr  = ImageFont.truetype(CN_FONT, 30)
    f_note   = ImageFont.truetype(CN_FONT, 22)
except Exception:
    f_label = f_instr = f_note = ImageFont.load_default()

WHITE   = (240, 240, 255, 230)
BLUE_LT = (170, 200, 255, 200)
GRAY    = (140, 160, 210, 180)

# ── Labels ───────────────────────────────────────────────────────────────────
label_y = icon_cy + ICON_SIZE // 2 + 28
draw.text((icon_cx, label_y),   'CodexSwitch',  font=f_label, fill=WHITE,   anchor='mt')
draw.text((folder_cx, label_y), 'Applications', font=f_label, fill=WHITE,   anchor='mt')

# ── Instruction line ─────────────────────────────────────────────────────────
instr_y = label_y + 72
draw.text((W // 2, instr_y),
          '将 CodexSwitch.app 拖入 Applications 文件夹',
          font=f_instr, fill=BLUE_LT, anchor='mm')

# ── Footer note ───────────────────────────────────────────────────────────────
note_y = H - 56
draw.text((W // 2, note_y),
          '⚡  首次运行请右键点击图标 → 打开 · 安装后从菜单栏 ⚡ 启动',
          font=f_note, fill=GRAY, anchor='mm')

# Divider line above footer
draw.line([(100, note_y - 28), (W - 100, note_y - 28)], fill=(60, 80, 140, 120), width=1)

# ── Save ─────────────────────────────────────────────────────────────────────
out_path = os.path.join(ASSETS, 'dmg_background.png')
img.convert('RGB').save(out_path, dpi=(144, 144))
print(f'  dmg_background.png  ({W}x{H} @144dpi)')

# ─────────────────────────────────────────────────────────────────────────────
# Usage guide (plain UTF-8 text, opens in TextEdit / any editor)
# ─────────────────────────────────────────────────────────────────────────────
GUIDE = """\
CodexSwitch 使用指南
====================

【快速开始】

1. 将 CodexSwitch.app 拖入 Applications（应用程序）文件夹
2. 从 Launchpad 或 Spotlight 启动 CodexSwitch
3. 首次运行：右键点击图标 → 「打开」（绕过 Gatekeeper 安全提示）
4. 点击菜单栏的 ⚡ 图标打开面板
5. 输入 DeepSeek API Key（格式：sk-xxxx）
6. 选择模型（V4 Pro 推荐 / V4 Flash 更快）
7. 打开 DeepSeek 开关，状态显示「运行中」即可使用

【使用说明】

• 开关 ON：Codex 将调用 DeepSeek 模型（显示 DeepSeek V4 Pro）
• 开关 OFF：停止代理，Codex 恢复默认设置
• API Key 自动保存，重启后无需重新输入
• 切换模型后需重新开启开关生效

【获取 API Key】

访问 https://platform.deepseek.com
→ 注册登录 → API Keys → Create

【技术说明】

• 本应用内置预编译的 Moon Bridge 代理程序，无需安装 Go 环境
• 代理运行在本地 127.0.0.1:38440，不向外传输任何数据
• API 请求直接发往 DeepSeek 服务器
• 支持 macOS 12.0+，arm64 及 Intel 通用二进制
"""

guide_path = os.path.join(ASSETS, '使用指南.txt')
with open(guide_path, 'w', encoding='utf-8') as f:
    f.write(GUIDE)
print('  使用指南.txt')
