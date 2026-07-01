package com.thedeathlycow.novoatlas.registry;

import com.thedeathlycow.novoatlas.NovoAtlas;
import com.thedeathlycow.novoatlas.world.gen.MapImage;
import com.thedeathlycow.novoatlas.world.gen.tiled.ServerResourceManager;
import net.minecraft.core.Registry;
import net.minecraft.resources.FileToIdConverter;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import org.jetbrains.annotations.Nullable;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.io.InputStream;
import java.util.IdentityHashMap;
import java.util.Map;

public final class ImageManager {
    public static final ImageManager HEIGHTMAP = new ImageManager(NovoAtlasResourceKeys.HEIGHTMAP, MapImage.Type.HEIGHTMAP);
    public static final ImageManager BIOME_MAP = new ImageManager(NovoAtlasResourceKeys.BIOME_MAP, MapImage.Type.BIOME_MAP);

    private final ResourceKey<Registry<MapImage>> registryKey;
    private final MapImage.Type type;
    private final Map<ResourceKey<MapImage>, MapImage> registry = new IdentityHashMap<>();

    private ImageManager(ResourceKey<Registry<MapImage>> registryKey, MapImage.Type type) {
        this.registryKey = registryKey;
        this.type = type;
    }

    public void reload(ResourceManager resourceManager) {
        Map<ResourceKey<MapImage>, MapImage> updatedRegistry = new IdentityHashMap<>();

        String regPath = NovoAtlas.MOD_ID + "/" + registryKey.location().getPath();
        var converter = new FileToIdConverter(regPath, ".png");
        Map<ResourceLocation, Resource> resources = converter.listMatchingResources(resourceManager);

        for (Map.Entry<ResourceLocation, Resource> entry : resources.entrySet()) {
            BufferedImage image;
            try (InputStream stream = entry.getValue().open()) {
                image = ImageIO.read(stream);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }

            MapImage map = MapImage.fromBufferedImage(image, this.type);
            ResourceKey<MapImage> key = ResourceKey.create(registryKey, converter.fileToId(entry.getKey()));

            updatedRegistry.put(key, map);
        }

        this.registry.clear();
        this.registry.putAll(updatedRegistry);
        NovoAtlas.LOGGER.info("Reloaded map images for {}", registryKey);

        // 更新全局 ResourceManager，供 TiledMapImage 使用
        ServerResourceManager.set(resourceManager);
    }

    @Nullable
    public MapImage getImage(ResourceKey<MapImage> key) {
        return this.registry.get(key);
    }
}