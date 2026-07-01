# Ore Profiles, No-Create Builds, and Modded Ores

[English](ORE_CUSTOMIZATION.md) | [简体中文](../zh-CN/ORE_CUSTOMIZATION_zh-CN.md)

Height, surface, and underground ore control are independent. Most ore changes do not require rebuilding Earth terrain.

## Remove All Custom Rich Ores

```powershell
python tools\ore\make_no_custom_ore_variant.py `
  "D:\packs\Top100RichOre_1_400_HQ_Pacific_FullRoute" `
  "D:\packs\EarthMap_1_400_NoCustomOre"
```

The tool copies the pack, removes `cave_biomes` from map info, deletes Ore PNGs, deletes `ore_combo_*` biomes and rich features, cleans biome tags, and verifies that custom ore or Create references do not remain.

Height and surface tiles are preserved. Underground generation returns to the normal biome and mod rules, which is also the recommended choice for preserving ancient cities, deep dark, lush caves, amethyst geodes, and modded underground structures.

## Keep Rich Ores but Remove Create Zinc

Do not delete only zinc JSON files. Multi-mineral colors and cave biomes would retain dangling references.

Correct process:

1. Remove zinc matching rules from `build_top100_rich_ore_dataset.py`.
2. Remove zinc from the `ORES` dictionary.
3. Filter deposits whose `ore` is `zinc`.
4. Rebuild the entire Ore layer and combination palette.
5. Merge the new Ore payload into the terrain pack.
6. Search the result for `create:`.

Changing the `ORES` order changes combination codes; old Ore colors cannot be reused.

## Add Another Modded Ore

Define registry IDs, vein size, count, and height range in `ORES`, then add matching deposit records. Client and server must both install the providing mod.

If the mod lacks a storage block, disable that mineral's high-tier core or use its ore block. Too many minerals can create excessive cave-biome combinations and datapack size.

## Adjust Prosperity

`TIERS` controls rank boundaries, density, radius, and core fraction. Per-mineral settings control vein shape and vertical placement. Rebuilding only the Ore payload is sufficient after these changes.

Always test a small world first to catch excessive density, missing registry IDs, invalid heights, or cave-content regressions.
