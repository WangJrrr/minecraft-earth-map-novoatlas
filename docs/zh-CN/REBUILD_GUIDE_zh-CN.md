# 1:200 与 1:400 重新生成指南

本文面向需要修改地表、河流、比例或矿产规则的开发者。普通玩家安装 Release 数据包时不需要运行这些脚本。

## 1. 环境准备

推荐使用 Windows PowerShell、64 位 Python 3.11+ 和足够的磁盘空间。

```powershell
cd C:\path\to\NovoAtlas-EarthMap
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy pillow
```

设置公开脚本使用的目录：

```powershell
$env:NOVOATLAS_OUTPUT_ROOT = "D:\NovoAtlasBuild\outputs"
$env:NOVOATLAS_CACHE_ROOT = "D:\NovoAtlasBuild\cache"
$env:NOVOATLAS_PIPELINE_ROOT = "$PWD\tools\pipeline"
$env:NOVOATLAS_MINERAL_INPUT_ROOT = "D:\NovoAtlasBuild\inputs\mineral_data"
```

这些环境变量只影响当前 PowerShell 窗口。重新开机或新开终端后需要再次设置。

## 2. 地理数据

在缓存目录准备：

```text
wc2.1_2.5m_tavg.zip
wc2.1_2.5m_prec.zip
terrarium_tiles/
worldcover_2021_z8/
```

WorldCover 和部分高程瓦片可由脚本按需下载。WorldClim ZIP 需要预先从官方来源获得。

在 `tools/pipeline/vector_cache` 准备：

```text
HydroRIVERS_v10_as_shp.zip
ne_10m_lakes.zip
```

1:400 的 `global_hydrorivers.py` 会按分片自动下载其他大陆 HydroRIVERS 档案，并缓存到 `NOVOATLAS_CACHE_ROOT`。使用数据前请阅读各数据提供方许可。

## 3. 使用 Release 包作为模板

生成脚本需要一个已有数据包提供 `pack.mcmeta`、dimension、surface biome 和 worldgen 基础结构。最简单可靠的做法是下载本项目对应比例的 Release 包，将它作为模板；全球高度与地表仍会由队列重新生成。

如果目标是不使用 Create 或不需要富矿，先按照 [ORE_CUSTOMIZATION_zh-CN.md](ORE_CUSTOMIZATION_zh-CN.md) 生成无自定义富矿模板。

## 4. 重新生成 1:200

### 4.1 准备拼装目录

将一个解压后的 1:200 数据包复制为：

```text
%NOVOATLAS_OUTPUT_ROOT%\NovoAtlas_World_1block200m_Global_HQ_Pacific_Assembly
```

删除旧的状态文件（如果存在）：

```powershell
Remove-Item "$env:NOVOATLAS_OUTPUT_ROOT\world_1_200_global_hq_pacific_region_queue_state.json" -ErrorAction SilentlyContinue
Remove-Item "$env:NOVOATLAS_OUTPUT_ROOT\world_1_200_global_hq_pacific_region_queue.log" -ErrorAction SilentlyContinue
```

### 4.2 启动队列

```powershell
python tools\1_200\run_global_hq_pacific_region_queue.py
```

队列逐片调用 `build_high_quality_region_from_v5_pipeline.py`，然后由 `patch_region_into_global_hq_pacific_assembly.py` 写入 Pacific-centered 全球瓦片。状态文件会记录已完成分片；进程中断后再次运行同一命令即可跳过已完成项。

### 4.3 查看进度

```powershell
Get-Content "$env:NOVOATLAS_OUTPUT_ROOT\world_1_200_global_hq_pacific_region_queue_state.json"
Get-Content "$env:NOVOATLAS_OUTPUT_ROOT\world_1_200_global_hq_pacific_region_queue.log" -Tail 20
```

### 4.4 1:200 特别说明

当前公开的 1:200 生产脚本保留旧亚洲 HydroRIVERS 路线。若需要全球完整河流，应将 1:400 的 `global_hydrorivers.py` 接入 1:200 builder，并使用新的河流缓存名，避免读取旧空掩膜。

## 5. 重新生成 1:400

### 5.1 准备基础模板

将解压后的 1:400 Original 数据包复制到：

```text
%NOVOATLAS_OUTPUT_ROOT%\FINAL_PACKS_1_400_Pacific\OriginalRichOre_1_400_Pacific_Tiled
```

若要自动生成 Top100 最终版，还需把 Top100 模板放在同级的：

```text
Top100RichOre_1_400_Pacific_Tiled
```

### 5.2 设置独立工作目录

```powershell
$env:NOVOATLAS_1_400_HQ_ROOT = "D:\NovoAtlasBuild\outputs\HQ_1_400_Rebuild"
python tools\1_400\initialize_global_hq_pacific_assembly_1_400.py
```

### 5.3 启动队列

```powershell
python tools\1_400\run_global_hq_pacific_region_queue_1_400.py
```

另开一个 PowerShell 可启动完成监视与最终打包：

```powershell
$env:NOVOATLAS_OUTPUT_ROOT = "D:\NovoAtlasBuild\outputs"
$env:NOVOATLAS_1_400_HQ_ROOT = "D:\NovoAtlasBuild\outputs\HQ_1_400_Rebuild"
python tools\1_400\watch_and_finalize_global_hq_pacific_1_400.py
```

不需要 Top100 或不使用 Create 时，不要运行自动 finalizer；队列完成后的 `OriginalRichOre_1_400_HQ_Pacific_FullRoute` 就是拼装结果，并可再使用无自定义富矿转换工具处理。

### 5.4 查看进度

```powershell
Get-Content "$env:NOVOATLAS_1_400_HQ_ROOT\world_1_400_global_hq_pacific_region_queue_state.json"
Get-Content "$env:NOVOATLAS_1_400_HQ_ROOT\world_1_400_global_hq_pacific_region_queue.log" -Tail 20
```

## 6. 中断与恢复

- 使用 `Ctrl+C` 可在前台安全停止队列。当前正在写入的分片可能需要下次重做，但已记录完成的分片不会重跑。
- 不要在 Python 正在写 PNG 或拼装瓦片时强制断电。
- 恢复时保持相同的输出目录、缓存目录和状态文件，然后重新运行队列命令。
- 若修改了河流、群系或矿物算法，应使用新的缓存文件名或清除对应分片缓存，避免旧结果掩盖新代码。

## 7. 修改后验证

在投入服务器前至少检查：

1. `pack.mcmeta` 能被 Minecraft 1.21.1 识别；
2. `map_info/world.json` 的 width、height、tile size 和路径一致；
3. height、surface、ore 的瓦片编号连续；
4. 新世界能够通过数据包验证；
5. 至少检查海岸、河流、南极、高山和一个富矿区；
6. 搜索所有模组命名空间，确认客户端和服务端安装了相应模组。

