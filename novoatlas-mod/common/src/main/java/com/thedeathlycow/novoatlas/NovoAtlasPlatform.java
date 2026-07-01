package com.thedeathlycow.novoatlas;

import dev.architectury.injectables.annotations.ExpectPlatform;

public class NovoAtlasPlatform {
    @ExpectPlatform
    public static boolean isModLoaded(String modid) {
        throw new AssertionError();
    }
}