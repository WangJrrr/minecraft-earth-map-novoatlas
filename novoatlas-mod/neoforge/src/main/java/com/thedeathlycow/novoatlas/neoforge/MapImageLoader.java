package com.thedeathlycow.novoatlas.neoforge;

import com.thedeathlycow.novoatlas.NovoAtlas;
import com.thedeathlycow.novoatlas.registry.ImageManager;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.server.packs.resources.ResourceManagerReloadListener;

public class MapImageLoader implements ResourceManagerReloadListener {
    public static final ResourceLocation ID = NovoAtlas.loc("map_image");

    @Override
    public void onResourceManagerReload(ResourceManager resourceManager) {
        ImageManager.HEIGHTMAP.reload(resourceManager);
        ImageManager.BIOME_MAP.reload(resourceManager);
    }
}