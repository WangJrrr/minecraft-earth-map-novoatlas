# 自定义 1:100、1:300、1:800 等比例

## 1. 比例定义

本项目以现有 1:200 网格为基准进行线性缩放。设目标比例分母为 `S`：

```text
线性缩放系数 F = 200 / S
目标宽度 = round(163840 × F)
目标高度 = round(92160 × F)
标准分片像素 = 6144 × F
像素工作量约为 F²
```

这会保持现有项目的全球布局和纵横比。它不是重新定义地图投影，也不会让垂直高度自动按相同比例变化。

## 2. 计算工具

```powershell
python tools\scale\calculate_scale_profile.py --scale 300
python tools\scale\calculate_scale_profile.py --scale 100 --output profiles\1_100.json
```

工具会给出全球宽高、标准分片像素、每层瓦片数和推荐 dataset ID。

## 3. 常用比例

| 比例 | 全球尺寸 | 标准分片像素 | 2048 瓦片/层 | 相对 1:200 像素量 |
|---|---:|---:|---:|---:|
| 1:100 | 327680 x 184320 | 12288 | 14400 | 400% |
| 1:200 | 163840 x 92160 | 6144 | 3600 | 100% |
| 1:300 | 109227 x 61440 | 4096 | 1620 | 44.44% |
| 1:400 | 81920 x 46080 | 3072 | 920 | 25% |
| 1:800 | 40960 x 23040 | 1536 | 240 | 6.25% |

瓦片数按 `ceil(width / 2048) × ceil(height / 2048)` 计算，因此最后一行或一列可能是带填充的部分瓦片。

## 4. 必须同步修改的参数

创建新比例不能只改 `horizontal_scale`。以下模块必须使用相同值：

1. 地理分片 builder 的 `GLOBAL_WIDTH`、`GLOBAL_HEIGHT`；
2. 分片像素尺寸计算；
3. Pacific assembly patcher 的 `WIDTH`、`HEIGHT`；
4. height、surface、ore 的 map-info width/height；
5. 矿产数据坐标换算的 `WIDTH`、`HEIGHT`；
6. Ore 图层生成器的 `WIDTH`、`HEIGHT`、`TILES_X`、`TILES_Z`；
7. 唯一 dataset ID，例如 `global_1_300_pacific_tiled_v1`；
8. 缓存目录名、状态文件名和最终包名。

任何一项仍使用旧比例，都可能造成城市坐标偏移、矿区错位、瓦片缺失或数据包读取越界。

对应公开文件如下：

| 文件 | 需要同步的内容 |
|---|---|
| `tools/1_200/build_high_quality_region_from_v5_pipeline.py` 或复制出的新 builder | `GLOBAL_WIDTH`、`GLOBAL_HEIGHT`、输出包名、缓存命名 |
| `tools/1_200/patch_region_into_global_hq_pacific_assembly.py` | `WIDTH`、`HEIGHT`、dataset ID、assembly 名称 |
| `tools/1_200/run_global_hq_region_queue.py` | builder、patcher、状态文件和日志名称 |
| `tools/ore/build_top100_rich_ore_dataset.py` | 读取 `NOVOATLAS_SCALE_DENOMINATOR`，计算宽高与矿区坐标 |
| `tools/ore/make_global_top100_rich_ore_layer_tiles.py` | 读取同一比例变量，生成对应 Ore tile 与 map ID |
| `tools/1_400/make_global_1_400_pacific_tiled_packs.py` 的新比例副本 | 最终目录、`DATA_ID`、宽高和 tile 数 |
| 最终 `data/world/novoatlas/map_info/world.json` | 三个图层的 width、height、tile path |

推荐为新比例复制脚本，而不是直接覆盖 1:200/1:400 文件。例如建立 `tools/1_300`，这样修复旧比例时不会意外影响新版本。

## 5. 分片边界算法

