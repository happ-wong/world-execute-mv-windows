#!/usr/bin/env python3
"""Render MV frames to a PNG contact sheet so the output can be eyeballed.

    python tools/render_frames.py --times 12,35,68,100,133,168,200
Writes tools/frames.png
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import player  # noqa: E402

CELL_W, CELL_H = 7, 15
BACK = (10, 10, 14)
STYLE_COLOR = {0: 137, 1: 215, 2: 221, 3: 230, 4: 203, 5: 94, 6: 58}
BOLD = {2, 3, 4}


def xterm(index):
    if index < 16:
        base = [(0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0), (0, 0, 128),
                (128, 0, 128), (0, 128, 128), (192, 192, 192), (128, 128, 128),
                (255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 0, 255), (255, 0, 255),
                (0, 255, 255), (255, 255, 255)]
        return base[index]
    if index < 232:
        steps = (0, 95, 135, 175, 215, 255)
        index -= 16
        return tuple(steps[v] for v in (index // 36, (index // 6) % 6, index % 6))
    level = 8 + (index - 232) * 10
    return (level, level, level)


def palette():
    colors = {}
    for style, index in STYLE_COLOR.items():
        rgb = xterm(index)
        if style in BOLD:
            rgb = tuple(min(255, int(channel * 1.15) + 12) for channel in rgb)
        colors[style] = rgb
    return colors


def fonts():
    def load(path, size):
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            return ImageFont.load_default()
    windows = Path('C:/Windows/Fonts')
    ascii_font = load(windows / 'consola.ttf', 14)
    if not (windows / 'consola.ttf').exists():
        ascii_font = load(windows / 'arial.ttf', 14)
    cjk_font = load(windows / 'msyh.ttc', 14)
    if not (windows / 'msyh.ttc').exists():
        cjk_font = load(windows / 'PingFang.ttc', 14)
    return ascii_font, cjk_font


def draw(canvas, image, origin, fonts_pair):
    ascii_font, cjk_font = fonts_pair
    colors = palette()
    draw = ImageDraw.Draw(image)
    for row_index, row in enumerate(canvas.cells):
        column = 0
        while column < canvas.w:
            char, style = row[column]
            if not char:
                column += 1
                continue
            wide = player.cw(char) == 2
            if char:
                draw.text((origin[0] + column * CELL_W, origin[1] + row_index * CELL_H), char,
                          fill=colors.get(style, (200, 200, 200)),
                          font=cjk_font if wide else ascii_font)
            column += 2 if wide else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--times', default='12,35,68,100,133,168,200')
    parser.add_argument('--width', type=int, default=120)
    parser.add_argument('--height', type=int, default=40)
    parser.add_argument('--columns', type=int, default=3)
    parser.add_argument('--out', default=str(ROOT / 'tools' / 'frames.png'))
    args = parser.parse_args()
    marks = [float(part) for part in re.split(r'[,\s]+', args.times.strip()) if part]
    film = player.Film()
    frame_w = args.width * CELL_W
    frame_h = args.height * CELL_H + 22
    cols = min(args.columns, len(marks))
    rows = (len(marks) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * frame_w, rows * frame_h), BACK)
    fonts_pair = fonts()
    for index, mark in enumerate(marks):
        canvas = film.render(mark, args.width - 1, args.height, False, 0.0, False, False)
        origin = ((index % cols) * frame_w, (index // cols) * frame_h)
        ImageDraw.Draw(sheet).rectangle(
            (origin[0], origin[1], origin[0] + frame_w, origin[1] + 22), fill=(24, 24, 30))
        ImageDraw.Draw(sheet).text((origin[0] + 6, origin[1] + 4),
                                   f't = {mark:.1f}s   {args.width}x{args.height}',
                                   fill=(190, 190, 190), font=fonts_pair[0])
        draw(canvas, sheet, (origin[0], origin[1] + 22), fonts_pair)
    sheet.save(args.out)
    print(f'{args.out}  {sheet.size[0]}x{sheet.size[1]}  {len(marks)} frames')
    return 0


if __name__ == '__main__':
    sys.exit(main())
