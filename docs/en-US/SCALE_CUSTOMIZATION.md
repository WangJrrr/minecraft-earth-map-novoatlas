# Custom Scales: 1:100, 1:300, 1:800, and Others

[English](SCALE_CUSTOMIZATION.md) | [简体中文](../zh-CN/SCALE_CUSTOMIZATION_zh-CN.md)

## Scale Formula

Custom scales are derived linearly from the existing 1:200 grid. For target denominator `S`:

```text
F = 200 / S
width = round(163840 × F)
height = round(92160 × F)
nominal standard-region pixels = 6144 × F
relative pixel work ≈ F²
```

This preserves the project's layout and aspect ratio. It does not redefine projection or automatically change vertical height compression.

## Calculator

```powershell
python tools\scale\calculate_scale_profile.py --scale 300
python tools\scale\calculate_scale_profile.py --scale 100 --output profiles\1_100.json
```

## Common Profiles

| Scale | Global dimensions | Nominal region | 2048 tiles/layer | Relative pixels |
|---|---:|---:|---:|---:|
| 1:100 | 327680 x 184320 | 12288 | 14400 | 400% |
| 1:200 | 163840 x 92160 | 6144 | 3600 | 100% |
| 1:300 | 109227 x 61440 | 4096 | 1620 | 44.44% |
| 1:400 | 81920 x 46080 | 3072 | 920 | 25% |
| 1:800 | 40960 x 23040 | 1536 | 240 | 6.25% |

Tile count is `ceil(width/2048) × ceil(height/2048)`. The last row or column may be padded while map info retains the true dimensions.

## Values That Must Stay Synchronized

Changing only `horizontal_scale` is insufficient. Update:

1. builder `GLOBAL_WIDTH` and `GLOBAL_HEIGHT`;
2. region pixel-edge calculations;
3. assembly patcher width and height;
4. height, surface, and Ore map-info dimensions;
5. mineral coordinate conversion dimensions;
6. Ore `TILES_X`, `TILES_Z`, and paths;
7. a unique dataset ID such as `global_1_300_pacific_tiled_v1`;
8. scale-specific cache, state, log, and package names.

Relevant files include region builders, Pacific patchers, queue scripts, mineral ranking, Ore-layer generation, final assembly scripts, and final `map_info/world.json`.

Copy an existing tool directory to a new scale directory instead of overwriting 1:200 or 1:400.

## Region Boundaries

For scales such as 1:300, do not repeatedly add a rounded fixed region width. Calculate each edge from global coordinates:

```python
left = round((west - seam_west) % 360 / 360 * global_width)
right = round((east - seam_west) % 360 / 360 * global_width)
top = round((90 - north) / 180 * global_height)
bottom = round((90 - south) / 180 * global_height)
```

Adjacent regions then share the same computed edge and avoid cumulative one-pixel errors. Pacific-seam regions must be split into right and left writes when modular coordinates wrap.

## Concrete 1:300 Example

```powershell
python tools\scale\calculate_scale_profile.py --scale 300 --output profiles\1_300.json
Copy-Item tools\1_200 tools\1_300 -Recurse
```

Use:

```text
GLOBAL_WIDTH = 109227
GLOBAL_HEIGHT = 61440
NOMINAL_STANDARD_SHARD = 4096
TILE_SIZE = 2048
TILES_X = 54
TILES_Z = 30
DATA_ID = global_1_300_pacific_tiled_v1
```

Replace scale-specific output identifiers throughout `tools/1_300`. Keep geographic bounding boxes unchanged; scale changes pixels per region, not geographic coverage.

Generate one test region before a global queue:

```powershell
python tools\1_300\build_high_quality_region_from_v5_pipeline.py `
  --name test_east_asia `
  --west 116 --south 24 --east 129.5 --north 36
```

The final 1:300 column is partial because width 109227 is not divisible by 2048. Pad the PNG tile but keep `109227` in map info. Rebuild the Ore layer at the same dimensions; reusing 1:200 or 1:400 Ore tiles would shift every mining district.

## Recommended Workflow

1. Generate a scale profile.
2. Create scale-specific script copies and dataset IDs.
3. Keep 432 geographic regions for comparable processing detail.
4. Use independent cache and output roots.
5. Test East Asia, South America, Europe, Antarctica, and the Pacific seam.
6. Assemble a 2 x 2 region group and inspect boundaries.
7. Run the global surface queue.
8. Rebuild the Ore layer at exactly the same dimensions.

## Tradeoffs

- **1:100:** four times the 1:200 pixel count and sixteen times the 1:400 count; very expensive but detailed.
- **1:300:** balanced, with exact 4096-pixel nominal regions but a partial final global tile column.
- **1:800:** lightweight, but narrow rivers, lakes, and islands are easier to lose. Hydrology thresholds may need scale-aware adjustment.

Horizontal scale changes do not require vertical-scale changes. Altering sea level, peak compression, snow lines, caves, or structure height is a separate world-generation design task.
