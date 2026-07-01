package com.thedeathlycow.novoatlas.world.gen.tiled;

import com.thedeathlycow.novoatlas.NovoAtlas;
import com.thedeathlycow.novoatlas.world.gen.MapImage;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.io.InputStream;
import java.util.Map;
import java.util.Optional;

/**
 * 瓦片化 MapImage 实现 — 不将整张图加载到内存，按 chunk 需求动态读取瓦片。
 */
public final class TiledMapImage extends MapImage {

    private final TiledImageConfig config;
    private final TileImageCache tileCache;

    public TiledMapImage(TiledImageConfig config, Type type) {
        super(config.worldWidth(), config.worldHeight(), type);
        this.config = config;
        this.tileCache = new TileImageCache(this::loadTile);
    }

    @Override
    public int getPixel(int x, int z) {
        if (x < 0 || z < 0 || x >= width() || z >= height()) return Integer.MIN_VALUE;

        int tileX = Math.floorDiv(x, config.tileSize());
        int tileZ = Math.floorDiv(z, config.tileSize());
        int localX = Math.floorMod(x, config.tileSize());
        int localZ = Math.floorMod(z, config.tileSize());

        BufferedImage tile = tileCache.get(tileX, tileZ);
        localX = Math.min(localX, tile.getWidth() - 1);
        localZ = Math.min(localZ, tile.getHeight() - 1);

        if (type() == Type.HEIGHTMAP) {
            return tile.getRaster().getSample(localX, localZ, 0);
        } else {
            return tile.getRGB(localX, localZ) & 0xFFFFFF;
        }
    }

    private BufferedImage loadTile(int tileX, int tileZ) {
        ResourceManager manager = getResourceManager();
        String path = config.tilePath(tileX, tileZ);
        ResourceLocation id = ResourceLocation.parse(path);

        Optional<BufferedImage> fileTile = TileFileSystemResolver.load(id);
        if (fileTile.isPresent()) {
            return fileTile.orElseThrow();
        }

        Optional<Resource> resource = manager.getResource(id);
        if (resource.isEmpty()) {
            String idPath = id.getPath();
            int lastSlash = idPath.lastIndexOf('/');
            String searchPrefix = lastSlash >= 0 ? idPath.substring(0, lastSlash) : idPath;
            Map<ResourceLocation, Resource> matches = manager.listResources(
                    searchPrefix,
                    candidate -> candidate.getNamespace().equals(id.getNamespace())
                            && candidate.getPath().equals(id.getPath())
            );
            resource = matches.values().stream().findFirst();
        }
        if (resource.isEmpty()) {
            String idPath = id.getPath();
            int lastSlash = idPath.lastIndexOf('/');
            String searchPrefix = lastSlash >= 0 ? idPath.substring(0, lastSlash) : idPath;
            Map<ResourceLocation, Resource> nearby = manager.listResources(
                    searchPrefix,
                    candidate -> candidate.getNamespace().equals(id.getNamespace())
            );
            NovoAtlas.LOGGER.error(
                    "Missing tile at ({}, {}): '{}'. Found {} resources in namespace '{}' under '{}'",
                    tileX,
                    tileZ,
                    path,
                    nearby.size(),
                    id.getNamespace(),
                    searchPrefix
            );
            throw new IllegalStateException(
                    "Missing tile at (%d,%d): '%s'".formatted(tileX, tileZ, path));
        }

        try (InputStream stream = resource.get().open()) {
            return ImageIO.read(stream);
        } catch (IOException e) {
            throw new RuntimeException("Failed to load tile (%d,%d)".formatted(tileX, tileZ), e);
        }
    }

    private ResourceManager getResourceManager() {
        return ServerResourceManager.getOrThrow();
    }
}
