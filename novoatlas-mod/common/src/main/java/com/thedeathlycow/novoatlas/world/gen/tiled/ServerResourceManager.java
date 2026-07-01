package com.thedeathlycow.novoatlas.world.gen.tiled;

import net.minecraft.server.packs.resources.ResourceManager;
import org.jetbrains.annotations.Nullable;

/**
 * 全局 ResourceManager 持有者。
 * ImageManager.reload() 时设置，TiledMapImage 首次采样时读取。
 */
public final class ServerResourceManager {
    private static volatile ResourceManager instance;

    public static void set(@Nullable ResourceManager rm) {
        instance = rm;
        TileFileSystemResolver.clearCache();
    }

    @Nullable
    public static ResourceManager get() { return instance; }

    public static ResourceManager getOrThrow() {
        ResourceManager rm = instance;
        if (rm == null) throw new IllegalStateException(
                "Server ResourceManager not available. Tiled maps require server-side generation.");
        return rm;
    }
}
