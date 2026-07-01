# 构建工具

[English](README.md) | [简体中文](README.zh-CN.md)

这些 Python 脚本组成了发布数据包所使用的离线构建流水线。

```text
1_200/    1:200 地理分区生成、队列与拼装
1_400/    1:400 河流及南极修正版生成与拼装
ore/      矿产数据集、富矿瓦片与无自定义富矿版本
pipeline/ 共用地理分类和早期流水线工具
scale/    自定义比例与坐标换算工具
```

普通玩家安装 Release 数据包时不需要运行这些脚本。它们用于复现结果、制作自定义比例和继续开发。

- `ore/make_no_custom_ore_variant.py`：保留高度和地表，移除自定义地下富矿层以及本项目对 Create 锌矿的依赖。
- `scale/calculate_scale_profile.py --scale <分母>`：计算 1:100、1:300、1:800 等比例的全球尺寸与 NovoAtlas 瓦片数量。
- `scale/convert_coordinates.py`：在 Pacific-centered 经纬度与 Minecraft X/Z 之间双向换算。
- `ore/build_top100_rich_ore_dataset.py` 和 `ore/make_global_top100_rich_ore_layer_tiles.py`：读取 `NOVOATLAS_SCALE_DENOMINATOR`，生成指定比例的矿区坐标与瓦片。

公开脚本会按需读取以下环境变量：

```text
NOVOATLAS_OUTPUT_ROOT
NOVOATLAS_CACHE_ROOT
NOVOATLAS_PIPELINE_ROOT
NOVOATLAS_MINERAL_INPUT_ROOT
NOVOATLAS_1_400_HQ_ROOT
NOVOATLAS_SCALE_DENOMINATOR
```

仓库不包含原始 WorldCover、WorldClim、HydroRIVERS、高程数据和中间缓存。在仓库根目录安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```
