# NovoAtlas 瓦片化地图 — 使用指南

> 适用场景：世界地图尺寸很大（如 81920×46080 像素），单张 PNG 无法加载到内存。

---

## 目录

1. [准备工作：切割瓦片](#1-准备工作切割瓦片)
2. [数据包结构](#2-数据包结构)
3. [map_info JSON 配置](#3-map_info-json-配置)
4. [dimension JSON 配置](#4-dimension-json-配置)
5. [完整示例](#5-完整示例)
6. [常见问题](#6-常见问题)

---

## 1. 准备工作：切割瓦片

### 工具推荐

| 工具 | 命令 / 操作 |
|------|-------------|
| **ImageMagick** | `magick world_heightmap.png -crop 1024x1024 height_%d.png` |
| **Python (PIL)** | `Image.crop()` 循环切片 |
| **GIMP** | "图像 → 切片" (Image → Transform → Guillotine) |
| **QGIS** | 搭配 gdal_translate 批量切割 |

### 切片规则

- **瓦片大小**：推荐 1024×1024 像素（可自定义，必须一致）
- **命名规则**：`{tx}_{tz}.png`，其中 `tx` 和 `tz` 是瓦片坐标（从左上角开始）
- **对齐**：左上角第一张瓦片覆盖 (0,0) 到 (tileSize-1, tileSize-1)
- **边缘瓦片**：最后一行/列的瓦片可能小于 tileSize（代码自动 clamp 处理）
- **格式**：支持 PNG、JPG、TIF、BMP、WebP（依赖 TwelveMonkeys ImageIO）

### ImageMagick 示例

```bash
# 假设有一张 81920×46080 的灰度高度图 world_height.png
# 按 1024×1024 切割，瓦片命名 height_0_0.png, height_0_1.png, ...

magick world_height.png \
  -crop 1024x1024 \
  -set filename:tile "%[fx:page.x/1024]_%[fx:page.y/1024]" \
  "height_%[filename:tile].png"
```

### Python (PIL) 示例

```python
from PIL import Image

img = Image.open("world_height.png")
tile_size = 1024
width, height = img.size

for tx in range(0, width, tile_size):
    for tz in range(0, height, tile_size):
        box = (tx, tz, min(tx + tile_size, width), min(tz + tile_size, height))
        tile = img.crop(box)
        tile.save(f"height_{tx//tile_size}_{tz//tile_size}.png")
```

---

## 2. 数据包结构

在你的数据包中创建以下目录结构：

```
your_datapack/
└── data/
    └── your_namespace/
        ├── novoatlas/
        │   └── map_info/
        │       └── your_world.json       ← 地图配置
        │
        ├── height/                        ← 高度图瓦片
        │   ├── 0_0.png
        │   ├── 0_1.png
        │   ├── 1_0.png
        │   └── ...
        │
        ├── biome/                         ← 群系图瓦片（可选）
        │   ├── 0_0.png
        │   ├── 0_1.png
        │   └── ...
        │
        ├── fluid/                         ← 流体高度图瓦片（可选）
        │   ├── 0_0.png
        │   └── ...
        │
        └── dimension/
            └── your_world.json            ← 维度定义

    └── minecraft/
        └── tags/
            └── function/
                └── load.json              ← （可选）/reload 触发
```

**瓦片放在哪？** 瓦片 PNG 必须放在数据包或资源包中，路径必须能被 Minecraft 的 ResourceManager 找到。推荐写清楚 namespace:path。

---

## 3. map_info JSON 配置

### 3.1 高度图 — 单张图片（原有格式，依旧支持）

```json
{
    "height_map": "your_namespace:your_height_map",
    "starting_y": 6,
    "scaling": {
        "horizontal_scale": 1,
        "vertical_scale": 1
    },
    "surface_biomes": { ... }
}
```

### 3.2 高度图 — 瓦片化（新格式）

```json
{
    "height_map": {
        "tile_size": 1024,
        "tiles": "your_namespace:height/{tx}_{tz}.png",
        "width": 81920,
        "height": 46080
    },
    "starting_y": 6,
    "scaling": {
        "horizontal_scale": 1,
        "vertical_scale": 1
    },
    "surface_biomes": { ... }
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `tile_size` | int | ✅ | 每张瓦片的边长（像素）|
| `tiles` | string | ✅ | 瓦片路径模板，`{tx}`=X坐标，`{tz}`=Z坐标 |
| `width` | int | ✅ | 世界总宽度（像素） |
| `height` | int | ✅ | 世界总高度（像素） |

### 3.3 群系图 — 瓦片化

```json
{
    "height_map": { ... },
    "surface_biomes": {
        "map": {
            "tile_size": 1024,
            "tiles": "your_namespace:biome/{tx}_{tz}.png",
            "width": 81920,
            "height": 46080
        },
        "biomes": [
            { "biome": "minecraft:plains",     "color": "#6D923D" },
            { "biome": "minecraft:ocean",      "color": "#313A8B" },
            { "biome": "minecraft:desert",     "color": "#AEA54A" }
        ]
    }
}
```

### 3.4 流体高度图 — 瓦片化

```json
{
    "height_map": { ... },
    "fluid_height_map": {
        "tile_size": 1024,
        "tiles": "your_namespace:fluid/{tx}_{tz}.png",
        "width": 81920,
        "height": 46080
    },
    "surface_biomes": { ... }
}
```

### 3.5 洞穴群系图 — 瓦片化

```json
{
    "height_map": { ... },
    "cave_biomes": {
        "layers": [
            {
                "y_range": { "max": 0 },
                "biomes": {
                    "map": {
                        "tile_size": 1024,
                        "tiles": "your_namespace:cave_biome/{tx}_{tz}.png",
                        "width": 81920,
                        "height": 46080
                    },
                    "biomes": [
                        { "biome": "minecraft:deep_dark", "color": "#000000" }
                    ]
                }
            }
        ]
    }
}
```

---

## 4. dimension JSON 配置

维度定义**不变**，依旧使用 `novoatlas:image_map` chunk generator：

```json
{
    "type": "minecraft:overworld",
    "generator": {
        "type": "novoatlas:image_map",
        "map_info": "your_namespace:your_world",
        "settings": "minecraft:overworld",
        "underground_density_function": "novoatlas:caves",
        "biome_source": {
            "type": "novoatlas:color_map",
            "map_info": "your_namespace:your_world",
            "default_biome": "minecraft:the_void"
        }
    }
}
```

---

## 5. 完整示例

### 数据包结构

```
my_world_datapack/
├── pack.mcmeta
└── data/
    └── myworld/
        ├── novoatlas/
        │   └── map_info/
        │       └── earth.json
        │
        ├── height/           ← 80×45 = 3600 张瓦片
        │   ├── 0_0.png
        │   ├── 0_1.png
        │   ├── ...
        │   └── 79_44.png
        │
        ├── biome/            ← 群系图瓦片（同样数量）
        │   ├── 0_0.png
        │   └── ...
        │
        └── dimension/
            └── earth.json
```

### map_info: `data/myworld/novoatlas/map_info/earth.json`

```json
{
    "starting_y": 6,
    "scaling": {
        "horizontal_scale": {
            "interpolation": "novoatlas:bilinear",
            "value": 1.0
        },
        "vertical_scale": 100.0
    },
    "height_map": {
        "tile_size": 1024,
        "tiles": "myworld:height/{tx}_{tz}.png",
        "width": 81920,
        "height": 46080
    },
    "fluid_height_map": {
        "tile_size": 1024,
        "tiles": "myworld:fluid/{tx}_{tz}.png",
        "width": 81920,
        "height": 46080
    },
    "surface_biomes": {
        "map": {
            "tile_size": 1024,
            "tiles": "myworld:biome/{tx}_{tz}.png",
            "width": 81920,
            "height": 46080
        },
        "biomes": [
            { "biome": "minecraft:ocean",           "color": "#313A8B" },
            { "biome": "minecraft:deep_ocean",      "color": "#10175E" },
            { "biome": "minecraft:warm_ocean",      "color": "#474D90" },
            { "biome": "minecraft:plains",          "color": "#6D923D" },
            { "biome": "minecraft:desert",          "color": "#AEA54A" },
            { "biome": "minecraft:jungle",          "color": "#338C2A" },
            { "biome": "minecraft:taiga",           "color": "#338553" },
            { "biome": "minecraft:jagged_peaks",    "color": "#FFFFFF" },
            { "biome": "minecraft:stony_peaks",     "color": "#939393" },
            { "biome": "minecraft:beach",           "color": "#C4B058" },
            { "biome": "minecraft:stony_shore",     "color": "#525252" }
        ]
    }
}
```

### dimension: `data/myworld/dimension/earth.json`

```json
{
    "type": "minecraft:overworld",
    "generator": {
        "type": "novoatlas:image_map",
        "map_info": "myworld:earth",
        "settings": "minecraft:overworld",
        "underground_density_function": "novoatlas:caves",
        "biome_source": {
            "type": "novoatlas:color_map",
            "map_info": "myworld:earth",
            "default_biome": "minecraft:the_void"
        }
    }
}
```

### pack.mcmeta

```json
{
    "pack": {
        "pack_format": 48,
        "description": "My tiled world datapack"
    }
}
```

---

## 6. 常见问题

### Q: 瓦片数量和内存估算？

**A**: 以 81920×46080 世界，1024×1024 瓦片为例：

| 项目 | 数值 |
|------|------|
| 瓦片总数 | 80×45 = 3600 张 |
| 每张灰度瓦片 | ~1 MB |
| 最多同时缓存 (默认) | 64 张 ≈ 64 MB (灰度) 或 ~256 MB (RGB) |
| 调整缓存大小 | 修改 `TileImageCache` 的 `DEFAULT_MAX_TILES` 常量 |

### Q: 调高缓存大小能提高性能吗？

**A**: 能，但有上限。超过玩家视野范围内的瓦片数量后再增加收益递减。
玩家视野半径 16 chunks ≈ 256 blocks，horizontal_scale=1 时约 256 像素。
一个 1024×1024 瓦片覆盖 1024×1024 像素，所以通常 4-9 张瓦片就覆盖了视野。
64 张默认值已经足够覆盖较快的飞行移动。

### Q: 启动时会不会卡住？

**A**: 不会。瓦片是按需加载的（chunk 生成时），不是启动时全部加载。
首次进入某个区域时会有轻微的延迟（加载该区域的瓦片），但 TileCache 会缓存已加载的瓦片。

### Q: 瓦片文件名格式有限制吗？

**A**: `{tx}` 和 `{tz}` 会被替换为整数（如 `3`, `-2`）。你可以自由选择分隔符：
- `height/{tx}_{tz}.png` → `height/3_-2.png`
- `height/tile_{tx}x{tz}.png` → `height/tile_3x-2.png`

### Q: 已有的单张大图配置需要改吗？

**A**: 不需要。旧格式 `"height_map": "namespace:key"` 完全兼容。
两种格式可以混用——比如高度图用瓦片、群系图用单张。

### Q: 服务端 / 客户端？

**A**: NovoAtlas 是**纯服务端**世界生成模组。瓦片 PNG 必须放在服务端的数据包中。
客户端不需要安装此模组，也不需要有瓦片文件。

### Q: 插值器需要特殊处理吗？

**A**: 不需要。四种插值器（nearest_neighbor、bilinear、bicubic、lanczos）
都已适配 `getPixel()` 接口，自动兼容瓦片化地图。
推荐 bilinear 或 lanczos 以获得平滑的地形过渡。

### Q: 瓦片边缘采样会出问题吗？

**A**: 不会。`TiledMapImage.getPixel()` 会自动：
1. 根据像素坐标计算正确的瓦片
2. 加载相邻瓦片（如果插值需要跨瓦片采样）
3. 对边缘瓦片做 clamp（防止越界）
