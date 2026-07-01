import argparse
import json
import re
import shutil
from pathlib import Path


RICH_FEATURE = re.compile(r"(?:_rich_(?:vein|core)|_t[1-5]_rich_(?:vein|core))\.json$")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remove_cave_layers(pack):
    changed = 0
    for path in pack.glob("data/*/novoatlas/map_info/*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.pop("cave_biomes", None) is not None:
            write_json(path, value)
            changed += 1
    return changed


def remove_ore_tiles(pack):
    removed = []
    for path in pack.glob("data/*/novoatlas/*/ore"):
        if path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path.relative_to(pack)))
    return removed


def remove_rich_worldgen(pack):
    removed = []
    worldgen = pack / "data" / "world" / "worldgen"
    biome_dir = worldgen / "biome"
    if biome_dir.exists():
        for path in biome_dir.glob("ore_combo_*.json"):
            path.unlink()
            removed.append(str(path.relative_to(pack)))
    for folder in ("configured_feature", "placed_feature"):
        root = worldgen / folder
        if root.exists():
            for path in root.glob("*.json"):
                if RICH_FEATURE.search(path.name):
                    path.unlink()
                    removed.append(str(path.relative_to(pack)))
    return removed


def clean_biome_tags(pack):
    changed = 0
    for path in pack.glob("data/*/tags/worldgen/biome/*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        values = value.get("values")
        if not isinstance(values, list):
            continue
        filtered = [item for item in values if not (isinstance(item, str) and item.startswith("world:ore_combo_"))]
        if filtered != values:
            value["values"] = filtered
            write_json(path, value)
            changed += 1
    return changed


def update_description(pack):
    path = pack / "pack.mcmeta"
    value = json.loads(path.read_text(encoding="utf-8"))
    description = value.get("pack", {}).get("description", "Minecraft Earth Map for NovoAtlas - TerraScale")
    value.setdefault("pack", {})["description"] = f"{description} (no custom rich ore; no Create dependency)"
    write_json(path, value)


def find_forbidden_references(pack):
    matches = []
    for path in pack.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        if "create:" in text or "world:ore_combo_" in text or "_rich_vein" in text or "_rich_core" in text:
            matches.append(str(path.relative_to(pack)))
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Create a no-custom-rich-ore, no-Create variant without rebuilding terrain."
    )
    parser.add_argument("source", type=Path, help="Existing unpacked Earth-map datapack")
    parser.add_argument("output", type=Path, help="New datapack directory to create")
    args = parser.parse_args()

    if not (args.source / "pack.mcmeta").exists():
        raise FileNotFoundError(f"Not a datapack: {args.source}")
    if args.output.exists():
        raise FileExistsError(f"Output already exists: {args.output}")

    shutil.copytree(args.source, args.output)
    cave_maps = remove_cave_layers(args.output)
    ore_dirs = remove_ore_tiles(args.output)
    worldgen_files = remove_rich_worldgen(args.output)
    biome_tags = clean_biome_tags(args.output)
    update_description(args.output)

    forbidden = find_forbidden_references(args.output)
    if forbidden:
        raise RuntimeError("Custom ore references remain:\n" + "\n".join(forbidden))

    print(json.dumps({
        "output": str(args.output),
        "map_info_files_updated": cave_maps,
        "ore_directories_removed": len(ore_dirs),
        "worldgen_files_removed": len(worldgen_files),
        "biome_tags_updated": biome_tags,
        "create_dependency_removed": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
