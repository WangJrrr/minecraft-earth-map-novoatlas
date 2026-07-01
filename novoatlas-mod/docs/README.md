# NovoAtlas 瓦片化地图 — 文档索引

## 文件说明

| 文件 | 内容 |
|------|------|
| [`API.md`](./API.md) | 类结构、数据流、线程安全策略 |
| [`USAGE.md`](./USAGE.md) | 使用指南（瓦片切割、JSON 配置、数据包结构） |
| [`split_tiles.py`](./split_tiles.py) | 瓦片切割 Python 脚本 |
| [`example-datapack/`](./example-datapack/) | 完整示例数据包 |

## 快速开始

### 1. 切割瓦片

```bash
pip install Pillow
python split_tiles.py world_height.png tiles/height/ --prefix height
python split_tiles.py world_biome.png tiles/biome/ --prefix biome
```

### 2. 放入数据包

```
your_datapack/
└── data/
    └── your_namespace/
        ├── novoatlas/map_info/your_world.json
        ├── height/    ← 瓦片放这里
        ├── biome/     ← 群系瓦片
        └── dimension/your_world.json
```

### 3. 修改 JSON

`height_map` 从字符串改为对象：

```json
{
    "height_map": {
        "tile_size": 1024,
        "tiles": "your_namespace:height/{tx}_{tz}.png",
        "width": 81920,
        "height": 46080
    }
}
```

### 4. 启动服务器

把数据包放进 `world/datapacks/`，创建世界时选择 `novoatlas:image_map` 类型的维度。

## 关键参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `tile_size` | 1024 | 瓦片边长。太小→IO多，太大→内存大 |
| `interpolation` | `bilinear` | 地形平滑。大缩放时用 `lanczos` |
| 缓存大小 | 64 张 | `TileImageCache.DEFAULT_MAX_TILES` |

## 兼容性

- **完全向后兼容**：`"height_map": "namespace:key"` 格式不变
- **可混用**：高度图用瓦片、群系图用单张
- **纯服务端**：客户端不需要安装模组或瓦片文件
