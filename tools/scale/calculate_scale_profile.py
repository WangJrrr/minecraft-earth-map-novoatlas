import argparse
import json
import math
from pathlib import Path


BASE_SCALE = 200.0
BASE_WIDTH = 163840
BASE_HEIGHT = 92160
BASE_SHARD_PIXELS = 6144


def build_profile(scale, tile_size):
    factor = BASE_SCALE / scale
    width = round(BASE_WIDTH * factor)
    height = round(BASE_HEIGHT * factor)
    shard = BASE_SHARD_PIXELS * factor
    tiles_x = math.ceil(width / tile_size)
    tiles_z = math.ceil(height / tile_size)
    return {
        "scale": f"1:{scale:g}",
        "scale_denominator": scale,
        "relative_to_1_200_linear": factor,
        "relative_to_1_200_pixels": factor * factor,
        "global_width": width,
        "global_height": height,
        "nominal_standard_shard_pixels": shard,
        "tile_size": tile_size,
        "tiles_x": tiles_x,
        "tiles_z": tiles_z,
        "tiles_per_layer": tiles_x * tiles_z,
        "partial_last_tile_x": width % tile_size != 0,
        "partial_last_tile_z": height % tile_size != 0,
        "recommended_dataset_id": f"global_1_{scale:g}_pacific_tiled_v1".replace(".", "p"),
        "notes": [
            "Keep the same 432 geographic regions for comparable geographic detail.",
            "Compute each region edge from global coordinates; do not repeatedly add a rounded shard width.",
            "Use a scale-specific cache and output directory.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate a NovoAtlas Earth-map scale profile.")
    parser.add_argument("--scale", type=float, required=True, help="Scale denominator, for example 300")
    parser.add_argument("--tile-size", type=int, default=2048)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.scale <= 0 or args.tile_size <= 0:
        raise ValueError("Scale and tile size must be positive")
    profile = build_profile(args.scale, args.tile_size)
    text = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
