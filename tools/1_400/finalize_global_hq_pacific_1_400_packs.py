import json
import os
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = Path(os.environ.get("NOVOATLAS_OUTPUT_ROOT", PROJECT_ROOT / "outputs"))
HQ_ROOT = Path(os.environ.get(
    "NOVOATLAS_1_400_HQ_ROOT",
    str(OUT_ROOT / "HQ_1_400_Pacific_FullRoute"),
))
ORIGINAL_PACK = HQ_ROOT / "OriginalRichOre_1_400_HQ_Pacific_FullRoute"
TOP100_PACK = HQ_ROOT / "Top100RichOre_1_400_HQ_Pacific_FullRoute"
QUICK_TOP100_PACK = OUT_ROOT / "FINAL_PACKS_1_400_Pacific" / "Top100RichOre_1_400_Pacific_Tiled"
DATA_ID = "global_1_400_pacific_tiled_v1"
STATE_PATH = HQ_ROOT / "world_1_400_global_hq_pacific_region_queue_state.json"
SUMMARY_PATH = HQ_ROOT / "FINAL_DELIVERY_SUMMARY_1_400_HQ_PACIFIC_FULL_ROUTE.json"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_tiles(pack, kind):
    path = pack / "data/world/novoatlas" / DATA_ID / kind
    return len(list(path.glob("*.png"))) if path.exists() else 0


def copy_top100_pack():
    if TOP100_PACK.exists():
        shutil.rmtree(TOP100_PACK)
    shutil.copytree(ORIGINAL_PACK, TOP100_PACK)

    src_ore = QUICK_TOP100_PACK / "data/world/novoatlas" / DATA_ID / "ore"
    dst_ore = TOP100_PACK / "data/world/novoatlas" / DATA_ID / "ore"
    if not src_ore.exists():
        raise FileNotFoundError(src_ore)
    if dst_ore.exists():
        shutil.rmtree(dst_ore)
    shutil.copytree(src_ore, dst_ore)

    meta_path = TOP100_PACK / "pack.mcmeta"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pack"]["description"] = "NovoAtlas global 1:400 Pacific HQ full-route assembly: Top100 rich ore"
    write_json(meta_path, meta)


def main():
    if not ORIGINAL_PACK.exists():
        raise FileNotFoundError(ORIGINAL_PACK)
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    completed = len(state.get("completed", []))
    total = int(state.get("total_regions", 432))
    failed = len(state.get("failed", []))
    if completed < total or failed:
        raise SystemExit(f"Queue is not cleanly complete: completed={completed}/{total}, failed={failed}")

    copy_top100_pack()
    summary = {
        "status": "ready",
        "scale": "1 block ~= 400 m",
        "route": "Full 1:200-style geographic shard route, 432 regions, Pacific-centered tiled assembly.",
        "original_rich_ore_pack": str(ORIGINAL_PACK),
        "top100_rich_ore_pack": str(TOP100_PACK),
        "state": str(STATE_PATH),
        "manifest": str(HQ_ROOT / "world_1_400_global_hq_pacific_manifest.json"),
        "tile_counts": {
            "original": {
                "height": count_tiles(ORIGINAL_PACK, "height"),
                "surface": count_tiles(ORIGINAL_PACK, "surface"),
                "ore": count_tiles(ORIGINAL_PACK, "ore"),
            },
            "top100": {
                "height": count_tiles(TOP100_PACK, "height"),
                "surface": count_tiles(TOP100_PACK, "surface"),
                "ore": count_tiles(TOP100_PACK, "ore"),
            },
        },
    }
    write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
