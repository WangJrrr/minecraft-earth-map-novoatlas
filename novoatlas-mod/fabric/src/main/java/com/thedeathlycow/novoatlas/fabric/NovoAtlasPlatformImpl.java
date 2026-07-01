package com.thedeathlycow.novoatlas.fabric;

import net.fabricmc.loader.api.FabricLoader;

public class NovoAtlasPlatformImpl {
    public static boolean isModLoaded(String modid) {
        return FabricLoader.getInstance().isModLoaded(modid);
    }
}