对于 1:300 等不能让全球宽度整除所有经度分段的比例，不要不断累加四舍五入后的固定分片宽度。应从每条经纬度边界直接计算全局像素：

```python
left = round((west - seam_west) % 360 / 360 * global_width)
right = round((east - seam_west) % 360 / 360 * global_width)
top = round((90 - north) / 180 * global_height)
bottom = round((90 - south) / 180 * global_height)
```

分片实际宽高使用边界差值。相邻分片共享同一条计算边界，可以避免累计 1 像素误差。

跨越 Pacific seam 的分片需要按模运算拆分为左右两段写入，不能把 `right < left` 当作负宽度。

## 6. 推荐工作流

1. 运行比例计算器并保存 profile。
2. 复制现有 1:200 或 1:400 builder 为新文件，例如 `build_high_quality_region_1_300.py`。
3. 将所有尺寸改为 profile 值，并使用新的 dataset ID。
4. 保留 432 个地理分片，以维持与现有版本相近的地理处理粒度。
5. 为新比例建立独立输出目录、缓存目录和状态文件。
6. 先生成东亚、南美、欧洲、南极和 Pacific seam 附近的测试分片。
7. 拼装 2 x 2 相邻分片，检查边界、河流和矿区坐标。
8. 再启动全球队列。
9. 地表完成后，按相同比例重建 Ore 图层。

## 7. 1:300 具体示例

先生成 profile：

```powershell
python tools\scale\calculate_scale_profile.py --scale 300 --output profiles\1_300.json
```

得到的核心参数为：

```text
GLOBAL_WIDTH = 109227
GLOBAL_HEIGHT = 61440
NOMINAL_STANDARD_SHARD = 4096
TILE_SIZE = 2048
TILES_X = 54
TILES_Z = 30
DATA_ID = global_1_300_pacific_tiled_v1
```

创建脚本副本：

```powershell
Copy-Item tools\1_200 tools\1_300 -Recurse
```

在 `tools/1_300` 中依次替换上述尺寸和所有包含 `1_200` 的输出标识。不要修改真实经纬度 BBOX；比例改变的是每个 BBOX 的像素尺寸，不是地理覆盖范围。

标准 13.5° x 12° 分片可使用约 4096 x 4096 像素，但边缘和特殊纬度分片仍应以全局边界差值为准。全球宽度 109227 不是 2048 的整数倍，所以最后一列瓦片需要填充，map-info 中仍写真实宽度 109227。

先只运行一个分片：

```powershell
python tools\1_300\build_high_quality_region_from_v5_pipeline.py `
  --name test_east_asia `
  --west 116 --south 24 --east 129.5 --north 36
```

检查临时包后，再初始化新的 1:300 assembly，运行队列。队列状态、缓存和最终包名必须包含 `1_300`，否则可能把 1:300 结果写入旧版本目录。

矿产层也使用 109227 x 61440。只缩放地表而复用 1:200 或 1:400 Ore PNG，会导致矿区坐标整体错位。

## 8. 不同比例的取舍

### 1:100

细节最高，但像素量约为 1:200 的四倍、1:400 的十六倍。下载、缓存、拼装、数据包和服务器区块预生成成本都会显著增加。

### 1:300

位于 1:200 和 1:400 之间。标准 13.5° x 12° 分片正好约为 4096 x 4096，但全球宽度不是 2048 的整数倍，需要正确处理最后一列部分瓦片。

### 1:800

非常轻量，适合低存储服务器或概览型世界，但细小岛屿、河流和湖泊更容易消失。应考虑降低河流筛选阈值或适当加宽河道，但不能简单放大所有水体。

## 9. 高度比例

自定义水平比例不必重新定义垂直高度。默认可以复用当前 Minecraft 高度压缩函数，以保持可玩性。若同时改变垂直比例，应单独设计海平面、山峰上限、雪线、洞穴和结构高度；这属于新的世界生成版本，不能只改一个乘数。
