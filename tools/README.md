# Build Tools

[English](README.md) | [简体中文](README.zh-CN.md)

These Python scripts form the offline pipeline used to create the published datapacks.

```text
1_200/    1:200 geographic region generation, queueing and assembly
1_400/    1:400 river/Antarctica-corrected generation and assembly
ore/      mineral datasets, rich-ore tiles and no-custom-ore variants
pipeline/ shared geographic classification and earlier pipeline utilities
scale/    scale-profile and coordinate-conversion utilities
```

Players installing a Release datapack do not need to run these scripts. They are included for reproducibility, custom scales and further development.

- `ore/make_no_custom_ore_variant.py` preserves height and surface data while removing the custom cave-biome ore layer and the project's Create zinc dependency.
- `scale/calculate_scale_profile.py --scale <denominator>` calculates global dimensions and NovoAtlas tile counts for scales such as 1:100, 1:300 and 1:800.
- `scale/convert_coordinates.py` converts Pacific-centered longitude/latitude to Minecraft X/Z and back.
- `ore/build_top100_rich_ore_dataset.py` and `ore/make_global_top100_rich_ore_layer_tiles.py` read `NOVOATLAS_SCALE_DENOMINATOR` when producing scale-specific ore coordinates and tiles.

Public scripts use environment variables for output, cache and source-data locations where applicable:

```text
NOVOATLAS_OUTPUT_ROOT
NOVOATLAS_CACHE_ROOT
NOVOATLAS_PIPELINE_ROOT
NOVOATLAS_MINERAL_INPUT_ROOT
NOVOATLAS_1_400_HQ_ROOT
NOVOATLAS_SCALE_DENOMINATOR
```

Raw WorldCover, WorldClim, HydroRIVERS, elevation data and intermediate caches are intentionally not included. Install Python dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```
