package com.thedeathlycow.novoatlas.neoforge;

import net.neoforged.fml.loading.LoadingModList;

public class NovoAtlasPlatformImpl {
    public static boolean isModLoaded(String modid) {
        return LoadingModList.get().getModFileById(modid) != null;
    }
}