package com.thedeathlycow.novoatlas.mixin.accessor;

import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import net.minecraft.world.level.levelgen.NoiseChunk;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(NoiseChunk.class)
public interface NoiseChunkAccessor {
    @Invoker("cellWidth")
    int invokeCellWidth();

    @Invoker("cellHeight")
    int invokeCellHeight();

    @Invoker("getInterpolatedState")
    BlockState invokeGetInterpolatedState();

    @Accessor("beardifier")
    DensityFunctions.BeardifierOrMarker accessBeardifier();

    @Invoker("wrap")
    DensityFunction invokeWrap(DensityFunction densityFunction);
}