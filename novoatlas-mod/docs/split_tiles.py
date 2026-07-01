#!/usr/bin/env python3
"""
NovoAtlas 瓦片切割工具
将一张大尺寸 PNG（高度图或群系图）切割为瓦片。

用法:
    python split_tiles.py input.png output_dir/ --size 1024 --prefix height

输出命名规则: output_dir/height_0_0.png, height_0_1.png, ...
"""

import argparse
import os
import sys
from PIL import Image


def split_image(
    input_path: str,
    output_dir: str,
    tile_size: int = 1024,
    prefix: str = "tile",
    ext: str = ".png",
):
    print(f"正在打开: {input_path}")
    img = Image.open(input_path)
    width, height = img.size
    print(f"图片尺寸: {width} x {height} 像素")

    tiles_x = (width + tile_size - 1) // tile_size
    tiles_z = (height + tile_size - 1) // tile_size
    print(f"瓦片网格: {tiles_x} x {tiles_z} = {tiles_x * tiles_z} 张")
    print(f"输出目录: {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    count = 0
    for tx in range(tiles_x):
        for tz in range(tiles_z):
            left = tx * tile_size
            upper = tz * tile_size
            right = min(left + tile_size, width)
            lower = min(upper + tile_size, height)

            tile = img.crop((left, upper, right, lower))

            # 如果瓦片不是完整尺寸，用黑色填充
            if tile.size != (tile_size, tile_size):
                padded = Image.new(img.mode, (tile_size, tile_size), 0)
                padded.paste(tile, (0, 0))
                tile = padded

            filename = f"{prefix}_{tx}_{tz}{ext}"
            tile.save(os.path.join(output_dir, filename))
            count += 1

            if count % 100 == 0:
                print(f"  已处理 {count} 张瓦片...")

    print(f"完成! 共生成 {count} 张瓦片")
    print(f"\n在 map_info JSON 中使用以下配置:")
    print(f'  "tile_size": {tile_size},')
    print(f'  "tiles": "YOUR_NAMESPACE:{prefix}/{{tx}}_{{tz}}{ext}",')
    print(f'  "width": {width},')
    print(f'  "height": {height}')


def main():
    parser = argparse.ArgumentParser(
        description="NovoAtlas 瓦片切割工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python split_tiles.py world_height.png tiles/height/ --prefix height
  python split_tiles.py world_biome.png tiles/biome/ --size 512 --prefix biome_colors
        """,
    )
    parser.add_argument("input", help="输入图片路径")
    parser.add_argument("output_dir", help="输出瓦片的目录")
    parser.add_argument("--size", type=int, default=1024, help="瓦片边长 (默认: 1024)")
    parser.add_argument("--prefix", default="tile", help="文件名前缀 (默认: tile)")
    parser.add_argument("--ext", default=".png", help="文件扩展名 (默认: .png)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 找不到输入文件 '{args.input}'", file=sys.stderr)
        sys.exit(1)

    try:
        split_image(args.input, args.output_dir, args.size, args.prefix, args.ext)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
