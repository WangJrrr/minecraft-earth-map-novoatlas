# Compatibility and Zinc

[English](COMPATIBILITY.md) | [简体中文](../zh-CN/COMPATIBILITY_zh-CN.md)

## Required Mod Content

Current release packages reference:

```text
create:zinc_ore
create:deepslate_zinc_ore
create:zinc_block
```

Create is therefore required. Without those registry entries, Minecraft may reject the datapack before world creation.

## Why Zinc Is Not Replaced with Copper or Iron

Zinc districts come from zinc mineral data. Silently replacing them with copper or iron would alter the represented commodity. The official rich-ore editions preserve zinc and declare Create as a dependency.

## No-Create / No-Custom-Ore Variant

Do not remove only the zinc JSON files. Ore colors encode multi-mineral combinations, and deleting isolated files leaves dangling references.

Use:

```powershell
python tools\ore\make_no_custom_ore_variant.py SOURCE_DATAPACK OUTPUT_DATAPACK
```

The tool removes the entire custom cave-biome ore layer while retaining height and surface data. It also checks that no `create:`, `world:ore_combo_*`, or rich-feature references remain.

## Underground Structures

Rich-ore regions replace the original cave biome with `world:ore_combo_*`. This may remove deep dark and lush cave identities and suppress amethyst geodes, ancient cities, cave decoration, or modded structures that depend on original biome tags.

The no-custom-ore variant is currently the most reliable option when underground compatibility is more important than geographically controlled rich ores.
