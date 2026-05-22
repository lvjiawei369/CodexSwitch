#!/usr/bin/env python3
"""生成 CodexSwitch 图标 (icns + ico)，需要 pip install pillow"""
import subprocess, os, struct, zlib
from pathlib import Path

SIZES = [16, 32, 64, 128, 256, 512, 1024]
ASSETS = Path(__file__).parent / "assets"
ASSETS.mkdir(exist_ok=True)

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("请先运行: pip3 install pillow")
    raise

def make_base(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Dark circle background
    m = size // 16
    d.ellipse([m, m, size - m, size - m], fill="#1e1e2e")
    # Green ring
    rw = max(2, size // 32)
    d.ellipse([m, m, size - m, size - m], outline="#a6e3a1", width=rw)
    # Lightning bolt drawn with polygon
    cx, cy = size / 2, size / 2
    s = size * 0.28
    bolt = [
        (cx + s * 0.12,  cy - s * 0.9),
        (cx - s * 0.18,  cy - s * 0.05),
        (cx + s * 0.14,  cy - s * 0.05),
        (cx - s * 0.12,  cy + s * 0.9),
        (cx + s * 0.28,  cy + s * 0.08),
        (cx - s * 0.04,  cy + s * 0.08),
    ]
    d.polygon(bolt, fill="#f9e2af")
    return img

# Generate PNG for each size
pngs = {}
for sz in SIZES:
    img = make_base(sz)
    p = ASSETS / f"icon_{sz}.png"
    img.save(p)
    pngs[sz] = p
    print(f"  icon_{sz}.png")

# ── macOS .icns ───────────────────────────────────────────────────────────────
iconset = ASSETS / "icon.iconset"
iconset.mkdir(exist_ok=True)
ICNS_MAP = {
    16: "icon_16x16", 32: "icon_16x16@2x",
    32: "icon_32x32", 64: "icon_32x32@2x",
    128: "icon_128x128", 256: "icon_128x128@2x",
    256: "icon_256x256", 512: "icon_256x256@2x",
    512: "icon_512x512", 1024: "icon_512x512@2x",
}
for sz, name in ICNS_MAP.items():
    make_base(sz).save(iconset / f"{name}.png")

r = subprocess.run(
    ["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "icon.icns")],
    capture_output=True, text=True,
)
if r.returncode == 0:
    print("✓ assets/icon.icns")
else:
    print(f"✗ iconutil 失败: {r.stderr.strip()}")

# ── Windows .ico ──────────────────────────────────────────────────────────────
ico_sizes = [16, 32, 48, 64, 128, 256]
ico_images = [make_base(s).convert("RGBA") for s in ico_sizes]
(ASSETS / "icon.ico").write_bytes(b"")  # placeholder
ico_images[0].save(
    str(ASSETS / "icon.ico"),
    format="ICO",
    sizes=[(s, s) for s in ico_sizes],
    append_images=ico_images[1:],
)
print("✓ assets/icon.ico")
print("\n完成！图标已生成到 assets/ 目录")
