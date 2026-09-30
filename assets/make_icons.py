#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 travel-intel 全套图标：1024/512/192/apple-touch-icon/favicon。
风格与看板一致：暖白底 + 低饱和品牌蓝山形线条 + 琥珀太阳。"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BG = (247, 245, 240, 255)      # 暖白
BLUE = (74, 123, 166, 255)     # 低饱和品牌蓝
BLUE_L = (158, 192, 220, 255)  # 浅蓝（远山）
AMBER = (217, 154, 78, 255)    # 琥珀（太阳）

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 圆角底
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=200, fill=BG)

# 太阳（右上）
d.ellipse([660, 170, 860, 370], outline=AMBER, width=44)

# 远山（浅蓝，实心弱化）
d.polygon([(120, 780), (430, 420), (620, 780)], fill=BLUE_L)

# 主山（品牌蓝，粗线）
d.line([(120, 800), (450, 380), (700, 800)], fill=BLUE, width=48, joint="curve")
d.line([(430, 800), (650, 540), (900, 800)], fill=BLUE, width=48, joint="curve")

# 地平线
d.line([(120, 810), (904, 810)], fill=BLUE, width=36)

# 导出各尺寸
out = {
    "icon-1024.png": 1024,
    "icon-512.png": 512,
    "icon-192.png": 192,
    "apple-touch-icon.png": 180,
    "favicon.png": 64,
}
for name, size in out.items():
    img.resize((size, size), Image.LANCZOS).save(os.path.join(ROOT, name))
    print("+", name, size)
