package com.thedeathlycow.novoatlas.mixin.accessor;

import net.minecraft.world.level.levelgen.SurfaceRules;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(SurfaceRules.Context.class)
public interface SurfaceRulesContextAccessor {
    @Accessor("blockX")
    int blockX();

    @Accessor("blockY")
    int blockY();

    @Accessor("blockZ")
    int blockZ();
}