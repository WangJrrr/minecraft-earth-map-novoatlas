import argparse
import json
import os
from pathlib import Path

from PIL import Image


Image.MAX_IMAGE_PIXELS = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
ASSEMBLY = OUT_ROOT / "NovoAtlas_World_1block200m_Global_HQ_Pacific_Assembly"
MANIFEST = OUT_ROOT / "world_1_200_global_hq_pacific_manifest.json"
WIDTH = 163840
HEIGHT = 92160
TILE_SIZE = 2048
SEAM_WEST_LON = -31.5


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lonlat_to_global_pixel(lon, lat):
    shifted_lon = (lon - SEAM_WEST_LON) % 360.0
    x = int(round(shifted_lon / 360.0 * WIDTH))
    z = int(round((90.0 - lat) / 180.0 * HEIGHT))
    return x, z


def find_region_image(pack, kind):
    root = pack / "data/world/novoatlas" / ("heightmap" if kind == "height" else "biome_map")
    images = sorted(root.glob("*.png"))
    if not images:
        raise FileNotFoundError(f"No {kind} image under {root}")
    return images[0]


def paste_crop_wrapped(tile_dir, source, src_box, global_x, global_z):
    crop = source.crop(src_box)
    remaining = crop.width
    offset = 0
    while remaining > 0:
        x_wrapped = (global_x + offset) % WIDTH
        run = min(remaining, WIDTH - x_wrapped)
        sub = crop.crop((offset, 0, offset + run, crop.height))
        tx0, tx1 = x_wrapped // TILE_SIZE, (x_wrapped + run - 1) // TILE_SIZE
        tz0, tz1 = global_z // TILE_SIZE, (global_z + crop.height - 1) // TILE_SIZE
        for tz in range(tz0, tz1 + 1):
            for tx in range(tx0, tx1 + 1):
                tile_path = tile_dir / f"{tx}_{tz}.png"
                tile = Image.open(tile_path).copy()
                gx0 = tx * TILE_SIZE
                gz0 = tz * TILE_SIZE
                ix0 = max(x_wrapped, gx0)
                iz0 = max(global_z, gz0)
                ix1 = min(x_wrapped + run, gx0 + TILE_SIZE)
                iz1 = min(global_z + crop.height, gz0 + TILE_SIZE)
                piece = sub.crop((ix0 - x_wrapped, iz0 - global_z, ix1 - x_wrapped, iz1 - global_z))
                tile.paste(piece, (ix0 - gx0, iz0 - gz0))
                tile.save(tile_path, optimize=True)
        remaining -= run
        offset += run


def patch_layer(region_pack, kind, bbox):
    source_path = find_region_image(region_pack, kind)
    source = Image.open(source_path)
    width, height = source.size
    x0, z0 = lonlat_to_global_pixel(bbox["west"], bbox["north"])
    tile_dir = ASSEMBLY / "data/world/novoatlas/global_1_200_full_tiled_v1" / kind
    paste_crop_wrapped(tile_dir, source, (0, 0, width, height), x0, z0)
    tx_count = (width + TILE_SIZE - 1) // TILE_SIZE
    tz_count = (height + TILE_SIZE - 1) // TILE_SIZE
    return {
        "kind": kind,
        "source": str(source_path),
        "start_pixel": {"x": x0, "z": z0},
        "estimated_touched_tiles": tx_count * tz_count,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region-pack", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--west", type=float, required=True)
    parser.add_argument("--south", type=float, required=True)
    parser.add_argument("--east", type=float, required=True)
    parser.add_argument("--north", type=float, required=True)
    args = parser.parse_args()

    region_pack = Path(args.region_pack)
    bbox = {"west": args.west, "south": args.south, "east": args.east, "north": args.north}
    height = patch_layer(region_pack, "height", bbox)
    surface = patch_layer(region_pack, "surface", bbox)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest.setdefault("regions", []).append(
        {
            "name": args.name,
            "region_pack": str(region_pack),
            "bbox": bbox,
            "height_patch": height,
            "surface_patch": surface,
        }
    )
    write_json(MANIFEST, manifest)
    print(json.dumps({"assembly_pack": str(ASSEMBLY), "manifest": str(MANIFEST), "patched": manifest["regions"][-1]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
