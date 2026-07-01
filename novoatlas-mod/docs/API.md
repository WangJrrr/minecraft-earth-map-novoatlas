# NovoAtlas 瓦片化地图 — API 接口文档

> **版本**: 基于 NovoAtlas 1.7.0+  
> **新增功能**: 瓦片化（Tiled）地图加载，支持超大尺寸世界生成

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        MapInfo                              │
│  heightMap: ImageSource                                     │
│  fluidHeightMap: Optional<ImageSource>                      │
│                                                             │
│  getHeightMap() ──► MapImage (cached)                       │
│  getFluidHeightMap() ──► MapImage (cached)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  ImageSource │
                    │              │
                    │ Either<      │
                    │   Tiled,     │──► TiledImageConfig ──► TiledMapImage
                    │   Registry   │──► ResourceKey ───────► SingleMapImage
                    │ >            │
                    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌────────────┐ ┌──────────┐ ┌──────────────┐
     │SingleMapImg│ │TiledMapImg│ │TileImageCache│
     │            │ │          │ │              │
     │ int[][]    │ │ config   │ │ LRU (64 tiles)│
     │ O(1) 访问  │ │ TileCache│ │ 读写锁       │
     └────────────┘ └──────────┘ └──────────────┘
```

---

## 核心类说明

### `MapImage`（抽象类）
**包**: `com.thedeathlycow.novoatlas.impl.gen`

所有地图图像的基类。定义了统一的像素访问接口。

```java
public abstract class MapImage {
    public abstract int getPixel(int x, int z);  // 子类必须实现
    public int sample(int x, int z, MapInfo info);      // 世界坐标 → 像素值
    public int sample(int x, int z, MapInfo info, int fallback);  // 越界返回 fallback
    public int getTruncated(double x, double z);        // 截断采样（最近邻）
    public int width();
    public int height();
    public Type type();  // HEIGHTMAP 或 BIOME_MAP
}
```

| 方法 | 说明 |
|------|------|
| `getPixel(x, z)` | **抽象方法**。子类实现具体的像素读取逻辑 |
| `sample(x, z, info)` | 世界坐标 → 像素坐标 → 插值采样（含水平/垂直缩放）|
| `getTruncated(x, z)` | 截断坐标后直接 getPixel，不插值 |

### `SingleMapImage`
**包**: `com.thedeathlycow.novoatlas.impl.gen`

单张图片实现。整张 PNG 加载到 `int[][]`，O(1) 无锁访问。适合小图（< 4096×4096）。

```java
public final class SingleMapImage extends MapImage {
    public int[][] pixels();  // 直接返回整个像素数组
    @Override public int getPixel(int x, int z);  // pixels[x][z]
}
```

### `TiledMapImage`
**包**: `com.thedeathlycow.novoatlas.impl.gen.tiled`

瓦片化实现。**不加载整张图到内存**，按需从数据包读取瓦片 PNG。

```java
public final class TiledMapImage extends MapImage {
    public TiledMapImage(TiledImageConfig config, Type type);
    @Override public int getPixel(int x, int z);
    public TiledImageConfig config();
}
```

**工作流程**：
1. Chunk 坐标 → 世界像素坐标 (px, pz)
2. 像素坐标 → 瓦片坐标 (tileX, tileZ) + 瓦片内偏移 (localX, localZ)
3. `TileImageCache.get(tileX, tileZ)` → BufferedImage
4. `raster.getSample(localX, localZ, 0)` (高度图) 或 `getRGB(localX, localZ) & 0xFFFFFF` (群系图)

### `TiledImageConfig`
**包**: `com.thedeathlycow.novoatlas.impl.gen.tiled`

瓦片配置的不可变记录。

```java
public record TiledImageConfig(
    int tileSize,      // 瓦片边长（像素），如 1024
    String tilePattern,// 瓦片路径模板，如 "ns:height/{tx}_{tz}.png"
    int worldWidth,    // 世界总宽度（像素），如 81920
    int worldHeight    // 世界总高度（像素），如 46080
)
```

| 字段 | JSON 字段 | 说明 |
|------|-----------|------|
| `tileSize` | `tile_size` | 每张瓦片的像素边长，必须是正整数 |
| `tilePattern` | `tiles` | 资源路径模板，`{tx}`=瓦片X，`{tz}`=瓦片Z |
| `worldWidth` | `width` | 整个世界的像素宽度 |
| `worldHeight` | `height` | 整个世界的像素高度 |

### `TileImageCache`
**包**: `com.thedeathlycow.novoatlas.impl.gen.tiled`

线程安全的 LRU 瓦片缓存。

```java
public final class TileImageCache {
    public TileImageCache(int maxTiles, BiFunction<Integer, Integer, BufferedImage> loader);
    public BufferedImage get(int tileX, int tileZ);
    public int size();
    public void clear();
}
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `maxTiles` | 64 | 最大缓存瓦片数。1024×1024 灰度 ≈ 1MB/张，RGB ≈ 4MB/张 |
| `loader` | 必填 | `(tileX, tileZ) -> BufferedImage`，由 TiledMapImage 提供 |

**线程安全策略**：
- `ReentrantReadWriteLock`：正常读取用读锁（多线程并发），加载新瓦片用写锁
- 双重检查锁定（DCL）：避免同一瓦片被并发加载多次
- `LinkedHashMap(access-order=true)` + `removeEldestEntry`：自动淘汰最久未使用的瓦片

### `ImageSource`
**包**: `com.thedeathlycow.novoatlas.impl.gen`

统一单图和瓦片两种来源的包装类型。

```java
public record ImageSource(Either<TiledImageConfig, ResourceKey<MapImage>> value) {
    public static Codec<ImageSource> codec(ResourceKey<Registry<MapImage>> registryKey);
    public MapImage resolve(MapImage.Type type, ImageManager registry);
    public boolean isTiled();
}
```

| 方法 | 说明 |
|------|------|
| `codec(registryKey)` | 创建 Codec，先解析 JSON 对象（瓦片），失败则解析字符串（ResourceKey）|
| `resolve(type, registry)` | 解析为 MapImage：瓦片→TiledMapImage，单图→ImageManager 查找 |
| `isTiled()` | 是否使用瓦片化加载 |

---

## 数据流：从 Chunk 到像素

```
chunk (blockX=32, blockZ=-64)
  │
  ▼
MapInfo.getHeightMapElevation(32, -64, fallback)
  │
  ▼
MapImage.sample(x=32, z=-64, info, fallback)
  │  horizontalScale: x/=scale, z/=scale
  │  + width/2, height/2 (居中偏移)
  │
  ▼
像素坐标: px = 25123.5, pz = 19872.3
  │
  ▼
MapScaleConfig.HorizontalConfig.sample(25123.5, 19872.3, image)
  │  使用插值器 (nearest/bilinear/bicubic/lanczos)
  │
  ▼
Interpolator.sample(x, z, image)
  │  Bilinear: getPixel(25123, 19872), getPixel(25124, 19872), ...
  │  Bicubic:  getPixel() × 16
  │
  ▼
TiledMapImage.getPixel(25123, 19872)
  │  tileX = 25123 / 1024 = 24
  │  tileZ = 19872 / 1024 = 19
  │  localX = 25123 % 1024 = 547
  │  localZ = 19872 % 1024 = 416
  │
  ▼
TileImageCache.get(24, 19)
  │  LRU 命中 → 直接返回
  │  LRU 未命中 → 读锁→写锁→loadTile(24,19)→放入缓存
  │
  ▼
BufferedImage.getRaster().getSample(547, 416, 0)
  → 返回灰度值 128
```
